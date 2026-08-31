"""Command routing module for Aura CLI.

This module analyzes user input and determines which system or handler
should process it. It acts as the first logic layer after receiving a
command, deciding if the input is an internal command (slash command),
a shell command to execute directly, or a query for a language model.
"""

from pathlib import Path
import threading
from typing import Any, Optional, Tuple

from rich.console import Console

from aura_cli.cli.command_processor import process_slash_command
from aura_cli.cli.ui.constants import UIIcons, UIStyles
from aura_cli.core.stats import StatsTracker
from aura_cli.core.tools.shell import (
    execute_shell_command,
    extract_shell_command,
    shell_execution_status,
    should_execute_directly,
)


def route_command(
    command: str,
    agi_thread: Optional[threading.Thread],
    ops_thread: Optional[threading.Thread],
    current_model: str,
    stats: StatsTracker,
    ui: Any,
    console: Console,
    project_root: Optional[Path] = None,
    app_loop: Optional[Any] = None,
) -> Tuple[
    bool,
    Optional[str],
    Optional[threading.Thread],
    Optional[threading.Thread],
    Optional[str],
]:
    """Process and route a user command to the appropriate handler.

    Routes to slash-command processor (prefix '/'), shell executor
    (direct shell command) or LLM query handler (default).

    Args:
        command: User input string.
        agi_thread: Running AgiWorker thread, if any.
        ops_thread: Running OpsWorker thread, if any.
        current_model: Active LLM model name.
        stats: Statistics tracker.
        ui: UIManager instance.
        console: Rich Console.
        project_root: Project root path.
        app_loop: AppLoop instance (for conversation history access).
    Returns:
        Tuple (should_continue, result_type, new_agi_thread, new_ops_thread, new_model).
    """
    if command.startswith("/"):
        result = process_slash_command(
            command,
            agi_thread,
            ops_thread,
            current_model,
            stats,
            ui,
            console,
            project_root=project_root,
            app_loop=app_loop,
            status_queue=ui.status_queue if ui else None,
        )

        if len(result) == 5:
            should_continue, message, new_agi, new_ops, new_model = result
        else:
            should_continue, message, new_agi, new_ops = result
            new_model = None

        if message:
            if any(
                keyword in message
                for keyword in [
                    "Aura Dev:",
                    "/dev",
                    "/auto",
                    "Tema:",
                    "Modelo:",
                    "Aura AGI:",
                    "Aura Ops:",
                    "já está ativa",
                    "não disponível",
                    "não encontrada",
                    "invalid",
                    "desconhecido",
                ]
            ):
                stats.set_notification(message, duration_seconds=3.0)
            else:
                if ui and hasattr(ui, "print"):
                    ui.print(message)
                else:
                    console.print(message)

        if not should_continue:
            return False, None, None, None, None

        return True, message, new_agi, new_ops, new_model

    if should_execute_directly(command):
        shell_enabled, shell_reason = shell_execution_status()
        if not shell_enabled:
            return (
                True,
                f"[{UIStyles.WARNING}]{UIIcons.WARNING} {shell_reason}[/{UIStyles.WARNING}]",
                agi_thread,
                ops_thread,
                current_model,
            )

        shell_cmd = extract_shell_command(command)
        success, output = execute_shell_command(shell_cmd)
        if output == "__CLEAR_SCREEN__":
            console.clear()
            return True, None, agi_thread, ops_thread, current_model

        ui.display_shell_output(shell_cmd, success, output)
        return True, None, agi_thread, ops_thread, current_model

    return True, "llm_query", agi_thread, ops_thread, current_model
