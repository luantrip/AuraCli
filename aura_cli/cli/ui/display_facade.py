"""Display facade — single channel for all user-facing status messages.

Routes display_error/success/warning/info() to UIManager when registered,
or falls back to Console + UIStyles. Use get_console() instead of creating
Console() in individual modules. register_ui() / unregister_ui() manage
the UIManager lifecycle. Accessibility is opt-in and never starts an external reader.
"""

import os
from typing import Optional

from rich.console import Console

from aura_cli.cli.ui.constants import UIIcons, UIStyles

_console: Optional[Console] = None
_current_ui: Optional[object] = None


def _get_console() -> Console:
    """Return the shared Rich console instance (internal use)."""
    global _console
    if _console is None:
        _console = Console()
    return _console


def get_console() -> Console:
    """Return the shared Rich console instance.

    Preferred over creating a new Console() in each module.
    When UIManager is registered via register_ui(), prefer using
    display_error/success/warning/info instead for consistent routing.

    Returns:
        Shared Console instance managed by display_facade.
    """
    return _get_console()


def register_ui(ui: object) -> None:
    """Register UIManager so display_* delegate to it when available."""
    global _current_ui
    _current_ui = ui


def unregister_ui() -> None:
    """Unregister UIManager (e.g. on app exit)."""
    global _current_ui
    _current_ui = None


def _is_accessible_mode() -> bool:
    """True if accessibility mode is enabled (env or config)."""
    if os.environ.get("AURA_ACCESSIBLE", "").strip().lower() in ("1", "true", "yes"):
        return True
    try:
        from aura_cli.core.config import get_config_manager

        config = get_config_manager()
        if bool(config.get("accessibility_mode", False)):
            return True
        accessibility = config.get("accessibility", {})
        return bool(
            isinstance(accessibility, dict) and accessibility.get("enabled", False)
        )
    except Exception:
        return False


def _icon(icon: str) -> str:
    """Return icon with optional accessible text."""
    return UIIcons.with_alt(icon, include_alt=_is_accessible_mode())


def _display_styled(message: str, *, method: str, icon: str, style: str) -> None:
    """Shared implementation for all display_* functions."""
    if _current_ui is not None and hasattr(_current_ui, method):
        getattr(_current_ui, method)(message)
        return
    c = _get_console()
    # The facade lacks sufficient context to decide vertical rhythm.
    # Separators belong to the VisualEmitter/surface that composes the turn.
    c.print(f"[{style}]{_icon(icon)} {message}[/{style}]")


def display_error(message: str) -> None:
    """Display error message. Use instead of console.print with ERROR style."""
    _display_styled(
        message,
        method="display_error",
        icon=UIIcons.ERROR,
        style=UIStyles.ERROR,
    )


def display_success(message: str) -> None:
    """Display success message."""
    _display_styled(
        message,
        method="display_success",
        icon=UIIcons.SUCCESS,
        style=UIStyles.SUCCESS,
    )


def display_warning(message: str) -> None:
    """Display warning message."""
    _display_styled(
        message,
        method="display_warning",
        icon=UIIcons.WARNING,
        style=UIStyles.WARNING,
    )


def display_info(message: str) -> None:
    """Display info message."""
    _display_styled(
        message,
        method="display_info",
        icon=UIIcons.INFO,
        style=UIStyles.INFO,
    )
