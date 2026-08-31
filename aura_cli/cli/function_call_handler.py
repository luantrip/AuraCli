"""CLI adapter for an LLM turn that may execute tools.

Response classification, call budgeting and provider-error policies live in
``application.conversation``. Provider invocation, Rich feedback and concrete
tool execution remain here at the interface boundary. Provider-specific tool-call
formats are normalized by ``cli.response_parser`` and execution is delegated to
the canonical engine in ``cli.tool_execution``.
"""

import asyncio
import inspect
import json
import os
import threading
import time
from typing import Any, Callable, Dict, List, Optional, Tuple

from rich.console import Console

from aura_cli.application.conversation.claims import (
    factual_fallback,
    repair_instruction,
    validate_completion_claims,
)
from aura_cli.application.conversation.continuity import (
    ContinuationController,
    TurnStopReason,
    stop_message,
)
from aura_cli.application.conversation.function_loop import (
    FunctionLoopAction,
    FunctionLoopBudget,
    decide_function_loop_action,
)
from aura_cli.application.conversation.provider_errors import (
    ProviderErrorKind,
    resolve_provider_error,
)
from aura_cli.application.execution import LLMCallRecord, TurnExecution, utc_now
from aura_cli.cli import response_parser, tool_execution
from aura_cli.cli.ui.manager import UIManager
from aura_cli.cli.utils.exceptions import (
    FileOperationError,
    LLMError,
    RateLimitError,
    ToolExecutionError,
)
from aura_cli.contracts.security import CapabilityAuditSink
from aura_cli.core.llm.base import query_with_fallback
from aura_cli.core.logger import get_logger

# Deliberately small public surface. Parsing belongs to response_parser and
# execution internals belong to tool_execution.
__all__ = [
    "execute_tool_call",
    "process_function_calls_loop",
]


logger = get_logger(__name__)

_globals_lock = threading.Lock()
_last_error_message: Optional[str] = None
_last_error_time: float = 0.0
_ERROR_SUPPRESSION_WINDOW = (
    3.0  # Seconds to suppress identical quota/rate-limit messages
)


def _guard_completion_claims(
    *,
    content: str,
    user_request: Optional[str],
    turn_execution: Optional[TurnExecution],
    conversation_history: List[Dict],
    repair_attempted: bool,
) -> tuple[str, bool]:
    """Return guarded content and whether another model iteration is required."""
    if turn_execution is None or not user_request:
        return content, False
    validation = validate_completion_claims(user_request, content, turn_execution)
    if validation.supported:
        return content, False
    if repair_attempted:
        return factual_fallback(turn_execution, validation.issues), False
    conversation_history.append(
        {
            "role": "system",
            "content": repair_instruction(turn_execution, validation.issues),
        }
    )
    logger.warning(
        "Unsupported completion claim rejected for turn %s: %s",
        turn_execution.turn_id,
        "; ".join(validation.issues),
    )
    return content, True


async def _emit_checkpoint_if_due(
    continuation: ContinuationController,
    calls_executed: int,
    callback: Optional[Callable[[TurnExecution], Any]],
    turn_execution: Optional[TurnExecution],
) -> None:
    if not continuation.record_operations(calls_executed):
        return
    if callback is None or turn_execution is None:
        return
    result = callback(turn_execution)
    if inspect.isawaitable(result):
        await result


async def execute_tool_call(
    function_name: str,
    function_args: Dict[str, Any],
    tool_call_id: str,
    available_tools: Dict[str, Any],
    conversation_history: List[Dict],
    stats: Any,
    ui: UIManager,
    console: Console,
    *,
    suppress_tool_loading: bool = False,
    turn_execution: Optional[TurnExecution] = None,
    capability_audit: CapabilityAuditSink | None = None,
) -> Tuple[Any, float]:
    """Public function-calling entrypoint for the canonical CLI tool engine."""
    execution_kwargs: dict[str, Any] = {
        "suppress_tool_loading": suppress_tool_loading,
        "turn_execution": turn_execution,
    }
    if capability_audit is not None:
        execution_kwargs["capability_audit"] = capability_audit
    return await tool_execution.execute_tool_call(
        function_name,
        function_args,
        tool_call_id,
        available_tools,
        conversation_history,
        stats,
        ui,
        console,
        **execution_kwargs,
    )


def _check_rate_limit_suppression(quota_msg: str) -> bool:
    """Return True if this quota message should be suppressed (shown recently)."""
    global _last_error_message, _last_error_time
    with _globals_lock:
        current_time = time.time()
        if (
            _last_error_message == quota_msg
            and current_time - _last_error_time < _ERROR_SUPPRESSION_WINDOW
        ):
            return True
        _last_error_message = quota_msg
        _last_error_time = current_time
    return False


async def _handle_tool_calls(
    tool_calls: list,
    available_tools: Dict[str, Any],
    conversation_history: List[Dict],
    stats: Any,
    ui: Any,
    console: Any,
    suppress_tool_loading: bool,
    function_call_count: int,
    *,
    turn_execution: Optional[TurnExecution],
) -> int:
    """Execute all tool calls from a single LLM response. Returns updated call count."""
    # Reflect tool execution in stats so status_bar shows 'executing' instead of 'thinking'
    if hasattr(stats, "set_status"):
        stats.set_status("executing", "Executando ferramentas...")

    for tool_call in tool_calls:
        function_name, function_args_str, tool_call_id = (
            response_parser.extract_tool_call_data(tool_call, function_call_count)
        )
        function_args = json.loads(function_args_str) if function_args_str else {}
        if not isinstance(function_name, str) or not function_name:
            logger.warning(
                f"Invalid tool call: function_name must be a non-empty string, got {type(function_name)}"
            )
            continue
        if not isinstance(function_args, dict):
            logger.warning(
                f"Invalid tool call args for {function_name}: expected dict, got {type(function_args)}"
            )
            function_args = {}
        function_call_count += 1
        try:
            await execute_tool_call(
                function_name,
                function_args,
                tool_call_id,
                available_tools,
                conversation_history,
                stats,
                ui,
                console,
                suppress_tool_loading=suppress_tool_loading,
                turn_execution=turn_execution,
            )
        except KeyError as e:
            logger.debug(f"Ferramenta não encontrada (ignorando): {e}")
            from aura_cli.cli.ui.components.turn_separator import ToolCallInline

            ui.print(
                ToolCallInline().render(function_name, function_args, status="error")
            )
            tool_execution._append_tool_interaction_to_history(
                conversation_history,
                function_name,
                function_args,
                tool_call_id,
                f"Erro: ferramenta '{function_name}' não encontrada.",
            )
        except (ToolExecutionError, FileOperationError, LLMError) as e:
            logger.warning(
                f"Error processing function call, continuing: {e}", exc_info=True
            )
            from aura_cli.cli.ui.components.turn_separator import ToolCallInline

            ui.print(
                ToolCallInline().render(function_name, function_args, status="error")
            )
            tool_execution._append_tool_interaction_to_history(
                conversation_history,
                function_name,
                function_args,
                tool_call_id,
                f"Error executing {function_name}: {getattr(e, 'message', str(e))}",
            )
        except Exception as e:
            logger.error(
                f"Erro inesperado ao processar function call: {e}", exc_info=True
            )
            tool_execution._append_tool_interaction_to_history(
                conversation_history,
                function_name,
                function_args,
                tool_call_id,
                f"Erro inesperado ao executar {function_name}: {e}",
            )
    return function_call_count


def _handle_rate_limit_error(e: RateLimitError) -> Tuple[str, None]:
    """Convert RateLimitError to user-friendly message."""
    resolution = resolve_provider_error(
        e,
        rate_limit=True,
        retry_after=e.retry_after,
        model=e.model,
    )
    if resolution.suppression_key and _check_rate_limit_suppression(
        resolution.suppression_key
    ):
        return "__SUPPRESSED__", None
    return resolution.message, None


def _handle_leaked_key() -> Tuple[str, None]:
    """Revoke a leaked API key and return an error message."""
    try:
        import keyring

        from aura_cli.core.secure_config import secure_config_manager

        try:
            keyring.delete_password("aura_cli", "google_api_key")
        except Exception as ke:
            logger.warning(f"Failed to remove key from keyring: {ke}")
        try:
            secure_config_manager.delete_api_key("google")
        except Exception as se:
            logger.warning(f"Failed to remove key from SecureConfig: {se}")
        for env_key in ["GOOGLE_API_KEY", "GEMINI_API_KEY"]:
            os.environ.pop(env_key, None)
        logger.info("Chave vazada removida automaticamente")
    except Exception as re_err:
        logger.warning(f"Failed to remove leaked key: {re_err}")
    return (
        "▲ Chave de API inválida\n\nChave desativada por segurança.\n\n▪ Tente: /settings para nova chave",
        None,
    )


async def _llm_call_with_learning(
    model: str,
    conversation_history: List[Dict],
    tool_schemas: List[Dict],
    turn_execution: Optional[TurnExecution] = None,
) -> Any:
    """Execute LLM call and record learning decision."""

    def observe(event: Dict[str, Any]) -> None:
        if turn_execution is None:
            return
        if event["event"] == "start":
            turn_execution.llm_calls.append(
                LLMCallRecord(
                    **{key: value for key, value in event.items() if key != "event"}
                )
            )
            return
        record = next(
            item
            for item in reversed(turn_execution.llm_calls)
            if item.llm_call_id == event["llm_call_id"]
        )
        record.status = event["event"]
        record.finished_at = utc_now()
        record.duration = event.get("duration")
        record.error = event.get("error")

    response = await asyncio.to_thread(
        query_with_fallback,
        model,
        conversation_history,
        tools=tool_schemas,
        event_callback=observe,
    )
    try:
        from aura_cli.core.llm.multi_model_advanced import (
            AdvancedMultiModelIntelligence,
        )

        _mmi = AdvancedMultiModelIntelligence(enable_learning=True, enable_cache=False)
        _mmi.learner.record_decision(
            task_type="general",
            models_used=[model],
            selected_model=model,
        )
    except Exception as _e:
        logger.debug(f"Ignorado: {_e}")
    return response


def _handle_llm_call_error(e: Exception) -> Optional[Tuple[str, Any]]:
    """Map LLM call exceptions to user-facing messages. Returns (msg, None) or None to re-raise."""
    if isinstance(e, RateLimitError):
        return _handle_rate_limit_error(e)
    resolution = resolve_provider_error(e)
    if resolution.kind is ProviderErrorKind.CONNECTION:
        logger.warning(f"Erro de conexão com LLM: {e}")
    elif resolution.kind is ProviderErrorKind.INVALID_REQUEST:
        logger.error(f"Requisição inválida ao LLM: {e}", exc_info=True)
    elif resolution.kind in {
        ProviderErrorKind.AUTHENTICATION,
        ProviderErrorKind.LEAKED_CREDENTIAL,
    }:
        logger.warning(f"Erro de chave de API: {e}")
    elif resolution.kind is ProviderErrorKind.MODEL_NOT_FOUND:
        logger.warning(f"Model not found: {e}")
    elif resolution.kind is ProviderErrorKind.RATE_LIMIT:
        logger.debug(f"Rate limit (generic): {str(e)[:60]}")
    else:
        logger.warning(f"Erro LLM: {e}")

    if resolution.suppression_key and _check_rate_limit_suppression(
        resolution.suppression_key
    ):
        return "__SUPPRESSED__", None
    if resolution.revoke_credentials:
        _handle_leaked_key()
    return resolution.message, None


async def process_function_calls_loop(
    model: str,
    conversation_history: List[Dict],
    tool_schemas: List[Dict],
    available_tools: Dict[str, Any],
    stats: Any,
    ui: UIManager,
    console: Console,
    max_calls: int = 5,
    shutdown_event: Optional[threading.Event] = None,
    *,
    suppress_tool_loading: bool = False,
    turn_execution: Optional[TurnExecution] = None,
    user_request: Optional[str] = None,
    continuation: Optional[ContinuationController] = None,
    checkpoint_callback: Optional[Callable[[TurnExecution], Any]] = None,
) -> Tuple[str, Any]:
    """Process function call loop until final response obtained.

    When suppress_tool_loading is True, tool executions do not show their own
    spinner (avoids nested spinners when already inside "Generating response...").
    """
    global _last_error_message, _last_error_time
    budget = FunctionLoopBudget(maximum=max_calls)
    response = None
    claim_repair_attempted = False
    continuation = continuation or ContinuationController()

    # Activate workspace to group tool calls for this round
    from aura_cli.cli.ui.components.agent_workspace import AgentWorkspacePanel

    workspace = AgentWorkspacePanel(turn_execution=turn_execution)
    tool_execution.set_active_workspace(workspace)
    # Expose active history so vision tools can inject multimodal messages
    from aura_cli.core.execution_context import set_active_conversation_history
    set_active_conversation_history(conversation_history)

    try:
        while budget.available:
            stop_reason = continuation.begin_iteration()
            if stop_reason is not None:
                return stop_message(stop_reason), response
            if shutdown_event and shutdown_event.is_set():
                return stop_message(TurnStopReason.USER), None

            # --- LLM call ---
            try:
                response = await _llm_call_with_learning(
                    model, conversation_history, tool_schemas, turn_execution
                )
            except Exception as e:
                result = _handle_llm_call_error(e)
                if result is not None:
                    return result
                raise

            has_choices = bool(response and getattr(response, "choices", None))
            message = response.choices[0].message if has_choices else None
            tool_calls = response_parser.parse_tool_calls(message) if message else None
            content = getattr(message, "content", None) if message else None
            action = decide_function_loop_action(
                has_response=bool(response),
                has_choices=has_choices,
                tool_call_count=len(tool_calls or ()),
                content=content,
                has_tool_schemas=bool(tool_schemas),
            )

            if action is FunctionLoopAction.EMPTY_RESPONSE:
                return (
                    "▲ Resposta vazia do modelo\n\nO modelo não retornou resposta.\n\n▪ Tente: aguardar e tentar de novo, /model",
                    None,
                )
            if action is FunctionLoopAction.INVALID_RESPONSE:
                return (
                    "▲ Resposta inválida do modelo\n\nResposta sem conteúdo válido.\n\n▪ Tente: /model",
                    response,
                )

            if action is FunctionLoopAction.EXECUTE_TOOLS:
                new_count = await _handle_tool_calls(
                    tool_calls or [],
                    available_tools,
                    conversation_history,
                    stats,
                    ui,
                    console,
                    suppress_tool_loading,
                    budget.consumed,
                    turn_execution=turn_execution,
                )
                calls_executed = new_count - budget.consumed
                budget.consume(calls_executed)
                await _emit_checkpoint_if_due(
                    continuation,
                    calls_executed,
                    checkpoint_callback,
                    turn_execution,
                )
                if hasattr(stats, "set_status"):
                    stats.set_status("thinking", "Pensando...")
                continue

            if action is FunctionLoopAction.RETRY_WITHOUT_TOOLS:
                # Nemotron (and some models) returns content=None with tool_calls=[]
                # when it receives many tools but does not need to use any.
                # Retry without tools to force a text response.
                logger.debug(
                    "content=None com tool_calls vazio — retry sem ferramentas"
                )
                try:
                    response = await asyncio.to_thread(
                        query_with_fallback,
                        model,
                        conversation_history,
                    )
                    if response and hasattr(response, "choices") and response.choices:
                        content = response.choices[0].message.content
                except Exception as _e:
                    logger.debug(f"Retry sem ferramentas falhou: {_e}")

            final_content = content if content else "Resposta vazia."
            final_content, retry_claim = _guard_completion_claims(
                content=final_content,
                user_request=user_request,
                turn_execution=turn_execution,
                conversation_history=conversation_history,
                repair_attempted=claim_repair_attempted,
            )
            if retry_claim:
                claim_repair_attempted = True
                continue

            # Tools already shown inline in real-time
            return final_content, response
        return stop_message(TurnStopReason.BUDGET), response
    finally:
        tool_execution.set_active_workspace(None)
        from aura_cli.core.execution_context import clear_execution_context
        clear_execution_context()
        if workspace.has_entries:
            ui.print(
                workspace.render(
                    expanded=bool(turn_execution and turn_execution.failures)
                )
            )
