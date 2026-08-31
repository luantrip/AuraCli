"""
Shared Status Bar Components.

Provides consistent status bars across all Aura CLI tools.
"""

from __future__ import annotations

import contextlib
from dataclasses import dataclass
from typing import List, Optional

from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Static


@dataclass
class StatusItem:
    """A single item in a status bar."""

    key: str
    value: str
    icon: str = ""
    style: str = ""

    def render(self) -> str:
        """Render the status item."""
        icon_part = f"{self.icon} " if self.icon else ""
        return f"{icon_part}{self.value}"


class StatusBar(Widget):
    """
    Flexible status bar with multiple items.

    Example:
        ```python
        status = StatusBar(items=[
            StatusItem("file", "main.py", icon="◇"),
            StatusItem("line", "Line 42, Col 10", icon="📍"),
            StatusItem("encoding", "UTF-8"),
        ])
        ```
    """

    def __init__(
        self,
        items: Optional[List[StatusItem]] = None,
        left_items: Optional[List[StatusItem]] = None,
        right_items: Optional[List[StatusItem]] = None,
        **kwargs,
    ):
        """Initialize the instance."""
        super().__init__(**kwargs)
        self._left_items = left_items or items or []
        self._right_items = right_items or []

    def compose(self) -> ComposeResult:
        """Compose the widget layout."""
        with Horizontal():
            # Left items
            for item in self._left_items:
                yield Static(
                    item.render(),
                    classes=f"status-item status-item-left {item.style}",
                    id=f"status-{item.key}",
                )

            # Spacer
            yield Static("", classes="status-spacer")

            # Right items
            for item in self._right_items:
                yield Static(
                    item.render(),
                    classes=f"status-item status-item-right {item.style}",
                    id=f"status-{item.key}",
                )

    def update_item(self, key: str, value: str, icon: Optional[str] = None) -> None:
        """Update a status item by key."""
        try:
            widget = self.query_one(f"#status-{key}", Static)
            icon_part = f"{icon} " if icon else ""
            widget.update(f"{icon_part}{value}")
        except Exception as error:
            self.log.debug("Status item %s is not mounted yet: %s", key, error)

    def set_items(
        self,
        left_items: Optional[List[StatusItem]] = None,
        right_items: Optional[List[StatusItem]] = None,
    ) -> None:
        """Replace all items and refresh."""
        if left_items is not None:
            self._left_items = left_items
        if right_items is not None:
            self._right_items = right_items
        self.refresh()


class MiniStatusBar(Widget):
    """
    Compact single-line status bar.

    Example:
        ```python
        status = MiniStatusBar()
        status.update("Processing file 1 of 10...")
        ```
    """

    text: reactive[str] = reactive("")
    icon: reactive[str] = reactive("")
    extra: reactive[str] = reactive("")

    def compose(self) -> ComposeResult:
        """Compose the widget layout."""
        with Horizontal():
            yield Static("", classes="mini-status-icon", id="icon")
            yield Static("", classes="mini-status-text", id="text")
            yield Static("", classes="mini-status-extra", id="extra")

    def watch_text(self, value: str) -> None:
        """React to text changes."""
        with contextlib.suppress(Exception):
            self.query_one("#text", Static).update(value)

    def watch_icon(self, value: str) -> None:
        """React to icon changes."""
        with contextlib.suppress(Exception):
            self.query_one("#icon", Static).update(f"{value} " if value else "")

    def watch_extra(self, value: str) -> None:
        """React to extra changes."""
        with contextlib.suppress(Exception):
            self.query_one("#extra", Static).update(value)

    def update(
        self,
        text: Optional[str] = None,
        icon: Optional[str] = None,
        extra: Optional[str] = None,
    ) -> None:
        """Update status bar content."""
        if text is not None:
            self.text = text
        if icon is not None:
            self.icon = icon
        if extra is not None:
            self.extra = extra
