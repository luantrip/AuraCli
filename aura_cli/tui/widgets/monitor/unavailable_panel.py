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
                yield Static("Monitor unavailable", classes="unavailable-title")
                yield Static(
                    "This installation could not find the required dependency.",
                    classes="unavailable-text",
                )
                yield Static("Dependency: Chawan (cha)", classes="unavailable-label")
                yield Static(
                    "cd tools_tui/monitor && make", classes="unavailable-command"
                )
                yield Static(
                    "Or install the binary via your system package manager.",
                    classes="unavailable-text",
                )
                yield Static("Press Esc to go back.", classes="unavailable-hint")
