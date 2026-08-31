"""Bottom status bar for the monitor tool."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.reactive import reactive
from textual.widgets import Label, Static


class MonitorStatusBar(Static):
    """Bottom status bar with key hints."""

    message = reactive("")

    def compose(self) -> ComposeResult:
        with Horizontal():
            yield Label("│", classes="status-separator")
            yield Label("Esc", classes="status-key")
            yield Label(":back ", classes="status-action")
            yield Label("g", classes="status-key")
            yield Label(":goto ", classes="status-action")
            yield Label("r", classes="status-key")
            yield Label(":reload ", classes="status-action")
            yield Label("/", classes="status-key")
            yield Label(":search", classes="status-action")

    def watch_message(self, message: str) -> None:
        self.update(f" {message} ")
