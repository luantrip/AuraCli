"""Shown when the Chawan monitor backend is not available."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Container, Vertical
from textual.widgets import Static


class MonitorUnavailablePanel(Container):
    """Instructions when monitor dependencies are missing."""

    def compose(self) -> ComposeResult:
        with Container(id="monitor-unavailable-state", classes="unavailable-message"):
            with Vertical(classes="unavailable-content"):
                yield Static("Monitor indisponível", classes="unavailable-title")
                yield Static(
                    "Esta instalação não encontrou a dependência necessária.",
                    classes="unavailable-text",
                )
                yield Static("Dependência: Chawan (cha)", classes="unavailable-label")
                yield Static(
                    "cd tools_tui/monitor && make", classes="unavailable-command"
                )
                yield Static(
                    "Ou instale o binário pelo gerenciador de pacotes do sistema.",
                    classes="unavailable-text",
                )
                yield Static("Pressione Esc para voltar.", classes="unavailable-hint")
