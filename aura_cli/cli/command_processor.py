"""Slash command processor and router for Aura CLI.

This module processes, validates, and executes all slash commands (commands
starting with "/") available in Aura CLI. It is invoked by command_router.route_command
for any input that starts with "/". Some commands (/tui, /interface, /auto-run,
/exit) are handled earlier in app_loop; their branches here act as fallback.
Directs commands to handlers in the `commands` package (basic, agents, config,
context, management, project).
"""

from pathlib import Path
import queue
import threading
from typing import TYPE_CHECKING, Any, Optional, Tuple

if TYPE_CHECKING:
    from rich.console import Console


from aura_cli.application.presentation_routing import open_settings_for_ui
from aura_cli.cli.commands.agents import (
    handle_agi,
    handle_ops,
    handle_tool_details,
    handle_tools,
)
from aura_cli.cli.commands.arena import handle_arena
from aura_cli.cli.commands.basic import (
    handle_clear,
    handle_dashboard,
    handle_help,
    handle_history,
    handle_welcome,
)
from aura_cli.cli.commands.config import handle_dev, handle_extensions, handle_model
from aura_cli.cli.commands.context import (
    handle_checkpoint,
    handle_constitution,
    handle_memory,
    handle_tangent,
)
from aura_cli.cli.commands.cost import handle_cost
from aura_cli.cli.commands.management import (
    handle_cache,
    handle_resume,
    handle_session,
    handle_workflow,
)
from aura_cli.cli.commands.mcp import handle_mcp
from aura_cli.cli.commands.project import handle_init, handle_notebook, handle_todo
from aura_cli.cli.commands.skill import handle_skill
from aura_cli.cli.key_manager import show_settings_menu, show_theme_menu
from aura_cli.cli.ui.constants import UIIcons, UIStyles
from aura_cli.core.logger import get_logger
from aura_cli.core.stats import StatsTracker

logger = get_logger(__name__)


def _handle_tools_cmd(args: str) -> None:
    """Handle /tools command with optional audit sub-command."""
    if args.strip() == "audit":
        try:
            from rich.console import Console as _C

            from aura_cli.core.tools.tool_visual_feedback import (
                generate_tool_audit_report,
            )

            _C().print(generate_tool_audit_report())
        except Exception as _e:
            from rich.console import Console as _C

            _C().print(f"[red]Error generating audit report: {_e}[/red]")
    else:
        handle_tools()


def _handle_session_cmd(
    args: str, app_loop: Any, agi_thread: Any, ops_thread: Any, final_model: str
) -> tuple:
    """Route /session command with app_loop context for save/load integration."""
    msg = handle_session(args, app_loop=app_loop)
    return True, msg, agi_thread, ops_thread, final_model


def _handle_tangent_cmd(
    args: str, app_loop: Any, agi_thread: Any, ops_thread: Any, final_model: str
) -> tuple:
    """Route /tangent command through the TangentManager stored in app_loop."""
    if not app_loop:
        return (
            True,
            "Erro: AppLoop não disponível para tangent.",
            agi_thread,
            ops_thread,
            final_model,
        )
    updated_msgs, msg = handle_tangent(
        args, app_loop.conversation_history, app_loop.tangent_manager
    )
    app_loop.conversation_history = updated_msgs
    return True, msg, agi_thread, ops_thread, final_model


def _handle_checkpoint_cmd(
    args: str, app_loop: Any, agi_thread: Any, ops_thread: Any, final_model: str
) -> tuple:
    if not app_loop:
        return (
            True,
            "Erro: AppLoop não disponível para checkpoint.",
            agi_thread,
            ops_thread,
            final_model,
        )
    _success, state, msg = handle_checkpoint(
        args, app_loop.checkpoint_manager, {"messages": app_loop.conversation_history}
    )
    if state and state.get("messages"):
        app_loop.conversation_history = state["messages"]
    return True, msg, agi_thread, ops_thread, final_model


def process_slash_command(
    command: str,
    agi_thread: Optional[threading.Thread],
    ops_thread: Optional[threading.Thread],
    final_model: str,
    stats: StatsTracker,
    ui: Any,
    console: "Console",
    project_root: Optional[Path] = None,
    app_loop: Optional[Any] = None,
    status_queue: Optional[queue.Queue] = None,
) -> Tuple[
    bool,
    Optional[str],
    Optional[threading.Thread],
    Optional[threading.Thread],
    Optional[str],
]:
    """Process slash commands and return whether to continue loop.

    Routes slash commands to appropriate handlers in the commands package.
    """
    parts = command.strip().split()
    if not parts:
        return True, None, agi_thread, ops_thread, final_model

    cmd = parts[0].lower()
    args = " ".join(parts[1:])
    _ok = (True, None, agi_thread, ops_thread, final_model)

    result = _dispatch_slash_cmd(
        cmd,
        args,
        _ok,
        agi_thread,
        ops_thread,
        final_model,
        ui,
        app_loop,
        project_root,
        status_queue,
    )
    if result is not None:
        return result

    return (
        True,
        f"[{UIStyles.WARNING}]{UIIcons.WARNING} Comando desconhecido: {cmd}. Digite /help para ver os comandos disponíveis.[/{UIStyles.WARNING}]",
        agi_thread,
        ops_thread,
        final_model,
    )


def _dispatch_slash_cmd(
    cmd: str,
    args: str,
    _ok: tuple,
    agi_thread: Any,
    ops_thread: Any,
    final_model: str,
    ui: Any,
    app_loop: Any,
    project_root: Optional[Path],
    status_queue: Any,
) -> Optional[tuple]:
    """Dispatch a parsed slash command. Returns the 5-tuple result or None if unknown."""
    # Simple no-arg commands — call handler() and return _ok
    _SIMPLE: dict = {
        "/help": handle_help,
        "/clear": handle_clear,
        "/welcome": handle_welcome,
        "/history": handle_history,
        "/theme": show_theme_menu,
        "/extensions": handle_extensions,
        "/todo": handle_todo,
        "/init": handle_init,
        "/notebook": handle_notebook,
        "/tools": handle_tools,
    }
    if cmd in _SIMPLE and not args:
        _SIMPLE[cmd]()
        return _ok

    if cmd == "/settings" and not args:
        if not open_settings_for_ui(ui):
            show_settings_menu()
        return _ok

    # Commands that call handler(args) and return _ok
    _ARGS_OK: dict = {
        "/dashboard": handle_dashboard,
        "/tool": handle_tool_details,
        "/memory": handle_memory,
        "/constitution": handle_constitution,
    }
    if cmd in _ARGS_OK:
        _ARGS_OK[cmd](args)
        return _ok

    # Commands that return (True, handler(args), ...)
    _ARGS_MSG: dict = {
        "/workflow": handle_workflow,
        "/cache": handle_cache,
    }
    if cmd in _ARGS_MSG:
        return True, _ARGS_MSG[cmd](args), agi_thread, ops_thread, final_model

    return _dispatch_stateful_cmd(
        cmd,
        args,
        _ok,
        agi_thread,
        ops_thread,
        final_model,
        app_loop,
        project_root,
        status_queue,
    )


def _dispatch_stateful_cmd(
    cmd: str,
    args: str,
    _ok: tuple,
    agi_thread: Any,
    ops_thread: Any,
    final_model: str,
    app_loop: Any,
    project_root: Optional[Path],
    status_queue: Any,
) -> Optional[tuple]:
    """Dispatch commands that need stateful context (threads, model, app_loop)."""
    if cmd == "/session":
        return _handle_session_cmd(args, app_loop, agi_thread, ops_thread, final_model)

    if cmd == "/resume":
        return (
            True,
            handle_resume(args, app_loop=app_loop),
            agi_thread,
            ops_thread,
            final_model,
        )

    if cmd == "/keyboard":
        from aura_cli.cli.ui.key_bindings import show_keyboard_help

        show_keyboard_help()
        return _ok

    if cmd in ("/exit", "/quit"):
        return False, "Sessão encerrada.", agi_thread, ops_thread, final_model

    if cmd in ("/tui", "/interface"):
        return True, "Abrindo interface Nebula...", agi_thread, ops_thread, final_model

    if cmd == "/agi":
        full_cmd = cmd + (" " + args if args else "")
        return handle_agi(
            full_cmd,
            agi_thread,
            ops_thread,
            final_model,
            project_root or Path.cwd(),
            status_queue,
        )

    if cmd == "/ops":
        full_cmd = cmd + (" " + args if args else "")
        return handle_ops(
            full_cmd,
            agi_thread,
            ops_thread,
            final_model,
            project_root or Path.cwd(),
            status_queue,
        )

    if cmd == "/tools":
        _handle_tools_cmd(args)
        return _ok

    if cmd == "/cost":
        handle_cost(args)
        return _ok

    feature_result = _dispatch_feature_cmd(
        cmd, args, app_loop, agi_thread, ops_thread, final_model
    )
    if feature_result is not None:
        return feature_result

    if cmd == "/tangent":
        return _handle_tangent_cmd(args, app_loop, agi_thread, ops_thread, final_model)

    if cmd == "/checkpoint":
        return _handle_checkpoint_cmd(
            args, app_loop, agi_thread, ops_thread, final_model
        )

    return None


def _dispatch_feature_cmd(
    cmd: str,
    args: str,
    app_loop: Any,
    agi_thread: Any,
    ops_thread: Any,
    final_model: str,
) -> Optional[tuple]:
    if cmd == "/arena":
        return True, handle_arena(args, app_loop), agi_thread, ops_thread, final_model

    if cmd == "/skill":
        return True, handle_skill(args, app_loop), agi_thread, ops_thread, final_model

    if cmd == "/mcp":
        return True, handle_mcp(args, app_loop), agi_thread, ops_thread, final_model

    if cmd == "/model":
        new_model = handle_model(args or final_model)
        msg = f"Modelo: {new_model}" if new_model != final_model else None
        return True, msg, agi_thread, ops_thread, new_model

    if cmd == "/dev":
        return True, handle_dev(args), agi_thread, ops_thread, final_model

    return None
