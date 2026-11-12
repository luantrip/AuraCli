"""Agent command handlers for Aura CLI.

Handles commands:
- /agi: Start AGI agent
- /ops: Start Ops agent
- /tools: List available tools
- /tool: Show tool details
"""

import inspect
from pathlib import Path
import threading
from typing import Any, Optional, Tuple

from rich.columns import Columns
from rich.console import Group
from rich.panel import Panel
from rich.text import Text

from aura_cli.cli.helpers import (
    get_api_keys_dict,
    parse_agi_command,
    parse_agi_flags,
    parse_ops_command,
)
from aura_cli.cli.ops_tools_map import OPS_TOOLS
from aura_cli.cli.ui.constants import UIIcons, UIStyles
from aura_cli.cli.ui.display_facade import get_console
from aura_cli.cli.ui.formatters import format_agent_status
from aura_cli.cli.utils.worker_factory import (
    create_agi_worker_thread,
    create_ops_worker_thread,
)
from aura_cli.cli.utils.worker_readiness import WorkerReadinessError
from aura_cli.core.config import config_manager
from aura_cli.core.logger import get_logger
from aura_cli.core.service_registry import get_tools_dict

logger = get_logger(__name__)


def handle_agi(
    command: str,
    agi_thread: Optional[threading.Thread],
    ops_thread: Optional[threading.Thread],
    final_model: str,
    project_root: Path,
    status_queue: Any,
) -> Tuple[
    bool,
    Optional[str],
    Optional[threading.Thread],
    Optional[threading.Thread],
    Optional[str],
]:
    """Handle /agi command."""
    if agi_thread and agi_thread.is_alive():
        return (
            True,
            f"[{UIStyles.WARNING}]{UIIcons.WARNING} Aura AGI is already working. To start a new task, reinitialize the session.[/{UIStyles.WARNING}]",
            None,
            None,
            None,
        )

    objective = parse_agi_command(command)
    flags = parse_agi_flags(command)

    # Adversarial validation: opt-in via --validate flag or config

    enable_validation = flags.get("validate", False) or bool(
        config_manager.get("agi_adversarial_validation")
    )

    try:
        from aura_cli.adk.registry import ensure_adk_agents_registered

        ensure_adk_agents_registered()
    except (ImportError, AttributeError) as e:
        logger.debug(f"Could not pre-register ADK agents: {e}")
    except Exception as e:
        logger.warning(
            f"Unexpected error pre-registering ADK agents: {e}", exc_info=True
        )

    api_keys = get_api_keys_dict()

    try:
        _, new_agi_thread = create_agi_worker_thread(
            objective=objective or "",
            model=final_model,
            api_keys=api_keys,
            headless=False,
            project_root=project_root,
            enable_adversarial_validation=enable_validation,
        )
    except WorkerReadinessError as readiness_error:
        if status_queue:
            status_queue.put(
                {
                    "type": "status",
                    "status": "error",
                    "error_code": readiness_error.report.code,
                    "message": readiness_error.report.message,
                }
            )
        return (
            True,
            f"[{UIStyles.ERROR}]{UIIcons.ERROR} {readiness_error.report.message}[/{UIStyles.ERROR}]",
            None,
            None,
            final_model,
        )

    if status_queue:
        status_queue.put(
            {
                "type": "status",
                "status": "running",
                "message": "Aura AGI trabalhando...",
            }
        )
    return (
        True,
        format_agent_status("Aura AGI", "ativada em background..."),
        new_agi_thread,
        None,
        None,
    )


def handle_ops(
    command: str,
    agi_thread: Optional[threading.Thread],
    ops_thread: Optional[threading.Thread],
    final_model: str,
    project_root: Path,
    status_queue: Any,
) -> Tuple[
    bool,
    Optional[str],
    Optional[threading.Thread],
    Optional[threading.Thread],
    Optional[str],
]:
    """Handle /ops command."""
    if ops_thread and ops_thread.is_alive():
        return (
            True,
            f"[{UIStyles.WARNING}]{UIIcons.WARNING} Aura Ops is already working. To start a new task, reinitialize the session.[/{UIStyles.WARNING}]",
            None,
            None,
            None,
        )

    mode, task = parse_ops_command(command)

    api_keys = get_api_keys_dict()

    try:
        _, new_ops_thread = create_ops_worker_thread(
            task=task,
            model=final_model,
            api_keys=api_keys,
            mode=mode,
            headless=False,
            project_root=project_root,
        )
    except WorkerReadinessError as readiness_error:
        if status_queue:
            status_queue.put(
                {
                    "type": "status",
                    "status": "error",
                    "error_code": readiness_error.report.code,
                    "message": readiness_error.report.message,
                }
            )
        return (
            True,
            f"[{UIStyles.ERROR}]{UIIcons.ERROR} {readiness_error.report.message}[/{UIStyles.ERROR}]",
            None,
            None,
            final_model,
        )

    if status_queue:
        status_queue.put(
            {
                "type": "status",
                "status": "running",
                "message": f"Aura Ops ({mode}) trabalhando...",
            }
        )
    return (
        True,
        format_agent_status(f"Aura Ops ({mode})", "ativada em background..."),
        None,
        new_ops_thread,
        None,
    )


def handle_tools() -> None:
    """List all available tools in columns."""
    console = get_console()

    agi_tools_list = []
    tools_dict = get_tools_dict()
    for name in sorted(tools_dict.keys()):
        agi_tools_list.append(f"[cyan]{name}[/cyan]")

    ops_tools_list = []
    for name in sorted(OPS_TOOLS.keys()):
        ops_tools_list.append(f"[green]{name}[/green]")

    agi_header = Text(
        f"🛠️ AGI Tools · main catalog ({len(agi_tools_list)})",
        style=UIStyles.TITLE,
    )
    ops_header = Text(
        f"✦ Ops Tools · base operacional ({len(ops_tools_list)})",
        style=UIStyles.TITLE,
    )

    console.print()
    console.print(Group(agi_header, Columns(agi_tools_list, equal=True, expand=True)))
    console.print()
    console.print(Group(ops_header, Columns(ops_tools_list, equal=True, expand=True)))
    console.print(
        f"\n[{UIStyles.MUTED}]▪ Use [bold]/tool <name>[/bold] to see details of a specific tool.[/{UIStyles.MUTED}]"
    )
    console.print()


def handle_tool_details(tool_name: str) -> None:
    """Display details of specific tool."""
    console = get_console()
    tool_name = tool_name.strip()

    if not tool_name:
        console.print(f"[{UIStyles.ERROR}]Error: Tool name not provided.[/]")
        return

    tools_dict = get_tools_dict()
    tool_func = tools_dict.get(tool_name) or OPS_TOOLS.get(tool_name)

    if not tool_func:
        console.print(f"[{UIStyles.ERROR}]Tool '{tool_name}' not found.[/]")
        return

    sig = inspect.signature(tool_func)  # type: ignore[arg-type]  # Callable narrowing for inspect
    doc = inspect.getdoc(tool_func) or "No documentation."

    panel = Panel(
        f"[bold white]Signature:[/]\n[yellow]def {tool_name}{sig}[/]\n\n[bold white]Description:[/]\n{doc}",
        title=f"[{UIStyles.TITLE}]🛠️ {tool_name}[/]",
        border_style=UIStyles.BORDER_ACCENT,
    )
    console.print()
    console.print(panel)
    console.print()
