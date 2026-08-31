"""Address bar with navigation controls for the monitor tool."""

from __future__ import annotations

import contextlib

from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.message import Message
from textual.reactive import reactive
from textual.widgets import Button, Input, Static


class AddressBar(Horizontal):
    """Address bar with navigation controls."""

    class UrlSubmitted(Message):
        def __init__(self, url: str):
            super().__init__()
            self.url = url

    class NavigationAction(Message):
        def __init__(self, action: str):
            super().__init__()
            self.action = action

    url = reactive("")
    can_back = reactive(False)
    can_forward = reactive(False)
    loading = reactive(False)

    def compose(self) -> ComposeResult:
        yield Button("◀", id="back", classes="nav-btn", disabled=not self.can_back)
        yield Button(
            "▶", id="forward", classes="nav-btn", disabled=not self.can_forward
        )
        yield Button("⟳", id="reload", classes="nav-btn")
        yield Button("⌂", id="home", classes="nav-btn")
        yield Input(
            placeholder="Enter URL or search...", id="url_input", classes="url-input"
        )
        yield Static("", id="status", classes="status")

    def on_mount(self) -> None:
        url_input = self.query_one("#url_input", Input)
        url_input.value = self.url

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.post_message(self.NavigationAction(event.button.id or ""))

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "url_input":
            self.post_message(self.UrlSubmitted(event.value))

    def watch_url(self, url: str) -> None:
        with contextlib.suppress(Exception):
            self.query_one("#url_input", Input).value = url

    def watch_loading(self, loading: bool) -> None:
        try:
            btn = self.query_one("#reload", Button)
            btn.label = "◌" if loading else "⟳"
        except Exception as error:
            self.log.debug("Monitor reload button is not mounted yet: %s", error)

    def set_status(self, status: str) -> None:
        with contextlib.suppress(Exception):
            self.query_one("#status", Static).update(status)
