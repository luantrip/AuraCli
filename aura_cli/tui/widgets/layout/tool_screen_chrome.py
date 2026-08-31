"""Standard header block for tool launcher screens."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Container, VerticalGroup
from textual.widgets import Static


class ToolScreenChrome(Container):
    """Title + optional subtitle for auxiliary tool screens."""

    def __init__(
        self,
        title: str,
        subtitle: str = "",
        **kwargs,
    ) -> None:
        super().__init__(classes="header-container aura-tool-chrome", **kwargs)
        self._title = title
        self._subtitle = subtitle

    def compose(self) -> ComposeResult:
        with VerticalGroup():
            yield Static(self._title, classes="screen-header-text")
            if self._subtitle:
                yield Static(self._subtitle, classes="screen-subheader-text")
