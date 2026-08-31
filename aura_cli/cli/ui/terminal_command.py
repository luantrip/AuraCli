"""Terminal command display component — security-aware rendering.

Renders shell commands with status indicators (running / completed /
failed / background), execution time, exit code and security warnings.
Commands are validated before display; dangerous operations trigger a
visible warning. display_run_terminal_command() is the canonical
high-level entry point.
"""

from typing import Optional

from rich.console import Console

from aura_cli.cli.ui.display_facade import get_console
from aura_cli.cli.ui.security import evaluate_command_security
from aura_cli.cli.ui.terminal_display import display_terminal_command


def display_run_terminal_command(
    command: str,
    output: Optional[str] = None,
    status: str = "completed",
    execution_time: Optional[float] = None,
    exit_code: Optional[int] = None,
    show_security_warning: bool = True,
    output_console: Optional[Console] = None,
) -> None:
    """
    Display terminal command with security validation and rich formatting.

    Validates command for security risks before display. If dangerous command
    detected and show_security_warning=True, displays visual warning. Then
    delegates to display_terminal_command() for actual rendering. Automatically
    adjusts status to "failed" if exit_code != 0.

    Args:
        command: Executed command string
        output: Command output (optional)
        status: Status (running, completed, failed, background)
        execution_time: Execution time in seconds (optional)
        exit_code: Exit code (optional, 0=success)
        show_security_warning: Whether to show security warnings (default: True)

    Example:
        >>> display_run_terminal_command("ls -la", output="total 48\\n...", status="completed", execution_time=0.05)
        >>> display_run_terminal_command("rm -rf /tmp/test", status="completed", show_security_warning=True)
    """
    target_console = output_console if output_console is not None else get_console()
    if show_security_warning:
        is_dangerous, warning = evaluate_command_security(
            command, console_width=target_console.width
        )
        if is_dangerous and warning:
            target_console.print(warning)

    if status == "completed" and exit_code is not None and exit_code != 0:
        status = "failed"

    display_terminal_command(
        command=command,
        output=output,
        status=status,
        execution_time=execution_time,
        exit_code=exit_code,
        output_console=target_console,
    )
