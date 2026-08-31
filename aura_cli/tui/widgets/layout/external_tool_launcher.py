"""Reusable launcher panel for auxiliary tools (AuraPaint, files, …)."""

from __future__ import annotations

from typing import List, Optional

from textual import on
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.message import Message
from textual.widgets import Button, Static


class ExternalToolLauncher(Vertical):
    """
    Status, feature list, install hint, and optional launch button.

    Parent screen should handle ``ExternalToolLauncher.LaunchRequested``.
    """

    class LaunchRequested(Message):
        """User pressed launch or equivalent."""

    def __init__(
        self,
        *,
        available: bool,
        description_lines: List[str],
        features: List[str],
        install_command: Optional[str] = None,
        launch_button_label: str = "Abrir",
        launch_button_id: str = "launch_btn",
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self._available = available
        self._description_lines = description_lines
        self._features = features
        self._install_command = install_command
        self._launch_label = launch_button_label
        self._launch_id = launch_button_id

    def compose(self) -> ComposeResult:
        status = "✓ Disponível" if self._available else "○ Indisponível"
        status_class = "status-available" if self._available else "status-unavailable"
        yield Static(f"Estado: {status}", classes=status_class)

        for line in self._description_lines:
            yield Static(line, classes="description-text")

        yield Static("Recursos:", classes="features-label")
        for feat in self._features:
            yield Static(f"  • {feat}", classes="description-text")

        if self._available:
            with Horizontal(classes="action-hint"):
                yield Static("Pressione ", classes="action-hint")
                yield Static("Enter", classes="action-key")
                yield Static(" ou clique no botão para abrir", classes="action-hint")
            yield Static("Pressione Esc para voltar", classes="description-text")
            yield Button(self._launch_label, id=self._launch_id, variant="primary")
        else:
            yield Static("Para instalar:", classes="install-hint")
            if self._install_command:
                yield Static(self._install_command, classes="install-command")
            yield Static("Pressione Esc para voltar", classes="description-text")

    @on(Button.Pressed)
    def _on_launch_btn(self, event: Button.Pressed) -> None:
        if event.button.id == self._launch_id and self._available:
            self.post_message(self.LaunchRequested())
