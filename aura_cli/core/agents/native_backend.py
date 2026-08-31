"""
Native Backend — Lightweight agent backend without external dependencies.

Provides a zero-dependency agent backend for Aura CLI with multi-turn
tool calling via the LiteLLM interface.
"""

import json
import logging
import re
import time
from typing import Any, Callable, Dict, List, Optional

from aura_cli.core.llm.model_utils import DEFAULT_MODEL

from .interface import AgentBackend, AgentConfig, AgentResponse

_logger = logging.getLogger(__name__)

# Redact API keys and tokens from error messages before logging (avoid leaks)
_REDACT_PATTERNS = [
    (re.compile(r"key=AIzaSy[^\s&'\"]+", re.I), "key=***REDACTED***"),
    (
        re.compile(r"api[_-]?key['\"]?\s*[:=]\s*['\"]?[^\s'\"]+", re.I),
        "api_key=***REDACTED***",
    ),
    (re.compile(r"sk-[a-zA-Z0-9]{20,}", re.I), "sk-***REDACTED***"),
    (re.compile(r"Bearer\s+[a-zA-Z0-9._-]+", re.I), "Bearer ***REDACTED***"),
]


def _redact_sensitive(msg: str) -> str:
    """Replace API keys and tokens in string so logs stay safe."""
    if not msg:
        return msg
    out = msg
    for pattern, replacement in _REDACT_PATTERNS:
        out = pattern.sub(replacement, out)
    return out


def _is_rate_limit_error(exc: BaseException) -> bool:
    """True if exception is a rate limit (429 / quota) error."""
    name = type(exc).__name__
    if "RateLimit" in name or "rate_limit" in name.lower():
        return True
    msg = str(exc).lower()
    return any(x in msg for x in ("429", "rate limit", "quota", "resource_exhausted"))


def _parse_retry_after_seconds(exc: BaseException) -> Optional[int]:
    """Parse retry_after from exception (e.g. 'Please retry in 9.39s')."""
    if hasattr(exc, "retry_after") and exc.retry_after is not None:
        try:
            return int(exc.retry_after)
        except (TypeError, ValueError):
            pass  # non-numeric retry_after — fall through to regex parse
    msg = str(exc)
    m = re.search(r"retry\s+in\s+([\d.]+)\s*s", msg, re.I)
    if m:
        try:
            return max(1, int(float(m.group(1))))
        except (TypeError, ValueError):
            pass  # malformed float in retry message — return None
    return None


_DEFAULT_MAX_TURNS = 15


class NativeAgent:
    """
    Simple native agent.

    Attributes:
        name: Agent name
        role: Agent role
        system_message: System message
        llm_config: LLM configuration
        tools: Available tools
        conversation_history: Message history
    """

    def __init__(self, config: AgentConfig):
        """Initialize the instance."""
        self.name = config.name
        self.role = config.role
        self.system_message = config.system_message
        self.llm_config = config.llm_config
        self.tools = config.tools or []
        self.conversation_history: List[Dict[str, Any]] = []

    def add_message(self, role: str, content: str, **extra):
        """Add message to history."""
        msg: Dict[str, Any] = {"role": role, "content": content}
        msg.update(extra)
        self.conversation_history.append(msg)

    def add_raw_message(self, msg: Dict[str, Any]):
        """Add a pre-built message dict to history."""
        self.conversation_history.append(msg)

    def get_messages(self) -> List[Dict[str, Any]]:
        """Get message history."""
        return [
            {"role": "system", "content": self.system_message},
            *self.conversation_history,
        ]


class NativeUserProxy:
    """
    Native user proxy with multi-turn tool calling support.

    Implements an agentic loop: the assistant can request tool calls,
    the proxy executes them via ``function_map`` and feeds the results
    back until the assistant emits TERMINATE or the turn limit is hit.
    """

    def __init__(self, config: AgentConfig):
        """Initialize the instance."""
        self.name = config.name
        self.max_consecutive_auto_reply = (
            config.max_consecutive_auto_reply or _DEFAULT_MAX_TURNS
        )
        self.human_input_mode = config.human_input_mode
        self.function_map: Dict[str, Callable] = {}
        self.is_termination_msg: Optional[Callable] = None
        self.code_execution_config = False
        self._last_message: Optional[Dict[str, Any]] = None
        self.shutdown_check: Optional[Callable[[], bool]] = None
        self.on_message: Optional[Callable[[str, str], None]] = None

    def last_message(self) -> Dict[str, Any]:
        """Get last message."""
        return self._last_message or {}

    def initiate_chat(self, assistant: NativeAgent, message: str):
        """
        Initiate multi-turn chat with assistant, executing tool calls.

        The loop runs until:
        - The assistant sends a termination message (TERMINATE)
        - The maximum number of turns is reached
        - The LLM response contains no tool calls and no further action
        """
        assistant.add_message("user", message)

        tool_schemas = assistant.llm_config.get("tool_schemas")

        for turn in range(self.max_consecutive_auto_reply):
            if self.shutdown_check and self.shutdown_check():
                _logger.warning("Shutdown requested — stopping agent loop")
                break

            response = self._call_llm(assistant, tool_schemas)

            if response is None:
                _logger.warning("LLM returned None response on turn %d", turn)
                break

            choice = (
                response.choices[0]
                if hasattr(response, "choices") and response.choices
                else None
            )
            if choice is None:
                break

            resp_message = choice.message
            content = getattr(resp_message, "content", None) or ""
            tool_calls = getattr(resp_message, "tool_calls", None)

            if self.on_message and content:
                self.on_message("assistant", content)

            if tool_calls and self.function_map:
                assistant.add_raw_message(
                    self._build_assistant_msg(content, tool_calls)
                )
                any_executed = self._execute_tool_calls(assistant, tool_calls)
                if not any_executed:
                    assistant.add_message("assistant", content)
                    self._last_message = {"role": "assistant", "content": content}
                    break
            else:
                assistant.add_message("assistant", content)
                self._last_message = {"role": "assistant", "content": content}

                if self.is_termination_msg and self.is_termination_msg(
                    {"content": content}
                ):
                    break
                if not tool_calls:
                    break

    # Internal helpers

    @staticmethod
    def _build_assistant_msg(content: str, tool_calls) -> Dict[str, Any]:
        """Serialize an assistant message with tool_calls for the history."""
        calls_serialized = []
        for tc in tool_calls:
            calls_serialized.append(
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments,
                    },
                }
            )
        msg: Dict[str, Any] = {
            "role": "assistant",
            "content": content,
            "tool_calls": calls_serialized,
        }
        return msg

    def _execute_tool_calls(self, assistant: NativeAgent, tool_calls) -> bool:
        """Execute tool calls and append results to history. Returns True if any executed."""
        executed = False
        for tc in tool_calls:
            fn_name = tc.function.name
            fn_args_raw = tc.function.arguments or "{}"
            tool_call_id = tc.id

            if fn_name not in self.function_map:
                result_str = json.dumps(
                    {"error": f"Ferramenta '{fn_name}' não encontrada"}
                )
                assistant.add_raw_message(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call_id,
                        "name": fn_name,
                        "content": result_str,
                    }
                )
                executed = True
                continue

            try:
                fn_args = (
                    json.loads(fn_args_raw)
                    if isinstance(fn_args_raw, str)
                    else fn_args_raw
                )
            except json.JSONDecodeError:
                fn_args = {}

            try:
                _logger.info("Executing tool %s(%s)", fn_name, list(fn_args.keys()))
                result = self.function_map[fn_name](**fn_args)
                if not isinstance(result, str):
                    result_str = json.dumps(result, ensure_ascii=False, default=str)
                else:
                    result_str = result
            except Exception as exc:
                _logger.error("Tool %s failed: %s", fn_name, exc, exc_info=True)
                result_str = json.dumps({"error": str(exc)})

            MAX_TOOL_RESULT = 12_000
            if len(result_str) > MAX_TOOL_RESULT:
                result_str = result_str[:MAX_TOOL_RESULT] + "\n... [truncated]"

            assistant.add_raw_message(
                {
                    "role": "tool",
                    "tool_call_id": tool_call_id,
                    "name": fn_name,
                    "content": result_str,
                }
            )
            if self.on_message:
                self.on_message("tool", f"{fn_name}: {result_str[:200]}")
            executed = True

        return executed

    def _call_llm(self, assistant: NativeAgent, tool_schemas=None):
        """Single LLM call with optional tool schemas. Retries on 429 with backoff."""
        from aura_cli.core.llm.base import query_with_fallback

        messages = assistant.get_messages()
        llm_config = assistant.llm_config
        model, temperature, api_key = self._extract_model_params(llm_config)
        kwargs: Dict[str, Any] = {
            "messages": messages,
            "model": model,
            "temperature": temperature,
        }
        if api_key:
            kwargs["api_key"] = api_key
        if tool_schemas:
            kwargs["tools"] = tool_schemas

        max_retries = 2
        last_error: Optional[BaseException] = None

        for attempt in range(max_retries + 1):
            try:
                return query_with_fallback(**kwargs)
            except Exception as e:
                last_error = e
                if _is_rate_limit_error(e) and attempt < max_retries:
                    wait_s = _parse_retry_after_seconds(e) or 10
                    _logger.warning(
                        "Rate limit (429). Waiting %ds before retrying (%d/%d).",
                        wait_s,
                        attempt + 1,
                        max_retries,
                    )
                    time.sleep(wait_s)
                    continue
                break

        if last_error is not None:
            safe_msg = _redact_sensitive(str(last_error))
            if _is_rate_limit_error(last_error):
                _logger.warning("Error calling LLM (rate limit): %s", safe_msg)
            else:
                _logger.error("Error calling LLM: %s", safe_msg, exc_info=True)
        return None

    @staticmethod
    def _extract_model_params(llm_config: Dict[str, Any]):
        """Extract model name, temperature, and api_key from llm_config."""
        if llm_config.get("config_list"):
            cfg = llm_config["config_list"][0]
            return (
                cfg.get("model", DEFAULT_MODEL),
                cfg.get("temperature", 0.7),
                cfg.get("api_key"),
            )
        return (
            llm_config.get("model", DEFAULT_MODEL),
            llm_config.get("temperature", 0.7),
            llm_config.get("api_key"),
        )


class NativeBackend(AgentBackend):
    """
    Native backend without external dependencies.

    Provides a lightweight agent implementation using LiteLLM directly.
    """

    def create_assistant(self, config: AgentConfig) -> NativeAgent:
        """Create native assistant agent."""
        return NativeAgent(config)

    def create_user_proxy(self, config: AgentConfig) -> NativeUserProxy:
        """Create native user proxy."""
        return NativeUserProxy(config)

    async def execute_conversation(
        self, assistant: NativeAgent, user_proxy: NativeUserProxy, message: str
    ) -> AgentResponse:
        """
        Execute conversation using native backend.

        Args:
            assistant: Native assistant agent
            user_proxy: Native user proxy
            message: Initial message

        Returns:
            Agent response with conversation result
        """
        try:
            user_proxy.initiate_chat(assistant, message)

            last_message = user_proxy.last_message()

            return AgentResponse(
                content=last_message.get("content", ""),
                metadata={
                    "backend": "native",
                    "messages_count": len(assistant.conversation_history),
                },
                success=True,
            )
        except Exception as e:
            return AgentResponse(
                content="", metadata={"backend": "native"}, success=False, error=str(e)
            )

    def get_backend_name(self) -> str:
        """Get backend name."""
        return "native"
