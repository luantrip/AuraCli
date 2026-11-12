"""Aura CLI main entry point and orchestration.
Main CLI application definition using Typer.
"""

import json
from pathlib import Path
import time
from typing import Annotated, Any, Dict, List, Optional
import warnings as _warnings

from rich.console import Console
import typer

from aura_cli.cli.first_run import is_first_run, run_setup_wizard
from aura_cli.cli.helpers import (
    build_runtime_system_note,
    display_aura_splash_screen,
    initialize_conversation_history,
    show_onboarding_hint_if_first_run,
)
from aura_cli.cli.key_manager import check_api_keys, show_settings_menu
from aura_cli.cli.runtime import EmbeddingServerLifecycle, RuntimeServices
from aura_cli.cli.ui.components.input.shell_box import register_shell_presenter
from aura_cli.cli.ui.constants import UIIcons, UIStyles
from aura_cli.cli.ui.display_facade import (
    display_error,
    display_warning,
    get_console,
)
from aura_cli.cli.ui.manager import UIManager
from aura_cli.cli.utils import set_environment_for_litellm
from aura_cli.cli.utils.worker_readiness import WorkerReadinessError
from aura_cli.core.config import get_config_manager
from aura_cli.core.events.event_bus import get_event_bus
from aura_cli.core.llm.model_utils import (
    format_model_display_name,
    resolve_model_option,
)
from aura_cli.core.logger import get_logger
from aura_cli.core.stats import get_stats

register_shell_presenter()

# Keep this name patchable for callers and tests while deferring the LLM stack.
AppLoop = None


def get_tools_dict() -> Dict[str, Any]:
    """Load the heavy tool catalog only for commands that execute tools."""
    from aura_cli.core.service_registry import get_tools_dict as load_tools

    return load_tools()


def _get_app_loop_class():
    """Load the interactive runtime only when a chat session actually starts."""
    global AppLoop
    if AppLoop is None:
        from aura_cli.cli.app_loop import AppLoop as app_loop_class

        AppLoop = app_loop_class
    return AppLoop


_warnings.filterwarnings("ignore", category=FutureWarning, module="transformers")
_embedding_server = EmbeddingServerLifecycle()
logger = get_logger(__name__)

__version__ = "0.1.0"


_WORKER_EXIT_CODES = {
    "completed": 0,
    "error": 1,
    "failed": 1,
    "cancelled": 6,
    "timeout": 5,
    "blocked": 4,
}
_WORKER_ERROR_EXIT_CODES = {
    "configuration": 3,
    "missing_credential": 3,
    "model": 2,
    "provider": 2,
    "workspace": 2,
    "dependency": 7,
    "blocked": 4,
    "worker_wait_timeout": 5,
    "cancelled": 6,
}


def _worker_exit_code(result: Dict[str, Any]) -> int:
    """Map a worker result envelope to the CLI process exit code."""
    status = str(result.get("status", "error")).lower()
    if status == "error":
        return _WORKER_ERROR_EXIT_CODES.get(
            str(result.get("error_code", "")), _WORKER_EXIT_CODES["error"]
        )
    return _WORKER_EXIT_CODES.get(status, _WORKER_EXIT_CODES["error"])


def _handle_worker_readiness_error(
    error: WorkerReadinessError,
    output: str,
    console: Console,
) -> None:
    """Render a side-effect-free readiness failure and terminate deterministically."""
    result = error.report.to_dict()
    _format_output(result, output, console)
    raise typer.Exit(_worker_exit_code(result))


def _wait_for_worker_terminal(worker: Any, timeout: float) -> Dict[str, Any]:
    """Wait for the explicit terminal result while supporting legacy workers."""
    wait_terminal = getattr(type(worker), "wait_terminal", None)
    if callable(wait_terminal):
        return worker.wait_terminal(timeout=timeout)
    return worker.get_result(timeout=timeout)


def _cancel_worker(worker: Any, reason: str) -> None:
    """Request cooperative cancellation while tolerating legacy worker APIs."""
    cancel = getattr(worker, "cancel", None)
    if not callable(cancel):
        return
    try:
        cancel(reason=reason)
    except TypeError:
        cancel()


def _wait_for_worker_with_deadline(
    worker: Any,
    worker_thread: Any,
    timeout: float,
    *,
    cancel_grace: float = 2.0,
) -> Dict[str, Any]:
    """Wait for a worker without allowing a live thread to cause an infinite join.

    The configured timeout is the observation deadline. Once it expires, a
    cooperative cancellation request is sent and a short bounded grace period
    is allowed for cleanup. A non-responsive daemon thread is never joined
    indefinitely; the caller receives an explicit timeout envelope.
    """
    deadline = time.monotonic() + max(float(timeout), 0.0)
    if worker_thread is not None:
        while worker_thread.is_alive():
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                break
            worker_thread.join(timeout=min(0.5, remaining))

    if worker_thread is not None and worker_thread.is_alive():
        _cancel_worker(worker, f"timeout after {max(float(timeout), 0.0):.1f}s")
        worker_thread.join(timeout=max(float(cancel_grace), 0.0))
        if not worker_thread.is_alive():
            try:
                terminal = _wait_for_worker_terminal(worker, timeout=0.0)
            except Exception:
                terminal = None
            if isinstance(terminal, dict) and terminal.get("status") in {
                "timeout",
                "cancelled",
                "canceled",
                "error",
            }:
                return terminal
        return {
            "status": "timeout",
            "task_id": getattr(worker, "task_id", None),
            "error_code": "worker_wait_timeout",
            "message": "The operation exceeded the timeout and received a cancellation request.",
            "worker_still_running": bool(worker_thread.is_alive()),
        }

    remaining = max(0.0, deadline - time.monotonic())
    result = _wait_for_worker_terminal(worker, timeout=remaining)
    if not isinstance(result, dict):
        return {
            "status": "error",
            "error_code": "worker_invalid_result",
            "message": "The worker returned an invalid result.",
        }
    return result


def _version_callback(value: bool) -> None:
    """Show version and exit."""
    if value:
        console = get_console()
        console.print(f"[bold cyan]Aura CLI[/] version [bold green]{__version__}[/]")
        raise typer.Exit()


app = typer.Typer(
    pretty_exceptions_show_locals=False,
    pretty_exceptions_enable=False,
    help=f"[{UIStyles.TITLE}]Aura CLI - Your AI Code Assistant[/]",
    add_completion=False,
    no_args_is_help=False,
)


@app.callback(invoke_without_command=True)
def _main_callback(
    ctx: typer.Context,
    version: Annotated[
        bool,
        typer.Option(
            "--version",
            "-v",
            help="Display version and exit.",
            callback=_version_callback,
            is_eager=True,
        ),
    ] = False,
    mcp: bool = typer.Option(False, "--mcp", help="Inicia a Aura como servidor MCP."),
    mcp_transport: str = typer.Option(
        "stdio", "--mcp-transport", help="Transporte MCP: stdio ou http."
    ),
    mcp_port: int = typer.Option(
        8765, "--mcp-port", help="Porta HTTP do servidor MCP."
    ),
    allow_writes: bool = typer.Option(
        False, "--allow-writes", help="Permite tools mutantes via MCP."
    ),
    resume: Optional[str] = typer.Option(
        None,
        "--resume",
        help="Resumes an Aura session or imports an external session from a file.",
    ),
) -> None:
    """Aura CLI — AI code assistant entry point."""
    if ctx.invoked_subcommand is not None:
        return
    if mcp is True:
        from aura_cli.cli.commands.mcp import create_mcp_server

        server = create_mcp_server(allow_writes=allow_writes)
        if mcp_transport == "http":
            server.serve_http(port=mcp_port)
        else:
            server.serve_stdio()
        return
    try:
        start_interactive_session(resume_reference=resume)
    finally:
        _embedding_server.stop()


@app.command()
def chat(
    message: Annotated[
        Optional[List[str]], typer.Argument(help="Inicia um chat direto com a Aura.")
    ] = None,
    model: Annotated[
        Optional[str],
        typer.Option(
            "--model",
            "-m",
            help="ID ou alias do modelo (auto, gemini, openai, claude; ex.: gemini-2.5-flash).",
        ),
    ] = None,
) -> None:
    """
    Inicia um chat direto com a Aura. Se nenhuma mensagem for fornecida,
    inicia o modo interativo.
    """
    if message:
        project_root = Path.cwd()
        runtime_services = RuntimeServices.initialize(project_root)
        event_bus = get_event_bus()
        console = get_console()
        ui = UIManager(
            stats=get_stats(), status_queue=event_bus.get_queue(), console=console
        )
        conversation_history = initialize_conversation_history()
        conversation_history.append(build_runtime_system_note())
        app_loop = _get_app_loop_class()(
            ui=ui,
            stats=get_stats(),
            console=console,
            conversation_history=conversation_history,
            context_manager=runtime_services.workspace.context,
            available_tools=get_tools_dict(),
            initial_model=resolve_model_option(model),
            project_root=project_root,
            runtime_services=runtime_services,
        )
        try:
            app_loop.process_command_single_shot(" ".join(message))
        finally:
            app_loop.shutdown()
    else:
        start_interactive_session()


def _should_emit_progress(output: Optional[str], quiet: bool) -> bool:
    """Return whether human-readable progress may share the output stream."""
    return not quiet and (output or "text").lower() not in {"json", "yaml"}


def _format_output(
    data: Dict[str, Any], format_type: str, console: Optional[Console] = None
) -> None:
    """
    Format and output data in the specified format (json, yaml, or default).

    Args:
        data: Dictionary to format
        format_type: Output format ("json", "yaml", or default)
        console: Optional Rich console for default formatting
    """
    normalized_format = (format_type or "text").lower()
    if normalized_format == "json":
        print(json.dumps(data, indent=2, ensure_ascii=False))
    elif normalized_format == "yaml":
        try:
            import yaml

            print(yaml.dump(data, default_flow_style=False, allow_unicode=True))
        except ImportError:
            print(json.dumps(data, indent=2, ensure_ascii=False))
    else:
        if console and isinstance(data, dict):
            if data.get("status") == "completed":
                console.print(
                    f"[{UIStyles.SUCCESS}]{UIIcons.SUCCESS} Task completed![/{UIStyles.SUCCESS}]"
                )
                if data.get("context_summary"):
                    console.print(
                        f"[{UIStyles.MUTED}]{UIIcons.INFO} Contexto: {data['context_summary']}[/{UIStyles.MUTED}]"
                    )
            elif data.get("status") == "error":
                console.print(
                    f"[{UIStyles.ERROR}]{UIIcons.ERROR} Erro: {data.get('error', 'Unknown error')}[/{UIStyles.ERROR}]"
                )
            else:
                console.print(
                    f"[{UIStyles.WARNING}]{UIIcons.INFO} Status: {data.get('status', 'unknown')}[/{UIStyles.WARNING}]"
                )


@app.command()
def agi(
    project_root: Annotated[
        Optional[Path],
        typer.Option(
            "--project-root",
            "-p",
            help="Specifies the project root directory. Default: current directory.",
        ),
    ] = None,
    task: Annotated[
        Optional[List[str]],
        typer.Argument(help="Description of the task to be executed by the AGI Agent."),
    ] = None,
    model: Annotated[
        Optional[str],
        typer.Option(
            "--model",
            "-m",
            help="ID ou alias do modelo (auto, gemini, openai, claude; ex.: gemini-2.5-flash).",
        ),
    ] = None,
    output: Optional[str] = typer.Option(
        "text",
        "--output",
        "-o",
        help="Output format: 'text' (default), 'json', 'yaml'.",
    ),
    quiet: bool = typer.Option(
        False,
        "--quiet",
        "-q",
        help="Suppress detailed output, showing only the final result.",
    ),
) -> None:
    """Launch the AGI agent for complex multi-step tasks."""

    get_config_manager()
    console = get_console()

    if project_root is None:
        project_root = Path.cwd()

    if task:
        stats = get_stats()
        stats.set_model(resolve_model_option(model))
        ui = UIManager(stats=stats)

        from aura_cli.cli.helpers import get_api_keys_dict
        from aura_cli.cli.utils.worker_factory import create_agi_worker_thread

        api_keys = get_api_keys_dict()
        task_str = " ".join(task)
        model_str = resolve_model_option(model)

        try:
            worker, worker_thread = create_agi_worker_thread(
                objective=task_str,
                model=model_str,
                api_keys=api_keys,
                headless=True,
                project_root=project_root,
            )
        except WorkerReadinessError as readiness_error:
            _handle_worker_readiness_error(readiness_error, output or "text", console)

        try:
            if _should_emit_progress(output, quiet):
                ui.display_info("Running AGI task…")
            if worker_thread and worker_thread.is_alive():
                worker_thread.join(timeout=300.0)
            result = _wait_for_worker_terminal(worker, timeout=30.0)
            _format_output(result, output, console)  # type: ignore[arg-type]  # Dict[str,Any] → OutputData
            exit_code = _worker_exit_code(result)
            if exit_code:
                raise typer.Exit(exit_code)
        except typer.Exit:
            raise
        except Exception as e:
            logger.error(f"Error in headless execution: {e}", exc_info=True)
            error_result = {"status": "error", "error": str(e)}
            _format_output(error_result, output, console)  # type: ignore[arg-type]  # Dict[str,Any] → OutputData
            raise typer.Exit(1) from None
    else:
        start_interactive_session()


@app.command()
def settings() -> None:
    """Display the settings menu for API keys and models."""
    show_settings_menu()


def _check_port_in_use(port: int) -> bool:
    """Compatibility adapter for embedding-server port checks."""
    return _embedding_server.port_in_use(port)


def _wait_for_embedding_server(port: int, timeout: float = 45.0) -> None:
    """Wait for embedding server to become ready (runs in background thread)."""
    if not _embedding_server.wait_until_ready(port, timeout):
        logger.debug("Embedding server did not become ready within timeout.")


def _start_embedding_server(port: int) -> Any:
    """Start embedding server subprocess. Returns process or None on failure."""
    try:
        return _embedding_server.start(port)
    except Exception as e:
        logger.warning(
            f"Failed to start embeddings server: {e}. Semantic search may not work."
        )
        return None


def _init_embedding_server() -> None:
    """Initialize embedding server if not already running."""
    from aura_cli.core.embeddings import EMBEDDING_SERVER_PORT

    _start_embedding_server(EMBEDDING_SERVER_PORT)


from aura_cli.core.embeddings.client import (
    configure_embedding_server_starter,
)

configure_embedding_server_starter(_init_embedding_server)

from aura_cli.cli.ui.forget_prompt import select_messages_to_forget
from aura_cli.core.tangent.manager import configure_forget_selector

configure_forget_selector(select_messages_to_forget)


def start_interactive_session(resume_reference: Optional[str] = None) -> None:
    """Initialize and run interactive Aura CLI session."""
    import threading

    current_thread = threading.current_thread()
    is_main = (
        current_thread is threading.main_thread() or current_thread.name == "MainThread"
    )
    if not is_main:
        logger.warning(
            f"start_interactive_session called from non-main thread: {current_thread.name}"
        )

    ui = UIManager(stats=get_stats())

    # Embedding server is now lazy-started (only when first needed by SkillRetriever)
    # _init_embedding_server() — removed from eager startup for faster launch

    # One onboarding entry point. The wizard runs on a first launch AND whenever no
    # API key exists (skipped/incomplete setup), so there is no second, different
    # "settings" screen standing in for it.
    _ran_wizard: bool = False
    if is_first_run() or not check_api_keys():
        _ran_wizard = True
        run_setup_wizard(key_required=not check_api_keys())

    if not check_api_keys():
        ui.display_error(
            "No API key configured. Run `aura` to redo setup "
            "or `aura settings` to configure manually."
        )
        raise typer.Exit()

    set_environment_for_litellm()
    try:
        from aura_cli.cli.ui.constants import _clear_theme_cache
        from aura_cli.cli.ui.theme_manager import get_theme_manager
        from aura_cli.core.config import get_config_manager

        config = get_config_manager()
        theme_name = config.get("theme_name")
        if theme_name:
            theme_manager = get_theme_manager()
            theme_manager.load_theme(theme_name)
        _clear_theme_cache()
        UIStyles._ensure_initialized()
    except Exception as e:
        logger.debug(f"Error initializing theme: {e}")
    project_root = Path.cwd()

    get_event_bus()  # initialize event bus
    logger.debug("CoreEventBus initialized in main thread")

    _init_core_services(
        project_root, resume_reference=resume_reference, wizard_ran=_ran_wizard
    )

    get_config_manager()  # ensure config is loaded


def _resolve_initial_model(configured_model: Optional[str]) -> str:
    """Resolve the model shown at startup.

    Respects an explicit user choice; otherwise picks a provider-aware default
    whose provider actually has a configured key (instead of blindly using
    DEFAULT_MODEL, which may point to an unconfigured provider).
    """
    if configured_model:
        return resolve_model_option(configured_model)
    from aura_cli.cli.helpers import get_api_keys_dict
    from aura_cli.core.llm.model_utils import resolve_default_model

    return resolve_default_model(get_api_keys_dict())


def _maybe_show_onboarding_hint(*, ui: Any, wizard_ran: bool) -> None:
    """Show the one-time hint unless the wizard already provided all context.

    P2-6: the setup wizard displays a 'Setup complete!' panel on success; a
    second 'how to start' banner in the same session is redundant noise.
    """
    if not wizard_ran:
        show_onboarding_hint_if_first_run(ui=ui)


def _init_core_services(
    project_root: Path,
    *,
    resume_reference: Optional[str] = None,
    wizard_ran: bool = False,
) -> None:
    """Initialize all core services at startup."""
    runtime_services = RuntimeServices.initialize(project_root)
    logger.debug("Critical runtime services initialized in main thread")

    try:
        from aura_cli.core.agents import ensure_adk_initialized, is_adk_bridge_enabled

        if not is_adk_bridge_enabled():
            logger.info("ADK bridge disabled by AURA_USE_ADK_BRIDGE")
        elif ensure_adk_initialized():
            logger.info("✅ ADK agents initialized and registered successfully")
            from aura_cli.adk.registry import registered_adk_agents

            logger.debug(f"Registered ADK agents: {registered_adk_agents()}")
        else:
            logger.warning("▲  ADK initialization failed - native agents active")
    except (ImportError, AttributeError) as e:
        logger.warning(f"Could not initialise ADK: {e}")
    except Exception as e:
        logger.warning(f"Unexpected error initialising ADK: {e}", exc_info=True)

    try:
        from aura_cli.core.nim_integrity import (
            check_nim_integrity,
            log_integrity_summary,
        )

        log_integrity_summary(check_nim_integrity(verbose=False))
    except Exception as _nim_err:
        logger.debug(f"Nim integrity check skipped: {_nim_err}")

    try:
        from aura_cli.application.observability import get_telemetry_coordinator

        telemetry = get_telemetry_coordinator()
        telemetry.set_stats_tracker(get_stats())
        telemetry.enable_sync()
        logger.debug("TelemetryCoordinator activated")
    except Exception as _mb_err:
        logger.debug(f"MetricsBridge skipped: {_mb_err}")


    configured_model = get_config_manager().get("default_model")
    initial_model = _resolve_initial_model(configured_model)
    stats = get_stats()
    stats.set_model(initial_model)
    console = get_console()
    ui = UIManager(
        stats=stats, status_queue=get_event_bus().get_queue(), console=console
    )

    display_aura_splash_screen(ui=ui)
    model_short = format_model_display_name(initial_model)
    ui.display_info(f"{UIIcons.AURA} Aura iniciada com {model_short}")
    _maybe_show_onboarding_hint(ui=ui, wizard_ran=wizard_ran)

    conversation_history = initialize_conversation_history()
    conversation_history.append(build_runtime_system_note())
    app_loop = _get_app_loop_class()(
        ui=ui,
        stats=stats,
        console=console,
        conversation_history=conversation_history,
        context_manager=runtime_services.workspace.context,
        available_tools=get_tools_dict(),
        initial_model=initial_model,
        project_root=runtime_services.project_root,
        runtime_services=runtime_services,
    )
    if resume_reference:
        from aura_cli.application.sessions import (
            LoadSessionStatus,
            load_session_into_workspace,
        )
        from aura_cli.core.sessions.session_manager import get_session_manager

        manager = get_session_manager(project_root)
        try:
            external_source = _external_resume_source(resume_reference)
        except ValueError as exc:
            raise typer.BadParameter(str(exc), param_hint="--resume") from exc
        if external_source:
            from aura_cli.core.sessions.external_import import (
                ExternalSessionImportError,
                import_external_session,
                preview_external_session,
            )

            try:
                preview = preview_external_session(
                    external_source,
                    workspace_root=project_root,
                    active_model=app_loop.final_model,
                )
                if preview.requires_confirmation:
                    reasons = "; ".join(preview.divergence_reasons)
                    if not typer.confirm(
                        f"The external session diverges ({reasons}). Import as history?",
                        default=False,
                    ):
                        raise typer.Abort()
                imported = import_external_session(manager, external_source)
            except ExternalSessionImportError as exc:
                raise typer.BadParameter(str(exc), param_hint="--resume") from exc
            outcome = load_session_into_workspace(
                manager, reference=imported.id, workspace=app_loop
            )
            ui.display_info(
                f"External session imported: {imported.name} "
                f"({outcome.message_count} messages; read-only history)"
            )
        else:
            outcome = load_session_into_workspace(
                manager,
                reference=resume_reference,
                workspace=app_loop,
            )
        if outcome.status is LoadSessionStatus.AMBIGUOUS:
            matches = ", ".join(
                f"{session.name} ({session.id})" for session in outcome.matches
            )
            raise typer.BadParameter(
                f"Ambiguous reference; choose a session: {matches}",
                param_hint="--resume",
            )
        if outcome.status is LoadSessionStatus.NOT_FOUND:
            raise typer.BadParameter(
                f"Session not found: {resume_reference}",
                param_hint="--resume",
            )
        ui.display_info(
            f"Session resumed: {outcome.session.name if outcome.session else resume_reference} "
            f"({outcome.message_count} mensagens)"
        )
    app_loop.run()


def _external_resume_source(reference: str) -> str | None:
    """Return a filesystem source for an external resume reference.

    Namespaced references keep the future provider discovery contract explicit:
    ``file:``, ``grok:``, ``codex:``, ``claude:`` and ``opencode:`` currently
    accept a direct file/directory path after the namespace.
    """
    prefixes = ("file:", "grok:", "codex:", "claude:", "opencode:")
    if reference.startswith(prefixes):
        source = reference.split(":", 1)[1]
        provider = reference.split(":", 1)[0].casefold()
        if provider in {"grok", "codex"} and not Path(source).expanduser().exists():
            from aura_cli.core.sessions.external_discovery import (
                resolve_external_reference,
            )

            resolved = resolve_external_reference(reference)
            return str(resolved) if resolved else source
        return source if source else None
    candidate = Path(reference).expanduser()
    return str(candidate) if candidate.exists() else None


@app.command()
def ops(
    task: Annotated[
        List[str],
        typer.Argument(help="Description of the operation task to be performed."),
    ],
    mode: Annotated[
        str,
        typer.Option(
            "--mode",
            "-m",
            help="Operation mode: 'general', 'git', 'docker'.",
        ),
    ] = "general",
    model: Annotated[
        Optional[str],
        typer.Option(
            "--model",
            help="LLM model to use.",
        ),
    ] = None,
    output: Optional[str] = typer.Option(
        "text",
        "--output",
        "-o",
        help="Output format: 'text' (default), 'json'.",
    ),
    timeout: float = typer.Option(
        300.0,
        "--timeout",
        help="Total observation timeout for the operation, in seconds.",
        min=0.1,
    ),
    quiet: bool = typer.Option(
        False,
        "--quiet",
        "-q",
        help="Suppress detailed output.",
    ),
) -> None:
    """Execute autonomous DevOps tasks (git, docker, system)."""
    get_config_manager()
    console = get_console()
    Path.cwd()

    if task:
        stats = get_stats()
        stats.set_model(resolve_model_option(model))
        ui = UIManager(stats=stats)

        from aura_cli.cli.helpers import get_api_keys_dict
        from aura_cli.cli.utils.worker_factory import create_ops_worker_thread

        api_keys = get_api_keys_dict()
        task_str = " ".join(task)
        model_str = resolve_model_option(model)

        try:
            worker, worker_thread = create_ops_worker_thread(
                task=task_str,
                model=model_str,
                api_keys=api_keys,
                mode=mode,
                headless=True,
            )
        except WorkerReadinessError as readiness_error:
            _handle_worker_readiness_error(readiness_error, output or "text", console)

        try:
            if not quiet:
                ui.display_info(f"Running operation ({mode})...")
            result = _wait_for_worker_with_deadline(
                worker,
                worker_thread,
                timeout,
            )
            _format_output(result, output, console)  # type: ignore[arg-type]  # Dict[str,Any] → OutputData
            exit_code = _worker_exit_code(result)
            if exit_code:
                raise typer.Exit(exit_code)

        except KeyboardInterrupt:
            _cancel_worker(worker, "cancelled by user")
            display_warning("Operation cancelled by user.")
            raise typer.Exit(6) from None
        except typer.Exit:
            raise
        except Exception as e:
            logger.error(f"Ops execution error: {e}", exc_info=True)
            display_error(str(e))
            raise typer.Exit(1) from e
    else:
        display_error("Please provide a task description.")


if __name__ == "__main__":
    app()
