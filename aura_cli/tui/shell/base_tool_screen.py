"""Base screen for auxiliary tool surfaces (paint launcher, files, tools menu)."""

from __future__ import annotations

from typing import Any, ClassVar

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container
from textual.screen import Screen

from aura_cli.tui.widgets.layout.tool_screen_chrome import ToolScreenChrome


def restore_composer_focus(app: Any) -> None:
    """Restore the main composer when the host application provides it."""
    restore_focus = getattr(app, "_restore_composer_focus", None)
    if not callable(restore_focus):
        return
    call_after_refresh = getattr(app, "call_after_refresh", None)
    if callable(call_after_refresh):
        call_after_refresh(restore_focus)
    else:
        restore_focus()


def pop_screen_and_restore_focus(app: Any) -> None:
    """Pop one screen and restore the main composer when supported."""
    app.pop_screen()
    restore_composer_focus(app)


class BaseToolScreen(Screen):
    """
      Tool screens use shared chrome (title/subtitle) and ``compose_tool_body()``.

    Escape pops the screen stack (back to main Aura TUI).
    """

    SCREEN_TITLE: ClassVar[str] = ""
    SCREEN_SUBTITLE: ClassVar[str] = ""
    CHROME_ID: ClassVar[str] = "tool_screen_chrome"

    BINDINGS: ClassVar[list] = [
        Binding("escape", "pop_screen", "Voltar", show=True),
    ]

    def compose(self) -> ComposeResult:
        with Container(classes="aura-tool-screen"):
            yield ToolScreenChrome(
                self.SCREEN_TITLE,
                self.SCREEN_SUBTITLE,
                id=self.CHROME_ID,
            )
            yield from self.compose_tool_body()

    def compose_tool_body(self) -> ComposeResult:
        """Override with tool-specific content."""
        yield Container()

    def action_pop_screen(self) -> None:
        """Return to the main TUI and restore composer focus when possible."""
        pop_screen_and_restore_focus(self.app)
