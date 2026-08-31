"""Browser tab bar for the monitor tool."""

from __future__ import annotations

from typing import List

from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.message import Message
from textual.widgets import Button

from aura_cli.application.presentation.monitor import build_tab_views
from aura_cli.tui.tools.monitor.browser import BrowserTab


class TabBar(Horizontal):
    """Tab bar for managing multiple tabs."""

    class TabSelected(Message):
        """Emitted when a tab is clicked."""

        def __init__(self, index: int):
            super().__init__()
            self.index = index

    class NewTabRequested(Message):
        """Emitted when the user requests a new tab."""

    class TabClosed(Message):
        """Emitted when a tab close button is clicked."""

        def __init__(self, index: int):
            super().__init__()
            self.index = index

    def __init__(self, tabs: List[BrowserTab], active_index: int = 0, **kwargs):
        self._tabs = tabs
        self._active_index = active_index
        super().__init__(**kwargs)

    def compose(self) -> ComposeResult:
        for view in build_tab_views(self._tabs, self._active_index):
            btn = Button(
                view.label,
                id=f"tab_{view.index}",
                classes="active-tab" if view.active else "",
            )
            yield btn
        yield Button("+", id="new_tab", classes="new-tab-btn")

    def update_tabs(self, tabs: List[BrowserTab], active_index: int) -> None:
        self._tabs = tabs
        self._active_index = active_index
        self.refresh(recompose=True)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "new_tab":
            self.post_message(self.NewTabRequested())
        elif event.button.id and event.button.id.startswith("tab_"):
            index = int(event.button.id.split("_")[1])
            self.post_message(self.TabSelected(index))
