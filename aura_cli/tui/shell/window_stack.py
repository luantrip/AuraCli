"""Two-layer window model: Textual screens vs in-widget overlay dialogs."""

from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING, Any, Callable, Optional

if TYPE_CHECKING:
    from textual.app import App

    from aura_cli.tui.widgets.dialogs.base_dialog import BaseDialog, DialogProvider


class OverlayKind(str, Enum):
    """Where a UI surface is mounted."""

    SCREEN = "screen"  # ``app.push_screen`` — blocks app, ESC dismisses screen
    OVERLAY = "overlay"  # ``DialogProvider`` — widget mounted on app root


class WindowStack:
    """
    Facade for opening/closing TUI surfaces.

    - **Screens** (modals): settings, constitution, paint, file manager
    - **Overlays** (widgets): confirm/input via ``DialogProvider`` on the same screen
    """

    def __init__(self, app: App, dialog_provider: Optional[DialogProvider] = None):
        self._app = app
        self._dialogs = dialog_provider

    def push_screen(
        self, screen: Any, callback: Optional[Callable[..., Any]] = None
    ) -> None:
        if callback is not None:
            self._app.push_screen(screen, callback)
        else:
            self._app.push_screen(screen)

    def show_overlay(self, dialog: BaseDialog) -> None:
        if self._dialogs is None:
            raise RuntimeError("DialogProvider not attached to this app")
        self._dialogs.show(dialog)

    def close_overlays(self) -> None:
        if self._dialogs:
            self._dialogs.close_all()

    @property
    def has_overlay(self) -> bool:
        return bool(self._dialogs and self._dialogs.has_dialog)
