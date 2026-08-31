"""
Lightweight subagent runner for AuraCli.

Implements a synchronous, autonomous subagent that the main chat agent can
delegate focused tasks to.  Unlike AGI (heavy, multi-step planning) or Ops
(DevOps-focused), this runner is:

- Synchronous: blocks the caller, returns result inline
- Autonomous: no user confirmations needed (auto-approve all operations)
- Focused: limited tool set (12 essential tools)
- Fast: max 8 turns, 60s timeout
- Simple: uses NativeAgent directly, no planning/orchestration

This module belongs in ``core/agents/`` because it contains only execution
logic with no UI dependencies.  The CLI layer (``AppLoop``) delegates to it
via ``AppLoop._do_delegate_to_subagent()``.

Usage (from the main chat LLM):
    delegate_to_subagent(task="Read main.py and list all functions")
    delegate_to_subagent(task="Create a utils.py with a format_date function")
    delegate_to_subagent(task="Find all TODO comments in the project")
"""

from __future__ import annotations

from pathlib import Path
import threading
import time
from typing import Any, Callable, Dict, Optional
import uuid

from aura_cli.application.tools.execution_policy import (
    TaskExecutionPolicy,
    execution_policy_context,
)
from aura_cli.core.logger import get_logger

logger = get_logger(__name__)


def _invoke_subagent_tool_with_policy(
    name: str,
    func: Callable[..., Any],
    kwargs: Dict[str, Any],
    *,
    tool_call_count: list[int],
    on_tool_call: Optional[Callable[[str, int], None]],
    task_id: Optional[str] = None,
    cancel_event: Optional[threading.Event] = None,
    deadline: Optional[float] = None,
) -> Any:
    """Invoke one subagent tool without escaping its task-local policy."""
    if cancel_event is not None and cancel_event.is_set():
        raise TimeoutError("Subagent cancellation requested")
    if deadline is not None and time.monotonic() >= deadline:
        if cancel_event is not None:
            cancel_event.set()
        raise TimeoutError("Subagent execution deadline exceeded")

    tool_call_count[0] += 1
    if on_tool_call:
        on_tool_call(name, tool_call_count[0])
    policy = TaskExecutionPolicy(
        task_id=task_id or f"subagent:{name}",
        auto_confirm=True,
        allow_dangerous=False,
        confirm_writes=False,
    )
    with execution_policy_context(policy):
        return func(**kwargs)


# Tools available to the subagent (focused subset)
SUBAGENT_TOOLS = frozenset(
    {
        "read_file",
        "write_file",
        "edit_file",
        "list_directory",
        "find_in_files",
        "codebase_search",
        "tree_view",
        "run_shell_command",
        "web_search",
        "glob_search",
        "advanced_grep_search",
    }
)

# System prompt for the subagent
SUBAGENT_SYSTEM_PROMPT = """You are an autonomous subagent of AuraCli. Your role is to execute specific tasks directly and efficiently.

Rules:
- Execute the task using the available tools
- Be autonomous — do not ask questions, use your judgment
- Be concise in the final result
- When the task is done, present the result and say TERMINATE
- If the task cannot be completed, explain briefly why and say TERMINATE
- Do not repeat the task back — go straight to execution
- Maximum efficiency: use the minimum number of calls necessary"""

# Configuration
MAX_TURNS = 8
TIMEOUT_SECONDS = 60.0


def run_subagent(
    task: str,
    context: str = "",
    model: str = "",
    project_root: Optional[Path] = None,
    tools_dict: Optional[Dict[str, Callable]] = None,
    on_tool_call: Optional[Callable[[str, int], None]] = None,
    task_id: Optional[str] = None,
    strategy_card: Optional[Any] = None,
    use_strategy_card: bool = False,
) -> str:
    """
    Execute a focused task using a lightweight subagent synchronously.

    Args:
        task: The task description for the subagent.
        context: Optional additional context.
        model: LLM model to use. If empty, uses the current session model.
        project_root: Project root for path resolution.
        tools_dict: Available tools dict. If None, fetches from ServiceRegistry.
        on_tool_call: Optional callback(tool_name, call_count) for UI updates.
        task_id: Optional task identifier for policy tracking.
        strategy_card: Optional ``AgentCard`` whose content will be injected
            into the task prompt to diversify the subagent's approach.

    Returns:
        The subagent's final response text, or an error message.
    """
    # Inject strategy card into task prompt if provided.
    if use_strategy_card and strategy_card is None:
        try:
            from aura_cli.core.agents.strategy_deck import StrategyDeck
            strategy_card = StrategyDeck().draw_one()
        except Exception as _deck_err:
            logger.debug("Failed to draw strategy card: %s", _deck_err)
    if strategy_card is not None:
        try:
            from aura_cli.core.agents.strategy_injector import inject_card_into_prompt

            task = inject_card_into_prompt(task, strategy_card)
        except Exception as _card_err:
            logger.debug("Failed to inject strategy card: %s", _card_err)

    start_time = time.time()
    execution_task_id = task_id or f"subagent:{uuid.uuid4().hex[:12]}"
    cancel_event = threading.Event()
    deadline = time.monotonic() + TIMEOUT_SECONDS

    # Resolve model
    if not model:
        try:
            from aura_cli.core.config import get_config_manager
            from aura_cli.core.llm.model_utils import (
                DEFAULT_MODEL,
                resolve_model_option,
            )

            configured_model = get_config_manager().get("default_model")
            model = (
                resolve_model_option(configured_model)
                if configured_model
                else DEFAULT_MODEL
            )
        except Exception:
            from aura_cli.core.llm.model_utils import DEFAULT_MODEL

            model = DEFAULT_MODEL

    # Get tools
    if tools_dict is None:
        try:
            from aura_cli.core.service_registry import get_tools_dict

            tools_dict = get_tools_dict()
        except Exception:
            return "Error: could not load subagent tools."

    # Filter to subagent tool set
    subagent_tools = {
        name: func for name, func in tools_dict.items() if name in SUBAGENT_TOOLS
    }

    if not subagent_tools:
        return "Error: no tools available for the subagent."

    # Build the message
    user_message = task
    if context:
        user_message = f"{task}\n\nContexto adicional:\n{context}"

    # Create NativeAgent + NativeUserProxy and run
    try:
        assistant, user_proxy = _create_subagent_backend(
            model,
            subagent_tools,
            on_tool_call,
            execution_task_id,
            cancel_event,
            deadline,
        )
        return _run_subagent_conversation(
            assistant,
            user_proxy,
            user_message,
            start_time,
            cancel_event=cancel_event,
            deadline=deadline,
        )

    except ImportError as e:
        return f"Error: subagent component unavailable ({e})"
    except Exception as e:
        logger.error(f"Subagent execution error: {e}")
        return f"Subagent execution error: {e}"


def _create_subagent_backend(
    model: str,
    subagent_tools: dict,
    on_tool_call: Optional[Callable],
    task_id: str,
    cancel_event: Optional[threading.Event] = None,
    deadline: Optional[float] = None,
) -> tuple:
    """Create and configure NativeBackend assistant and user_proxy. Returns (assistant, user_proxy)."""
    from aura_cli.core.agents.interface import AgentConfig
    from aura_cli.core.agents.native_backend import NativeBackend

    backend = NativeBackend()

    assistant_config = AgentConfig(
        name="aura_subagent",
        role="assistant",
        system_message=SUBAGENT_SYSTEM_PROMPT,
        llm_config={"config_list": [{"model": model}], "timeout": TIMEOUT_SECONDS},
        tools=list(subagent_tools.values()),
        max_consecutive_auto_reply=MAX_TURNS,
        human_input_mode="NEVER",
    )
    proxy_config = AgentConfig(
        name="aura_proxy",
        role="user",
        system_message="",
        llm_config={},
        tools=list(subagent_tools.values()),
        max_consecutive_auto_reply=MAX_TURNS,
        human_input_mode="NEVER",
    )

    assistant = backend.create_assistant(assistant_config)
    user_proxy = backend.create_user_proxy(proxy_config)

    tool_call_count = [0]

    def _wrap_tool(name: str, func: Callable) -> Callable:
        """Wrap a tool to skip confirmations and track usage."""

        def wrapped(**kwargs):
            return _invoke_subagent_tool_with_policy(
                name,
                func,
                kwargs,
                tool_call_count=tool_call_count,
                on_tool_call=on_tool_call,
                task_id=task_id,
                cancel_event=cancel_event,
                deadline=deadline,
            )

        return wrapped

    user_proxy.function_map = {
        name: _wrap_tool(name, func) for name, func in subagent_tools.items()
    }

    try:
        from aura_cli.core.llm.tool_schemas import create_tool_schemas

        tool_schemas = create_tool_schemas(subagent_tools)
        assistant.llm_config["tool_schemas"] = tool_schemas
    except Exception as e:
        logger.debug(f"Failed to create tool schemas for subagent: {e}")

    def _is_terminate(msg: dict) -> bool:
        content = msg.get("content", "") or ""
        return "TERMINATE" in content

    user_proxy.is_termination_msg = _is_terminate
    return assistant, user_proxy


def _run_subagent_conversation(
    assistant: Any,
    user_proxy: Any,
    user_message: str,
    start_time: float,
    *,
    cancel_event: Optional[threading.Event] = None,
    deadline: Optional[float] = None,
) -> str:
    """Execute the subagent conversation in a thread with timeout. Returns result string."""
    import asyncio

    result_container: list = [None]
    error_container: list = [None]

    def _run():
        try:
            from aura_cli.core.agents.native_backend import NativeBackend

            response = asyncio.run(
                NativeBackend().execute_conversation(
                    assistant, user_proxy, user_message
                )
            )
            result_container[0] = response
        except Exception as e:
            error_container[0] = str(e)

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()
    remaining = (
        max(0.0, deadline - time.monotonic())
        if deadline is not None
        else TIMEOUT_SECONDS
    )
    thread.join(timeout=remaining)

    if thread.is_alive():
        if cancel_event is not None:
            cancel_event.set()
        return (
            f"Subagent timeout ({TIMEOUT_SECONDS}s). Task possibly incomplete."
        )
    if error_container[0]:
        return f"Subagent error: {error_container[0]}"

    response = result_container[0]
    if response and response.success:
        content = (response.content or "").replace("TERMINATE", "").strip()
        return content or "(Subagent completed the task with no textual response)"
    if response:
        return f"Subagent failed: {response.error or 'unknown error'}"
    return "Subagent returned no result."
