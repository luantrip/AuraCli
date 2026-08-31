"""Security warnings system for Aura CLI — protects against dangerous commands.

Detects destructive commands (rm -rf, format, dd, shutdown, sudo rm, etc.),
generates Rich visual warnings and enforces explicit confirmation.
is_dangerous_command() and create_security_warning() are the main entry points.
"""

from typing import Optional, Tuple

import rich
from rich.panel import Panel
from rich.text import Text

from aura_cli.cli.ui.constants import UIIcons, UIStyles
from aura_cli.cli.ui.layout_contract import layout_for_width

DANGEROUS_COMMANDS = [
    "rm -rf",
    "rm -r",
    "rm -f",
    "del /f /s",
    "format",
    "mkfs",
    "dd if=",
    "chmod 777",
    "chmod 000",
    "sudo rm",
    "sudo del",
    "sudo format",
    "> /dev/sd",
    "shutdown",
    "reboot",
    "halt",
    "poweroff",
    "init 0",
    "init 6",
]

ALLOWED_COMMANDS = [
    "ls",
    "pwd",
    "cd",
    "cat",
    "echo",
    "grep",
    "find",
    "which",
    "where",
    "type",
    "help",
    "man",
    "info",
]


def is_dangerous_command(command: str) -> bool:
    """
    Check if command is potentially dangerous or destructive.

    Analyzes command against list of known dangerous commands and
    regex patterns to detect destructive operations. Commands in
    ALLOWED_COMMANDS list are considered safe automatically.

    Args:
        command: Command to check (full string)

    Returns:
        True if command is dangerous, False if safe

    Example:
        >>> is_dangerous_command("rm -rf /")
        True
        >>> is_dangerous_command("ls -la")
        False
    """
    command_lower = command.lower().strip()

    for allowed in ALLOWED_COMMANDS:
        if command_lower.startswith(allowed + " ") or command_lower == allowed:
            return False

    for dangerous in DANGEROUS_COMMANDS:
        if dangerous.lower() in command_lower:
            return True

    import re

    dangerous_patterns = [
        r"rm\s+.*-.*[rf]",  # rm with flags -r or -f
        r"del\s+.*\/[fs]",  # del with flags /f or /s (Windows)
        r"format\s+",
        r"mkfs\s+",  # filesystem creation
        r"dd\s+if=",  # dd with input file
        r"chmod\s+[0-7]{3}",  # chmod with numeric permissions
        r"sudo\s+(rm|del|format|mkfs)",  # sudo with dangerous commands
    ]

    return any(re.search(pattern, command_lower) for pattern in dangerous_patterns)


def create_security_warning(command: str, console_width: int = 80) -> Panel:
    """
    Create formatted security warning Panel profissional com visual rico.

    Generates visual warning Panel with warning icon, command highlighted
    and explanatory message. Uses Rich Panel for professional display.

    Args:
        command: Command that triggered warning

    Returns:
        Rich Panel with formatted warning

    Example:
        >>> warning = create_security_warning("rm -rf /")
        >>> console.print(warning)
    """
    from rich.panel import Panel

    warning_text = Text()
    warning_text.append(f"{UIIcons.WARNING} ", style=UIStyles.ERROR + " bold")
    warning_text.append(
        "Comando potencialmente perigoso detectado!\n\n", style=UIStyles.ERROR + " bold"
    )
    warning_text.append("Comando: ", style=UIStyles.LABEL)
    warning_text.append(f"{command}\n\n", style=UIStyles.WARNING + " bold")
    warning_text.append(
        f"{UIIcons.WARNING} Este comando pode causar:\n", style=UIStyles.WARNING
    )
    warning_text.append("  • Perda permanente de dados\n", style=UIStyles.MUTED)
    warning_text.append(
        "  • Alterações irreversíveis no sistema\n", style=UIStyles.MUTED
    )
    warning_text.append("  • Danos a arquivos e diretórios\n\n", style=UIStyles.MUTED)
    warning_text.append(
        "Confirmação explícita necessária!", style=UIStyles.ERROR + " bold"
    )

    return Panel(
        warning_text,
        title=f"[{UIStyles.ERROR}]{UIIcons.WARNING} Aviso de segurança[/{UIStyles.ERROR}]",
        border_style=UIStyles.BORDER_ERROR,
        padding=layout_for_width(console_width).focus_padding,
        box=rich.box.DOUBLE,
    )


def evaluate_command_security(
    command: str, console_width: int = 80
) -> Tuple[bool, Optional[Panel]]:
    """
    Evaluate command security and return warning if needed.

    Convenient wrapper combining is_dangerous_command() and
    create_security_warning(). Returns tuple with danger flag
    and formatted warning message (or None if safe).

    Args:
        command: Command to evaluate

    Returns:
        Tuple (is_dangerous: bool, warning_message: Optional[str])

    Example:
        >>> is_dangerous, warning = evaluate_command_security("rm -rf /")
        >>> if is_dangerous:
        ...     console.print(warning)
    """
    if is_dangerous_command(command):
        warning = create_security_warning(command, console_width=console_width)
        return True, warning
    return False, None
