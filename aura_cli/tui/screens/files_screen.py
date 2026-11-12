"""Files Screen — external file manager launcher."""

from __future__ import annotations

from typing import ClassVar

from textual import on
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Center, Middle

from aura_cli.tui.shell.base_tool_screen import (
    BaseToolScreen,
    pop_screen_and_restore_focus,
)
from aura_cli.tui.tools import get_tool_availability
from aura_cli.tui.widgets.layout.external_tool_launcher import ExternalToolLauncher


class FilesScreen(BaseToolScreen):
    """Launcher for optional Files manager."""

    SCREEN_TITLE = "File Manager"
    SCREEN_SUBTITLE = "System file explorer"

    BINDINGS: ClassVar[list] = [
        *BaseToolScreen.BINDINGS,
        Binding("enter", "launch", "Open files"),
    ]

    def compose_tool_body(self) -> ComposeResult:
        availability = get_tool_availability()
        with Center(), Middle():
            yield ExternalToolLauncher(
                available=availability.files,
                description_lines=[
                    "File manager for the terminal.",
                    "Baseado no TUIFIManager.",
                ],
                features=[
                    "File navigation with icons",
                    "Git repository recognition",
                    "Copy, move and delete operations",
                    "Suporte a teclado e mouse",
                ],
                install_command="pip install TUIFIManager",
                launch_button_label="Open files",
                id="files_launcher",
            )

    def action_launch(self) -> None:
        if get_tool_availability().files:
            pop_screen_and_restore_focus(self.app)
            self.app.action_launch_files()  # type: ignore[attr-defined]  # Textual App subclass action

    @on(ExternalToolLauncher.LaunchRequested)
    def _on_launch(self, _event: ExternalToolLauncher.LaunchRequested) -> None:
        self.action_launch()
