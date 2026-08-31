"""
Shared Navigation Components.

Provides breadcrumbs, tabs, and other navigation widgets.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, List, Optional

from textual import on
from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.message import Message
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Button, Static


@dataclass
class BreadcrumbItem:
    """A single item in a breadcrumb trail."""

    id: str
    label: str
    icon: str = ""
    data: Any = None


class Breadcrumb(Widget):
    """
    Breadcrumb navigation widget.

    Example:
        ```python
        breadcrumb = Breadcrumb(items=[
            BreadcrumbItem("home", "Home", icon="⌂"),
            BreadcrumbItem("folder", "Documents", icon="▷"),
            BreadcrumbItem("file", "report.txt", icon="◇"),
        ])
        ```
    """

    class ItemClicked(Message):
        """Message when breadcrumb item is clicked."""

        def __init__(self, item: BreadcrumbItem) -> None:
            """Initialize the widget."""
            super().__init__()
            self.item = item

    def __init__(
        self,
        items: Optional[List[BreadcrumbItem]] = None,
        separator: str = " › ",
        **kwargs,
    ):
        """Initialize the instance."""
        super().__init__(**kwargs)
        self._items = items or []
        self._separator = separator

    def compose(self) -> ComposeResult:
        """Compose the widget layout."""
        with Horizontal():
            for i, item in enumerate(self._items):
                is_last = i == len(self._items) - 1

                icon_part = f"{item.icon} " if item.icon else ""
                classes = "breadcrumb-item"
                if is_last:
                    classes += " breadcrumb-current"

                yield Button(
                    f"{icon_part}{item.label}",
                    classes=classes,
                    id=f"breadcrumb-{item.id}",
                    disabled=is_last,
                )

                if not is_last:
                    yield Static(self._separator, classes="breadcrumb-separator")

    def set_items(self, items: List[BreadcrumbItem]) -> None:
        """Update breadcrumb items."""
        self._items = items
        self.refresh()

    def push(self, item: BreadcrumbItem) -> None:
        """Add item to breadcrumb."""
        self._items.append(item)
        self.refresh()

    def pop(self) -> Optional[BreadcrumbItem]:
        """Remove and return last item."""
        if self._items:
            item = self._items.pop()
            self.refresh()
            return item
        return None

    @on(Button.Pressed)
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press events."""
        button_id = event.button.id or ""
        if button_id.startswith("breadcrumb-"):
            item_id = button_id[11:]  # Remove "breadcrumb-"
            for item in self._items:
                if item.id == item_id:
                    self.post_message(self.ItemClicked(item))
                    break


@dataclass
class Tab:
    """A single tab."""

    id: str
    label: str
    icon: str = ""
    closeable: bool = False
    data: Any = None


class TabBar(Widget):
    """
    Tab bar widget for switching between views.

    Example:
        ```python
        tabs = TabBar(tabs=[
            Tab("editor", "Editor", icon="✎"),
            Tab("preview", "Preview", icon="◉"),
            Tab("terminal", "Terminal", icon="💻"),
        ])
        ```
    """

    class TabSelected(Message):
        """Message when a tab is selected."""

        def __init__(self, tab: Tab) -> None:
            """Initialize the widget."""
            super().__init__()
            self.tab = tab

    class TabClosed(Message):
        """Message when a tab is closed."""

        def __init__(self, tab: Tab) -> None:
            """Initialize the widget."""
            super().__init__()
            self.tab = tab

    active_tab: reactive[str] = reactive("")

    def __init__(
        self, tabs: Optional[List[Tab]] = None, active: Optional[str] = None, **kwargs
    ):
        """Initialize the instance."""
        super().__init__(**kwargs)
        self._tabs = tabs or []
        self.active_tab = active or (self._tabs[0].id if self._tabs else "")

    def compose(self) -> ComposeResult:
        """Compose the widget layout."""
        with Horizontal():
            for tab in self._tabs:
                classes = "tab"
                if tab.id == self.active_tab:
                    classes += " tab-active"

                icon_part = f"{tab.icon} " if tab.icon else ""

                with Horizontal(classes=classes, id=f"tab-container-{tab.id}"):
                    yield Button(
                        f"{icon_part}{tab.label}",
                        id=f"tab-{tab.id}",
                    )
                    if tab.closeable:
                        yield Button("×", classes="tab-close", id=f"tab-close-{tab.id}")

            yield Static("", classes="tab-spacer")

    def watch_active_tab(self, old: str, new: str) -> None:
        """Update tab styling when active tab changes."""
        if old:
            try:
                container = self.query_one(f"#tab-container-{old}")
                container.remove_class("tab-active")
            except Exception as error:
                self.log.debug("Previous tab %s is not mounted: %s", old, error)

        if new:
            try:
                container = self.query_one(f"#tab-container-{new}")
                container.add_class("tab-active")
            except Exception as error:
                self.log.debug("Active tab %s is not mounted: %s", new, error)

    def add_tab(self, tab: Tab, activate: bool = True) -> None:
        """Add a new tab."""
        self._tabs.append(tab)
        if activate:
            self.active_tab = tab.id
        self.refresh()

    def remove_tab(self, tab_id: str) -> bool:
        """Remove a tab."""
        for i, tab in enumerate(self._tabs):
            if tab.id == tab_id:
                del self._tabs[i]

                # Update active tab if needed
                if self.active_tab == tab_id and self._tabs:
                    self.active_tab = self._tabs[max(0, i - 1)].id

                self.refresh()
                return True
        return False

    def get_tab(self, tab_id: str) -> Optional[Tab]:
        """Get a tab by ID."""
        for tab in self._tabs:
            if tab.id == tab_id:
                return tab
        return None

    @on(Button.Pressed)
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press events."""
        button_id = event.button.id or ""

        if button_id.startswith("tab-close-"):
            tab_id = button_id[10:]
            tab = self.get_tab(tab_id)
            if tab:
                self.post_message(self.TabClosed(tab))
        elif button_id.startswith("tab-"):
            tab_id = button_id[4:]
            tab = self.get_tab(tab_id)
            if tab and tab.id != self.active_tab:
                self.active_tab = tab.id
                self.post_message(self.TabSelected(tab))
