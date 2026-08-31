"""Centralized UI formatting utilities.

This module provides consistent formatting functions for UI components,
eliminating code duplication and ensuring visual consistency across
the Aura CLI interface.

Functions:
    format_status_message: Format status messages with icons
    format_error_message: Format error messages consistently
    format_success_message: Format success messages consistently
    format_info_message: Format info messages consistently
    format_warning_message: Format warning messages consistently
    format_file_operation: Format file operation messages
    format_model_name: Format model names for display
"""

from typing import Optional

from aura_cli.cli.ui.constants import UIIcons, UIStyles


def _safe_style(style: Optional[str], fallback: str = "white") -> str:
    """Ensure style is never None to prevent MarkupError.

    Args:
        style: Style value (can be None)
        fallback: Valor fallback se style for None

    Returns:
        Valid style (never None)
    """
    return style if style is not None else fallback


def format_status_message(
    message: str,
    icon: Optional[str] = None,
    style: Optional[str] = None,
) -> str:
    """Format a status message with optional icon and style.

    Args:
        message: Message text to format
        icon: Optional icon to prepend (defaults to BULLET)
        style: Optional style to apply (defaults to MUTED)

    Returns:
        Formatted message string with Rich markup
    """
    if icon is None:
        icon = UIIcons.BULLET
    if style is None:
        style = UIStyles.MUTED

    # Ensure style is never None to prevent MarkupError
    if style is None:
        style = "dim white"

    return f"[{style}]{icon} {message}[/{style}]"


def format_error_message(message: str, icon: Optional[str] = None) -> str:
    """Format an error message consistently.

    Args:
        message: Error message text
        icon: Optional icon (defaults to ERROR)

    Returns:
        Formatted error message with Rich markup
    """
    if icon is None:
        icon = UIIcons.ERROR

    style = UIStyles.ERROR or "red"  # Fallback se None
    return f"[{style}]{icon} {message}[/{style}]"


def format_success_message(message: str, icon: Optional[str] = None) -> str:
    """Format a success message consistently.

    Args:
        message: Success message text
        icon: Optional icon (defaults to SUCCESS)

    Returns:
        Formatted success message with Rich markup
    """
    if icon is None:
        icon = UIIcons.SUCCESS

    style = UIStyles.SUCCESS or "green"  # Fallback se None
    return f"[{style}]{icon} {message}[/{style}]"


def format_info_message(message: str, icon: Optional[str] = None) -> str:
    """Format an info message consistently.

    Args:
        message: Info message text
        icon: Optional icon (defaults to INFO)

    Returns:
        Formatted info message with Rich markup
    """
    if icon is None:
        icon = UIIcons.INFO

    style = UIStyles.INFO or "blue"  # Fallback se None
    return f"[{style}]{icon} {message}[/{style}]"


def format_warning_message(message: str, icon: Optional[str] = None) -> str:
    """Format a warning message consistently.

    Args:
        message: Warning message text
        icon: Optional icon (defaults to WARNING)

    Returns:
        Formatted warning message with Rich markup
    """
    if icon is None:
        icon = UIIcons.WARNING

    style = UIStyles.WARNING or "yellow"  # Fallback se None
    return f"[{style}]{icon} {message}[/{style}]"


def format_file_operation(
    operation: str,
    file_path: str,
    status: str = "completed",
) -> str:
    """Format a file operation message.

    Args:
        operation: Operation type (create, edit, read, delete)
        file_path: Path to the file
        status: Operation status (completed, failed, pending)

    Returns:
        Formatted file operation message
    """
    operation_icons = {
        "create": getattr(UIIcons, "FILE_CREATE", UIIcons.CREATE),
        "edit": getattr(UIIcons, "FILE_EDIT", UIIcons.EDIT),
        "read": getattr(UIIcons, "FILE_READ", UIIcons.FILE),
        "delete": getattr(UIIcons, "FILE_DELETE", UIIcons.DELETE),
    }

    status_styles = {
        "completed": UIStyles.SUCCESS,
        "failed": UIStyles.ERROR,
        "pending": UIStyles.WARNING,
    }

    icon = operation_icons.get(operation.lower(), UIIcons.BULLET)
    style = status_styles.get(status.lower(), UIStyles.MUTED)
    style = _safe_style(style, "dim white")

    return f"[{style}]{icon} {operation.capitalize()}: {file_path}[/{style}]"


def format_model_name(model: str) -> str:
    """Format a model name for display using centralized formatter.

    Args:
        model: Full model name (e.g., "gemini/gemini-2.5-flash")

    Returns:
        Formatted model name for display (e.g., "Gemini 2.5 Flash")
    """
    from aura_cli.core.llm.model_utils import format_model_display_name

    return format_model_display_name(model)


def format_agent_status(agent_type: str, status: str) -> str:
    """Format agent status message.

    Args:
        agent_type: Type of agent (AGI, Ops, etc.)
        status: Status message

    Returns:
        Formatted agent status message
    """
    agent_icons = {
        "agi": UIIcons.AGENT,
        "ops": UIIcons.OPS,
    }

    icon = agent_icons.get(agent_type.lower(), UIIcons.BULLET)
    style = _safe_style(UIStyles.PRIMARY, "cyan")

    return f"[{style}]{icon} {agent_type}: {status}[/{style}]"
