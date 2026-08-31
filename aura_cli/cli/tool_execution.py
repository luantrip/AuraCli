"""Tool execution engine for function calls.

This module handles the actual execution of tool calls including:
    - Security audit and confirmation checks
    - Diff confirmation for write operations
    - Tool interceptor hooks (before/after)
    - Policy checks
    - Auto-checkpointing
    - Result formatting and history management
"""

import os
import subprocess
import threading
import time
from typing import Any, Dict, List, Optional, Tuple

import rich.box
from rich.console import Console, Group
from rich.panel import Panel
from rich.text import Text

from aura_cli.application.conversation import append_tool_interaction
from aura_cli.application.diffs import generate_new_file_diff, generate_unified_diff
from aura_cli.application.execution import TurnExecution
from aura_cli.application.presentation.safe_payloads import (
    safe_tool_args_json,
    sanitize_intervention_context,
)
from aura_cli.application.tools import (
    GuardDecision,
    ToolExecutionPipeline,
    ToolExecutionRequest,
    append_python_syntax_diagnostic,
    format_tool_result,
)
from aura_cli.application.tools.capability_broker import (
    CapabilityDecision,
    decide_tool_capability,
)
from aura_cli.application.tools.execution_policy import get_execution_policy
from aura_cli.cli.ui.components.tool_result import ToolResult
from aura_cli.cli.ui.constants import UIIcons, UIStyles
from aura_cli.cli.ui.loading_states import LoadingState, show_tool_loading
from aura_cli.cli.ui.manager import UIManager
from aura_cli.cli.utils.exceptions import (
    FileOperationError,
    ToolExecutionError,
)
from aura_cli.contracts.security import CapabilityAuditSink, ToolAccessDecision
from aura_cli.core.logger import get_logger
from aura_cli.core.stats import get_stats

logger = get_logger(__name__)

DIFF_CONFIRMATION_ENABLED = True
WRITE_TOOLS = {"write_file", "edit_file", "replace_in_file"}
_globals_lock = threading.Lock()

# Active workspace for this round — accumulates tool calls instead of printing inline
_active_workspace: Optional[Any] = None

try:
    from aura_cli.core.events.human_intervention_events import (
        InterventionContext,
        RiskLevel,
    )
    from aura_cli.core.tools.human_intervention_adapter import (
        HumanInterventionAdapter,
        InterventionHelper,
    )

    INTERVENTION_AVAILABLE = True
except ImportError:
    INTERVENTION_AVAILABLE = False
    HumanInterventionAdapter = None  # type: ignore[assignment,misc]
    InterventionHelper = None  # type: ignore[assignment,misc]
    InterventionContext = None  # type: ignore[assignment,misc]
    RiskLevel = None  # type: ignore[assignment,misc]


# Lazy singletons for ToolInterceptor and PolicyManager (INFRA-NEW-05)
_tool_interceptor = None
_policy_manager = None


def _get_tool_interceptor():
    """Return shared ToolInterceptor instance (lazy init)."""
    global _tool_interceptor
    if _tool_interceptor is None:
        with _globals_lock:
            if _tool_interceptor is None:
                try:
                    from aura_cli.core.agents.tool_calling.tool_interceptor import (
                        ToolInterceptor,
                    )

                    _tool_interceptor = ToolInterceptor()
                except Exception as _e:
                    logger.debug(f"ToolInterceptor não disponível: {_e}")
    return _tool_interceptor


def _get_policy_manager():
    """Return shared PolicyManager instance (lazy init)."""
    global _policy_manager
    if _policy_manager is None:
        with _globals_lock:
            if _policy_manager is None:
                try:
                    from aura_cli.core.agents.tool_calling.tool_policies import (
                        PolicyManager,
                    )

                    _policy_manager = PolicyManager()
                except Exception as _e:
                    logger.debug(f"PolicyManager não disponível: {_e}")
    return _policy_manager


try:
    from aura_cli.core.service_registry import (
        ServiceRegistry,
        get_service_registry,
    )
except ImportError:
    ServiceRegistry = None  # type: ignore[assignment,misc]
    get_service_registry = None  # type: ignore[assignment]

try:
    from aura_cli.core.hooks import HookEvent, HookManager

    _hook_manager: Optional["HookManager"] = None

    def set_hook_manager(manager: Optional["HookManager"]) -> None:
        """Register the canonical hook manager used by the runtime."""
        global _hook_manager
        _hook_manager = manager

    def get_hook_manager() -> Optional["HookManager"]:
        """Return the canonical hook manager when available."""
        return _hook_manager

except ImportError:
    HookManager = None  # type: ignore[assignment,misc]
    HookEvent = None  # type: ignore[assignment,misc]
    set_hook_manager = None  # type: ignore[assignment]
    get_hook_manager = None  # type: ignore[assignment]


_intervention_adapter: Optional[Any] = None


def set_intervention_adapter(adapter: Any):
    """Set human intervention adapter for use in function calls.

    Args:
        adapter: HumanInterventionAdapter instance
    """
    global _intervention_adapter
    _intervention_adapter = adapter
    logger.debug("Intervention adapter configurado para function_call_handler")


def get_intervention_adapter() -> Optional[Any]:
    """Return current human intervention adapter."""
    return _intervention_adapter


def get_active_workspace() -> Optional[Any]:
    """Return the currently active workspace panel."""
    with _globals_lock:
        return _active_workspace


def set_active_workspace(workspace: Optional[Any]) -> None:
    """Set the active workspace panel."""
    global _active_workspace
    with _globals_lock:
        _active_workspace = workspace


def _emit_capability_audit(
    ui: Optional[UIManager],
    function_name: str,
    decision: CapabilityDecision,
    *,
    task_id: str | None = None,
    phase: str,
    capability_audit: CapabilityAuditSink | None = None,
) -> None:
    """Publish an optional structured capability event without rendering."""
    if callable(capability_audit):
        try:
            capability_audit(
                function_name,
                decision,
                task_id=task_id,
                phase=phase,
            )
            return
        except Exception as error:
            logger.debug("Capability audit sink failed: %s", error)
    emitter = getattr(ui, "emit_capability_decision", None)
    if not callable(emitter):
        return
    try:
        emitter(function_name, decision, task_id=task_id, phase=phase)
    except Exception as error:
        logger.debug("Capability audit emission failed: %s", error)


def _present_capability_decision(
    ui: Optional[UIManager],
    function_name: str,
    decision: CapabilityDecision,
    *,
    task_id: str | None = None,
    phase: str = "blocked",
    capability_audit: CapabilityAuditSink | None = None,
) -> None:
    """Render a blocked capability through UI adapters that support it."""
    _emit_capability_audit(
        ui,
        function_name,
        decision,
        task_id=task_id,
        phase=phase,
        capability_audit=capability_audit,
    )
    capability_presenter = getattr(ui, "display_capability_decision", None)
    if callable(capability_presenter):
        try:
            capability_presenter(function_name, decision, task_id=task_id)
            return
        except Exception as error:
            logger.debug("Capability decision presentation failed: %s", error)
    warning_presenter = getattr(ui, "display_warning", None)
    if callable(warning_presenter):
        warning_presenter(f"Execução de {function_name} bloqueada: {decision.reason}")


def _reject_capability(
    ui: Optional[UIManager],
    function_name: str,
    decision: CapabilityDecision,
    policy: Any,
    *,
    phase: str = "blocked",
    capability_audit: CapabilityAuditSink | None = None,
) -> bool:
    """Log and present a denied capability without allowing execution."""
    logger.warning(
        "%s task_id=%s",
        decision.reason,
        policy.task_id if policy else "interactive",
    )
    _present_capability_decision(
        ui,
        function_name,
        decision,
        task_id=policy.task_id if policy else None,
        phase=phase,
        capability_audit=capability_audit,
    )
    return False


def _check_capability_access(
    ui: Optional[UIManager],
    function_name: str,
    policy: Any,
    *,
    access_allowed: bool,
    access_reason: str | None,
    capability_audit: CapabilityAuditSink | None = None,
) -> bool:
    """Apply access denial through the same explainable capability decision."""
    if access_allowed:
        return True
    decision = decide_tool_capability(
        None,
        policy=policy,
        adapter_available=_intervention_adapter is not None,
        access_allowed=False,
        access_reason=access_reason,
    )
    return _reject_capability(
        ui,
        function_name,
        decision,
        policy,
        capability_audit=capability_audit,
    )


def _announce_risky_tool(
    function_name: str,
    risk_level: Any,
    console: Console,
    ui: Optional[UIManager],
) -> None:
    """Show the existing high-impact banner in the selected UI surface."""
    if risk_level == RiskLevel.CRITICAL:
        message = f"[bold red]▲  OPERAÇÃO CRÍTICA: {function_name}[/bold red]"
    elif risk_level == RiskLevel.HIGH:
        message = (
            f"[bold yellow]🔶 Operação de alto impacto: {function_name}[/bold yellow]"
        )
    else:
        return
    if ui is not None:
        ui.print(message)
    else:
        console.print(message)


def _request_tool_confirmation(
    prompt: str,
    context: Any,
    timeout_sec: float,
) -> bool:
    """Request confirmation through the configured adapter or CLI prompt."""
    safe_context = sanitize_intervention_context(context)
    if _intervention_adapter:
        return _intervention_adapter.request_confirmation(
            prompt=prompt,
            context=safe_context,
            default=False,
            timeout=timeout_sec,
        )

    from aura_cli.cli.ui.components.confirmation import ask_confirmation

    context_str = None
    if context and (context.tool_name or context.tool_args):
        context_str = f"Ferramenta: {context.tool_name or 'N/A'}"
        if context.tool_args:
            try:
                context_str += "\nArgumentos: " + safe_tool_args_json(context.tool_args)
            except Exception:
                context_str += "\nArgumentos: [oculto]"
    return ask_confirmation(
        message=prompt,
        default=False,
        context=context_str,
        timeout=timeout_sec,
    )


def _report_confirmation_cancelled(
    function_name: str, console: Console, ui: Optional[UIManager]
) -> None:
    """Report a user-declined confirmation through the selected UI surface."""
    message = f"Execução de {function_name} cancelada pelo usuário."
    if ui is not None:
        ui.display_warning(message)
    else:
        console.print(
            f"[{UIStyles.WARNING}]{UIIcons.CANCEL} {message}[/{UIStyles.WARNING}]"
        )


def _risk_without_intervention(
    function_name: str, function_args: Dict[str, Any]
) -> tuple[Any | None, bool]:
    """Resolve declared tool risk when the optional intervention layer is absent."""
    del function_args  # Registry metadata is independent of runtime arguments.
    if callable(get_service_registry):
        try:
            registry = get_service_registry()
            descriptor = (
                registry.get_tool(function_name) if registry is not None else None
            )
            risk = getattr(descriptor, "risk", None)
            if risk:
                return risk, True
        except Exception as error:
            logger.warning(
                "Não foi possível classificar risco de %s sem intervenção: %s",
                function_name,
                error,
            )
    return None, False


def _check_tool_requires_confirmation(
    function_name: str,
    function_args: Dict[str, Any],
    console: Console,
    ui: Optional[UIManager] = None,
    *,
    access_allowed: bool = True,
    access_reason: str | None = None,
    capability_audit: CapabilityAuditSink | None = None,
) -> bool:
    """Check if tool requires confirmation and request from user.

    Evaluates tool risk level and prompts user for confirmation if needed.
    Critical operations require explicit approval. When no intervention
    adapter is set (main-thread chat), uses ask_confirmation() so the user
    is always prompted for dangerous tools.
    """
    policy = get_execution_policy()
    if not _check_capability_access(
        ui,
        function_name,
        policy,
        access_allowed=access_allowed,
        access_reason=access_reason,
        capability_audit=capability_audit,
    ):
        return False

    if not INTERVENTION_AVAILABLE:
        risk_level, classified = _risk_without_intervention(
            function_name, function_args
        )
        if not classified:
            decision = CapabilityDecision(
                allowed=False,
                requires_confirmation=False,
                reason=(
                    "Operação rejeitada: camada de intervenção e classificação "
                    "de risco indisponíveis."
                ),
                risk_level=risk_level,
            )
        else:
            decision = decide_tool_capability(
                risk_level,
                policy=policy,
                adapter_available=False,
                access_allowed=access_allowed,
                access_reason=access_reason,
            )
            if decision.allowed and decision.requires_confirmation:
                decision = CapabilityDecision(
                    allowed=False,
                    requires_confirmation=False,
                    reason=(
                        "Operação requer confirmação explícita, mas a camada de "
                        "intervenção está indisponível."
                    ),
                    risk_level=risk_level,
                )
        if not decision.allowed:
            return _reject_capability(
                ui,
                function_name,
                decision,
                policy,
                capability_audit=capability_audit,
            )
        _emit_capability_audit(
            ui,
            function_name,
            decision,
            task_id=policy.task_id if policy else None,
            phase="evaluation",
            capability_audit=capability_audit,
        )
        return decision.allowed

    confirmation_request = InterventionHelper.build_tool_confirmation_request(
        function_name,
        function_args,
    )
    if confirmation_request is None:
        decision = decide_tool_capability(
            None,
            policy=policy,
            adapter_available=_intervention_adapter is not None,
            access_allowed=access_allowed,
            access_reason=access_reason,
        )
        _emit_capability_audit(
            ui,
            function_name,
            decision,
            task_id=policy.task_id if policy else None,
            phase="evaluation",
            capability_audit=capability_audit,
        )
        return decision.allowed
    risk_level, context, prompt, timeout_sec = confirmation_request
    decision = decide_tool_capability(
        risk_level,
        policy=policy,
        adapter_available=_intervention_adapter is not None,
        access_allowed=access_allowed,
        access_reason=access_reason,
    )
    if not decision.allowed:
        return _reject_capability(
            ui,
            function_name,
            decision,
            policy,
            capability_audit=capability_audit,
        )
    _emit_capability_audit(
        ui,
        function_name,
        decision,
        task_id=policy.task_id if policy else None,
        phase="evaluation",
        capability_audit=capability_audit,
    )
    if not decision.requires_confirmation:
        return True

    _emit_capability_audit(
        ui,
        function_name,
        decision,
        task_id=policy.task_id if policy else None,
        phase="confirmation",
        capability_audit=capability_audit,
    )
    _announce_risky_tool(function_name, risk_level, console, ui)
    approved = _request_tool_confirmation(prompt, context, timeout_sec)
    if not approved:
        _report_confirmation_cancelled(function_name, console, ui)
    return approved


def _generate_diff_lines(file_path: str, new_content: str) -> list:
    """Generate diff lines for a file change."""
    try:
        if os.path.exists(file_path):
            with open(file_path, encoding="utf-8") as f:
                old_content = f.read()
            return generate_unified_diff(file_path, old_content, new_content)
        return generate_new_file_diff(file_path, new_content)
    except (OSError, UnicodeDecodeError) as e:
        logger.warning(f"Não foi possível gerar diff: {e}", exc_info=True)
    except Exception as e:
        logger.error(f"Erro inesperado ao gerar diff: {e}", exc_info=True)
    return []


def _build_diff_header(file_path: str, diff_lines: list) -> Text:
    """Build the diff panel header text."""
    additions = sum(
        1 for line in diff_lines if line.startswith("+") and not line.startswith("+++")
    )
    deletions = sum(
        1 for line in diff_lines if line.startswith("-") and not line.startswith("---")
    )
    header = Text()
    header.append("Arquivo: ", style="dim")
    header.append(file_path, style="bold cyan")
    if additions > 0:
        header.append(f"  +{additions}", style="green")
    if deletions > 0:
        header.append(f"  -{deletions}", style="red")
    return header


def _build_diff_content(diff_lines: list, max_lines: int = 15) -> list:
    """Build Rich Text objects for diff content display."""
    diff_content = []
    line_count = 0
    for i, line in enumerate(diff_lines):
        if line.startswith(("+++", "---", "@@")):
            continue
        if line_count >= max_lines:
            remaining = sum(
                1 for line in diff_lines[i:] if not line.startswith(("+++", "---"))
            )
            if remaining > 0:
                diff_content.append(
                    Text(f"  … truncated ({remaining} more lines)", style="dim")
                )
            break
        escaped = line.replace("[", "\\[").replace("]", "\\]")
        diff_line = Text()
        if line.startswith("+"):
            diff_line.append("  ", style="dim")
            diff_line.append("+ ", style="green")
            diff_line.append(escaped[1:], style="green")
        elif line.startswith("-"):
            diff_line.append("  ", style="dim")
            diff_line.append("- ", style="red")
            diff_line.append(escaped[1:], style="red")
        elif line.strip():
            diff_line.append("  ", style="dim")
            diff_line.append(escaped, style="dim")
        if diff_line:
            diff_content.append(diff_line)
            line_count += 1
    return diff_content


def _prompt_user_action(console: Console, stats: Any) -> Tuple[bool, str]:
    """Prompt user to accept/reject diff. Returns (should_execute, action)."""
    try:
        from rich.prompt import Prompt

        result = (
            Prompt.ask(
                f"[{UIStyles.PRIMARY}][A]ceitar / [R]ejeitar / Aceitar [T]odos?[/{UIStyles.PRIMARY}]",
                default="",
            )
            .strip()
            .lower()
        )
        if result in ["a", "aceitar", "y", "yes", "s", "sim", ""]:
            return True, "accept"
        if result in ["t", "todos", "all"]:
            policy = get_execution_policy()
            if policy is not None:
                policy.auto_confirm = True
            else:
                stats.skip_confirmations = True
            return True, "accept_all"
        return False, "reject"
    except (EOFError, KeyboardInterrupt):
        return False, "reject"
    except Exception as e:
        logger.error(
            "Error getting user input; operation rejected: %s",
            e,
            exc_info=True,
        )
        return False, "reject"


async def _show_diff_confirmation(
    function_name: str,
    function_args: Dict[str, Any],
    ui: UIManager,
    console: Console,
) -> Tuple[bool, Optional[str]]:
    """Show diff confirmation for write operations.

    Displays a diff preview and asks user for confirmation before
    applying file changes. Supports accept, reject, and accept_all.

    Args:
        function_name: Tool name (write_file, edit_file, etc.)
        function_args: Tool arguments with file path and content
        ui: The UIManager instance, used to push screens in TUI mode.
        console: Rich Console for output

    Returns:
        Tuple (should_execute, action):
            - should_execute: True if operation should proceed
            - action: User action ("accept", "reject", "accept_all", None)
    """
    stats = get_stats()
    policy = get_execution_policy()

    if policy and policy.auto_confirm and not policy.confirm_writes:
        return True, "accept"
    if policy is None and stats.skip_confirmations:
        return True, "accept"

    file_path = function_args.get("path") or function_args.get("file_path", "")
    new_content = function_args.get("content") or function_args.get("new_string", "")

    if not file_path:
        return True, None

    diff_lines = _generate_diff_lines(file_path, new_content)

    if hasattr(ui, "push_screen_wait") or getattr(ui, "app", None):
        try:
            from aura_cli.interface_runtime import open_diff_confirmation

            action = await open_diff_confirmation(
                ui,
                file_path=file_path,
                diff_lines=diff_lines,
                new_content=new_content,
            )
            if action == "accept_all":
                if policy is not None:
                    policy.auto_confirm = True
                else:
                    stats.skip_confirmations = True
            return action in ["accept", "accept_all"], action
        except (ImportError, AttributeError, RuntimeError) as e:
            logger.error(
                f"Failed to use TUI diff screen, using terminal: {e}", exc_info=True
            )
        except Exception as e:
            logger.error(f"Erro inesperado na tela de diff TUI: {e}", exc_info=True)

    diff_content = _build_diff_content(diff_lines)
    panel_content = (
        Group(*diff_content) if diff_content else Text("  No changes", style="dim")
    )
    console.print()
    console.print(
        Panel(
            panel_content,
            title=_build_diff_header(file_path, diff_lines),
            border_style="cyan",
            padding=(0, 1),
            expand=False,
            box=rich.box.ROUNDED,
        )
    )
    return _prompt_user_action(console, stats)


def _format_tool_result_for_model(result: Any, function_name: str = "") -> str:
    """Compatibility adapter for provider-facing result formatting."""
    return format_tool_result(result)


def _append_tool_interaction_to_history(
    conversation_history: List[Dict],
    function_name: str,
    function_args: Dict[str, Any],
    tool_call_id: str,
    tool_content: str,
) -> None:
    """Append a tool call and tool result message to model conversation history."""
    append_tool_interaction(
        conversation_history,
        name=function_name,
        arguments=function_args,
        call_id=tool_call_id,
        content=tool_content,
    )


async def _run_hooks(
    hook_manager: Any, hook_event: Any, payload: dict, label: str
) -> None:
    """Execute hook_manager hooks, logging but not raising on failure."""
    if hook_manager is None:
        return
    try:
        await hook_manager.trigger(hook_event, payload)
    except (AttributeError, TypeError) as e:
        logger.warning(f"Error executing hooks {label}: {e}", exc_info=True)
    except Exception as e:
        logger.error(f"Erro inesperado ao executar hooks {label}: {e}", exc_info=True)


def _run_ops_audit(function_name: str, function_args: dict, console: Any) -> bool:
    """Return False if the tool call should be blocked by security audit."""
    try:
        from aura_cli.core.ops_tools.security.ops_auditor import (
            audit_tool_call,
            format_audit_warning,
        )

        audit = audit_tool_call(function_name, function_args)
        if audit.blocked:
            from aura_cli.cli.ui.components.confirmation import ask_confirmation

            console.print(f"[bold yellow]{format_audit_warning(audit)}[/bold yellow]")
            if not ask_confirmation(
                f"Executar '{function_name}' ({audit.risk_level.value} risk)?"
            ):
                return False
    except Exception as _e:
        logger.error("Auditoria de segurança indisponível; operação bloqueada: %s", _e)
        return False
    return True


def _try_auto_checkpoint(function_name: str, function_args: dict) -> None:
    """Create an auto-checkpoint before a write tool, silently ignoring failures."""
    try:
        from aura_cli.core.tools.checkpoint_tools import (
            _checkpoint_manager,
            create_checkpoint,
        )

        if _checkpoint_manager and _checkpoint_manager._initialized:
            file_path = (
                function_args.get("path") or function_args.get("file_path") or "unknown"
            )
            create_checkpoint(f"Auto-checkpoint before {function_name}: {file_path}")
    except Exception as e:
        logger.debug(f"Auto-checkpoint ignorado: {e}")


def _call_tool(
    function_name: str, function_args: dict, available_tools: dict, registry: Any
) -> Any:
    """Dispatch tool call through registry, ToolCaller, or direct invocation."""
    if registry and registry.get_tool(function_name) is not None:
        return registry.execute_tool(function_name, function_args)
    try:
        from aura_cli.core.agents.tool_calling.tool_caller import (
            CallStrategy,
            ToolCaller,
        )

        call_result = ToolCaller(max_retries=2, timeout=30.0, enable_cache=False).call(
            function_name,
            available_tools[function_name],
            function_args,
            strategy=CallStrategy.RETRY,
        )
        if call_result.success:
            return call_result.result
        raise ToolExecutionError(
            tool_name=function_name,
            message=call_result.error or f"Ferramenta '{function_name}' falhou",
        )
    except ImportError:
        return available_tools[function_name](**function_args)


def _evaluate_policy_access(
    function_name: str, function_args: dict
) -> tuple[bool, str | None]:
    """Return a pure access result for the capability decision broker."""
    policy = get_execution_policy()
    policy_manager = _get_policy_manager()
    if policy_manager is None:
        if policy and policy.fail_closed_policy_errors:
            return False, "Não foi possível avaliar a política da ferramenta."
        return True, None
    try:
        typed_evaluator = getattr(type(policy_manager), "evaluate_access", None)
        if callable(typed_evaluator):
            access = policy_manager.evaluate_access(
                function_name, "cli_agent", function_args
            )
        else:
            allowed, reason = policy_manager.check_access(
                function_name, "cli_agent", function_args
            )
            access = ToolAccessDecision(allowed=allowed, reason=reason)
        if not isinstance(access, ToolAccessDecision):
            raise TypeError("resultado de acesso incompatível")
        if not access.allowed:
            return False, f"Acesso negado pela política: {access.reason}"
        return True, access.reason
    except Exception as error:
        if policy and policy.fail_closed_policy_errors:
            return False, "Failed to evaluate tool policy."
        logger.debug("PolicyManager check ignorado: %s", error)
        return True, None


def _commit_policy_access(
    function_name: str,
    function_args: dict,
    ui: Optional[UIManager] = None,
    capability_audit: CapabilityAuditSink | None = None,
) -> None:
    """Consume a rate-limit slot immediately before the tool call."""
    policy = get_execution_policy()
    policy_manager = _get_policy_manager()
    if policy_manager is None:
        if policy and policy.fail_closed_policy_errors:
            decision = CapabilityDecision(
                allowed=False,
                requires_confirmation=False,
                reason="Não foi possível avaliar a política da ferramenta.",
            )
            _present_capability_decision(
                ui,
                function_name,
                decision,
                task_id=policy.task_id if policy else None,
                phase="commit",
                capability_audit=capability_audit,
            )
            raise ToolExecutionError(
                tool_name=function_name,
                message=decision.reason,
            )
        return

    typed_committer = getattr(type(policy_manager), "commit_access", None)
    if not callable(typed_committer):
        return
    try:
        access = policy_manager.commit_access(function_name, "cli_agent", function_args)
        if not isinstance(access, ToolAccessDecision):
            raise TypeError("resultado de commit incompatível")
        if not access.allowed:
            decision = CapabilityDecision(
                allowed=False,
                requires_confirmation=False,
                reason=f"Acesso negado pela política: {access.reason}",
            )
            _present_capability_decision(
                ui,
                function_name,
                decision,
                task_id=policy.task_id if policy else None,
                phase="commit",
                capability_audit=capability_audit,
            )
            raise ToolExecutionError(
                tool_name=function_name,
                message=decision.reason,
            )
        _emit_capability_audit(
            ui,
            function_name,
            CapabilityDecision(
                allowed=True,
                requires_confirmation=False,
                reason="Rate limit reservado para execução.",
            ),
            task_id=policy.task_id if policy else None,
            phase="commit",
            capability_audit=capability_audit,
        )
    except ToolExecutionError:
        raise
    except Exception as error:
        if policy and policy.fail_closed_policy_errors:
            decision = CapabilityDecision(
                allowed=False,
                requires_confirmation=False,
                reason="Failed to confirm tool policy.",
            )
            _present_capability_decision(
                ui,
                function_name,
                decision,
                task_id=policy.task_id if policy else None,
                phase="commit",
                capability_audit=capability_audit,
            )
            raise ToolExecutionError(
                tool_name=function_name,
                message=decision.reason,
                original_error=error,
            ) from error
        logger.debug("PolicyManager commit ignorado: %s", error)


def _run_policy_check(function_name: str, function_args: dict) -> None:
    """Check policy access, failing closed for task-local policy errors."""
    allowed, reason = _evaluate_policy_access(function_name, function_args)
    if not allowed:
        raise ToolExecutionError(
            tool_name=function_name,
            message=reason or "Acesso negado pela política.",
        )


def _track_tool_feedback(function_name: str, function_args: dict) -> None:
    """Record tool execution in ToolVisualFeedback, silently ignoring failures."""
    try:
        from aura_cli.core.tools.tool_visual_feedback import (
            ToolExecution,
            ToolStatus,
            get_tool_feedback,
        )

        fb = get_tool_feedback()
        if not (fb._executions and fb._executions[-1].tool_name == function_name):
            e = ToolExecution(
                tool_name=function_name,
                category=fb.get_category(function_name),
                args=function_args,
            )
            e.status = ToolStatus.SUCCESS
            e.end_time = time.time()
            fb._executions.append(e)
    except Exception as error:
        logger.debug(f"ToolFeedback tracking ignorado: {error}")


def _raise_tool_exception(
    function_name: str, function_args: dict, e: Exception
) -> None:
    """Re-raise e as the appropriate typed ToolExecutionError."""
    if isinstance(e, (KeyError, TypeError, ValueError)):
        raise ToolExecutionError(
            tool_name=function_name,
            message=f"Invalid arguments or tool not found: {e}",
            original_error=e,
        ) from e
    if isinstance(e, (OSError, PermissionError)):
        if function_name in WRITE_TOOLS:
            raise FileOperationError(
                operation=function_name,
                file_path=function_args.get("file_path", "unknown"),
                message=str(e),
                original_error=e,
            ) from e
        raise ToolExecutionError(
            tool_name=function_name,
            message=f"Falha na operação de arquivo: {e}",
            original_error=e,
        ) from e
    logger.error(
        f"Erro inesperado ao executar ferramenta '{function_name}': {e}", exc_info=True
    )
    raise ToolExecutionError(
        tool_name=function_name, message=f"Erro inesperado: {e}", original_error=e
    ) from e


def _run_tool_with_interceptors(
    function_name: str,
    function_args: dict,
    available_tools: dict,
    registry: Any,
    loading: Any,
    suppress_tool_loading: bool,
    ui: Optional[UIManager] = None,
    capability_audit: CapabilityAuditSink | None = None,
) -> Any:
    """Run tool with interceptor hooks and investigator UI. Returns result."""
    _ti = _get_tool_interceptor()
    if _ti is not None:
        try:
            _ti.intercept_before(function_name, function_args)
        except Exception as _ie:
            logger.debug(f"ToolInterceptor before ignorado: {_ie}")

    _commit_policy_access(function_name, function_args, ui, capability_audit)
    result = _call_tool(function_name, function_args, available_tools, registry)
    _track_tool_feedback(function_name, function_args)

    if _ti is not None:
        try:
            _ti.intercept_after(function_name, function_args, result)
        except Exception as _ie:
            logger.debug(f"ToolInterceptor after ignorado: {_ie}")

    if function_name in ("investigate_codebase", "investigate_codebase_deep"):
        try:
            from rich.console import Console as _C

            from aura_cli.cli.ui.components.investigator_file_progress import (
                AuraInvestigatorFileProgress,
            )
            from aura_cli.cli.ui.components.investigator_step import (
                AuraInvestigatorStep,
            )

            _c = _C()
            _c.print(
                AuraInvestigatorFileProgress().render("Analisando arquivos...", 100, 0)
            )
            _c.print(
                AuraInvestigatorStep().render(
                    "Investigação", "running", function_args.get("path", ".")
                )
            )
        except Exception as e:
            logger.debug(f"Investigator UI render falhou: {e}")

    if not suppress_tool_loading and loading:
        loading.update(LoadingState.FINALIZING, "Processando resultado...")

    return result


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
    """Execute tool and return result and execution time.

    When suppress_tool_loading is True, no spinner is shown for this tool
    (e.g. when already inside a parent "Generating response..." status).
    """
    registry = get_service_registry() if get_service_registry is not None else None

    if function_name not in available_tools and not (
        registry and registry.get_tool(function_name) is not None
    ):
        raise KeyError(
            f"Ferramenta '{function_name}' não encontrada em AVAILABLE_TOOLS"
        )

    hook_manager = get_hook_manager() if get_hook_manager is not None else None
    request = ToolExecutionRequest(function_name, function_args, tool_call_id)
    if turn_execution is not None:
        turn_execution.plan_operation(tool_call_id, function_name, function_args)

    async def before(req: ToolExecutionRequest) -> None:
        if turn_execution is not None:
            turn_execution.start_operation(req.call_id)
        await _run_hooks(
            hook_manager,
            HookEvent.PRE_TOOL,
            {
                "function_name": req.name,
                "function_args": dict(req.arguments),
                "tool_call_id": req.call_id,
            },
            "BEFORE_TOOL_CALL",
        )

    def guard(req: ToolExecutionRequest) -> GuardDecision:
        blocked = _check_execution_guards(
            req.name,
            dict(req.arguments),
            console,
            ui,
            capability_audit=capability_audit,
        )
        return GuardDecision(blocked is None, blocked[0] if blocked else "")

    async def execute(req: ToolExecutionRequest) -> Tuple[Any, float]:
        return await _execute_with_loading_and_heal(
            req.name,
            dict(req.arguments),
            available_tools,
            registry,
            console,
            ui,
            suppress_tool_loading,
            capability_audit=capability_audit,
        )

    async def after(req: ToolExecutionRequest, outcome: Any) -> None:
        await _run_hooks(
            hook_manager,
            HookEvent.POST_TOOL,
            {
                "function_name": req.name,
                "function_args": dict(req.arguments),
                "tool_call_id": req.call_id,
                "result": str(outcome.result)[:1000],
                "execution_time": outcome.elapsed,
            },
            "AFTER_TOOL_CALL",
        )

    try:
        outcome = await ToolExecutionPipeline(
            before=before,
            guard=guard,
            execute=execute,
            after=after,
        ).run(request)
    except BaseException as error:
        if turn_execution is not None:
            turn_execution.fail_operation(tool_call_id, error)
        raise
    if turn_execution is not None:
        turn_execution.finish_operation(
            tool_call_id,
            outcome.result,
            outcome.elapsed,
            blocked=outcome.blocked,
            evidence_update=_collect_postconditions(
                function_name, function_args, outcome
            ),
        )
    if outcome.blocked:
        return outcome.result, outcome.elapsed

    result, execution_time = outcome.result, outcome.elapsed

    _emit_tool_result(
        function_name,
        function_args,
        tool_call_id,
        result,
        execution_time,
        conversation_history,
        stats,
        ui,
        console,
    )
    return result, execution_time


def _collect_postconditions(
    function_name: str, function_args: dict[str, Any], outcome: Any
) -> dict[str, str]:
    """Collect concrete postconditions at the infrastructure boundary."""
    command = str(function_args.get("command", ""))
    is_commit = function_name in {"git_commit", "git_commit_smart"} or (
        function_name == "run_shell_command" and command.startswith("git commit")
    )
    if outcome.blocked or not is_commit:
        return {}
    from aura_cli.application.workspace.path_policy import resolve_workspace_path
    from aura_cli.core.tools.file_system import get_allowed_base_dir

    base_dir = get_allowed_base_dir()
    raw_root = function_args.get("repo_path") or function_args.get("path")
    try:
        root = resolve_workspace_path(
            str(raw_root) if raw_root else str(base_dir),
            base_dir,
        )
    except ValueError as error:
        logger.warning("Postconditions de Git bloqueadas por boundary: %s", error)
        return {}
    if root.is_file():
        root = root.parent

    def git(*args: str) -> str:
        result = subprocess.run(
            ["git", "-C", str(root), *args],
            capture_output=True,
            text=True,
            check=False,
            timeout=5,
        )
        return result.stdout.strip() if result.returncode == 0 else ""

    repository = git("rev-parse", "--show-toplevel")
    branch = git("branch", "--show-current")
    commit = git("rev-parse", "HEAD")
    if not repository or not branch or not commit:
        return {}
    return {"repository": repository, "branch": branch, "commit": commit}


def _check_execution_guards(
    function_name: str,
    function_args: dict,
    console: Any,
    ui: Any,
    *,
    capability_audit: CapabilityAuditSink | None = None,
) -> Optional[Tuple[str, float]]:
    """Run audit and one broker-backed capability guard before execution."""
    if not _run_ops_audit(function_name, function_args, console):
        return f"Operação '{function_name}' bloqueada pela auditoria de segurança.", 0.0

    access_allowed, access_reason = _evaluate_policy_access(
        function_name, function_args
    )
    if not access_allowed:
        policy = get_execution_policy()
        decision = decide_tool_capability(
            None,
            policy=policy,
            adapter_available=_intervention_adapter is not None,
            access_allowed=False,
            access_reason=access_reason,
        )
        _reject_capability(
            ui,
            function_name,
            decision,
            policy,
            capability_audit=capability_audit,
        )
        raise ToolExecutionError(
            tool_name=function_name,
            message=f"Execução de {function_name} bloqueada: {decision.reason}",
        )

    if function_name not in WRITE_TOOLS and not _check_tool_requires_confirmation(
        function_name,
        function_args,
        console,
        ui,
        access_allowed=access_allowed,
        access_reason=access_reason,
        capability_audit=capability_audit,
    ):
        return f"Execução de {function_name} cancelada pelo usuário", 0.0
    return None


async def _execute_with_loading_and_heal(
    function_name: str,
    function_args: dict,
    available_tools: dict,
    registry: Any,
    console: Any,
    ui: Any,
    suppress_tool_loading: bool,
    capability_audit: CapabilityAuditSink | None = None,
) -> Tuple[Any, float]:
    """Handle diff confirmation, tool execution, and auto-healing."""
    if DIFF_CONFIRMATION_ENABLED and function_name in WRITE_TOOLS:
        _try_auto_checkpoint(function_name, function_args)
        should_execute, _ = await _show_diff_confirmation(
            function_name, function_args, ui, console
        )
        if not should_execute:
            ui.display_warning("Alteração rejeitada pelo usuário.")
            return "Alteração em arquivo rejeitada pelo usuário", 0.0

    start_time = time.time()
    result: Optional[str] = None
    loading = None

    try:
        if not suppress_tool_loading:
            loading = show_tool_loading(console, function_name, function_args)
            loading.update(LoadingState.EXECUTING, "Executando...")
        result = _run_tool_with_interceptors(
            function_name,
            function_args,
            available_tools,
            registry,
            loading,
            suppress_tool_loading,
            ui,
            capability_audit,
        )
    except KeyboardInterrupt:
        if loading:
            loading.complete("Cancelado")
        raise
    except Exception as e:
        if loading:
            loading.error(str(e))
        _raise_tool_exception(function_name, function_args, e)

    execution_time = time.time() - start_time
    if loading:
        loading.complete(f"{function_name} executed in {execution_time:.2f}s")

    # Auto-healing: syntax validation for Python file writes
    if (
        function_name in ("write_file", "edit_file")
        and isinstance(result, str)
        and "success" in result.lower()
    ):
        path = function_args.get("path") or function_args.get("file_path", "")
        if path.endswith(".py"):
            try:
                with open(path, encoding="utf-8") as _f:
                    result = append_python_syntax_diagnostic(result, path, _f.read())
            except OSError as error:
                logger.debug(f"Validação pós-escrita ignorada para {path}: {error}")

    return result, execution_time


def _emit_tool_result(
    function_name: str,
    function_args: dict,
    tool_call_id: str,
    result: Any,
    execution_time: float,
    conversation_history: List[Dict],
    stats: Any,
    ui: UIManager,
    console: Console,
) -> None:
    """Render to UI, append to history, update stats."""
    tool_result_renderable = ToolResult().render(
        tool_name=function_name,
        result=str(result),
        execution_time=execution_time,
        status="done",
        args=function_args,
        show_args=False,
        console_width=console.width,
    )
    if get_active_workspace() is None:
        ui.print()
        ui.print(tool_result_renderable)
        ui.print()

    tool_content = _format_tool_result_for_model(result, function_name)
    _append_tool_interaction_to_history(
        conversation_history, function_name, function_args, tool_call_id, tool_content
    )

    stats.increment_tool_calls(function_name)
    if function_name == "read_file":
        stats._files_read_list.append(function_args.get("path", ""))
