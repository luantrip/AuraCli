"""AuraPaint screen — native editor launcher."""

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


class PaintScreen(BaseToolScreen):
    """Entry screen for the AuraPaint editor bundled with AuraCli."""

    SCREEN_TITLE = "AuraPaint"
    SCREEN_SUBTITLE = "Editor nativo de arte ANSI para terminal"

    BINDINGS: ClassVar[list] = [
        *BaseToolScreen.BINDINGS,
        Binding("enter", "launch", "Abrir AuraPaint"),
    ]

    def compose_tool_body(self) -> ComposeResult:
        availability = get_tool_availability()
        with Center(), Middle():
            yield ExternalToolLauncher(
                available=availability.paint,
                description_lines=[
                    "Editor de arte ANSI integrado à AuraCli.",
                    "Mantém compatibilidade com formatos Textual Paint.",
                ],
                features=[
                    "Criação de arte ANSI",
                    "Ferramentas de desenho e preenchimento",
                    "Paleta de cores",
                    "Suporte a camadas",
                ],
                install_command=None,
                launch_button_label="Abrir AuraPaint",
                id="paint_launcher",
            )

    def action_launch(self) -> None:
        if get_tool_availability().paint:
            pop_screen_and_restore_focus(self.app)
            self.app.action_launch_paint()  # type: ignore[attr-defined]

    @on(ExternalToolLauncher.LaunchRequested)
    def _on_launch(self, _event: ExternalToolLauncher.LaunchRequested) -> None:
        self.action_launch()
