"""
Shared Panel Components.

Provides collapsible panels, split views, and other container widgets.
"""

from __future__ import annotations

from enum import Enum
from typing import Optional

from textual import on
from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.css.query import NoMatches
from textual.message import Message
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Button, Static


class CollapsiblePanel(Widget):
    """
    Panel that can be collapsed/expanded.

    Example:
        ```python
        panel = CollapsiblePanel(title="Details", collapsed=False)
        with panel:
            yield Label("Panel content here")
        ```
    """

    class Toggled(Message):
        """Message when panel is toggled."""

        def __init__(self, collapsed: bool) -> None:
            """Initialize the widget."""
            super().__init__()
            self.collapsed = collapsed

    collapsed: reactive[bool] = reactive(False)

    def __init__(
        self,
        title: str = "Panel",
        collapsed: bool = False,
        collapsible: bool = True,
        icon_expanded: str = "▼",
        icon_collapsed: str = "▶",
        **kwargs,
    ):
        """Initialize the instance."""
        super().__init__(**kwargs)
        self.title = title
        self.collapsed = collapsed
        self.collapsible = collapsible
        self._icon_expanded = icon_expanded
        self._icon_collapsed = icon_collapsed
        self._content_widgets = []  # type: ignore[var-annotated]

    def compose(self) -> ComposeResult:
        """Compose the widget layout."""
        icon = self._icon_collapsed if self.collapsed else self._icon_expanded

        with Horizontal(classes="panel-header"):
            if self.collapsible:
                yield Button(icon, classes="panel-toggle", id="toggle")
            yield Static(self.title, classes="panel-title")

        content_classes = "panel-content"
        if self.collapsed:
            content_classes += " panel-content-collapsed"
            self.add_class("panel-collapsed")

        yield Container(*self._content_widgets, classes=content_classes, id="content")

    def watch_collapsed(self, value: bool) -> None:
        """Update UI when collapsed state changes."""
        if not self.is_mounted:
            return

        try:
            # Update icon
            if self.collapsible:
                toggle = self.query_one("#toggle", Button)
                icon = self._icon_collapsed if value else self._icon_expanded
                toggle.label = icon

            # Update content visibility
            content = self.query_one("#content", Container)
            if value:
                content.add_class("panel-content-collapsed")
                self.add_class("panel-collapsed")
            else:
                content.remove_class("panel-content-collapsed")
                self.remove_class("panel-collapsed")
        except NoMatches:
            return  # compose() applies the initial state once the DOM exists.

    def toggle(self) -> None:
        """Toggle collapsed state."""
        self.collapsed = not self.collapsed
        self.post_message(self.Toggled(self.collapsed))

    def expand(self) -> None:  # type: ignore[override]
        """Expand the panel."""
        self.collapsed = False

    def collapse(self) -> None:
        """Collapse the panel."""
        self.collapsed = True

    @on(Button.Pressed, "#toggle")
    def on_toggle_pressed(self) -> None:
        """Handle toggle button press."""
        self.toggle()


class SplitDirection(Enum):
    """Direction of split."""

    HORIZONTAL = "horizontal"
    VERTICAL = "vertical"


class SplitPanel(Widget):
    """
    Split panel with resizable panes.

    Example:
        ```python
        split = SplitPanel(direction=SplitDirection.HORIZONTAL)
        split.set_left(FileTree())
        split.set_right(CodeEditor())
        ```
    """

    class Resized(Message):
        """Message when panel is resized."""

        def __init__(self, ratio: float) -> None:
            """Initialize the widget."""
            super().__init__()
            self.ratio = ratio

    ratio: reactive[float] = reactive(0.3)  # First pane ratio

    def __init__(
        self,
        direction: SplitDirection = SplitDirection.HORIZONTAL,
        ratio: float = 0.3,
        min_size: int = 10,
        resizable: bool = True,
        **kwargs,
    ):
        """Initialize the instance."""
        super().__init__(**kwargs)
        self.direction = direction
        self.ratio = ratio
        self._min_size = min_size
        self._resizable = resizable
        self._first_widget: Optional[Widget] = None
        self._second_widget: Optional[Widget] = None

    def compose(self) -> ComposeResult:
        """Compose the widget layout."""
        ContainerClass = (
            Horizontal if self.direction == SplitDirection.HORIZONTAL else Vertical
        )
        divider_class = f"split-divider split-divider-{self.direction.value}"

        with ContainerClass():
            yield Container(classes="split-pane split-pane-first", id="first-pane")
            yield Static("", classes=divider_class, id="divider")
            yield Container(classes="split-pane split-pane-second", id="second-pane")

    def on_mount(self) -> None:
        """Mount pre-set widgets if they exist."""
        if self._first_widget:
            self.query_one("#first-pane", Container).mount(self._first_widget)
        if self._second_widget:
            self.query_one("#second-pane", Container).mount(self._second_widget)
        self._update_sizes()

    def set_first(self, widget: Widget) -> None:
        """Set the first pane content."""
        self._first_widget = widget
        if self.is_mounted:
            try:
                pane = self.query_one("#first-pane", Container)
                pane.remove_children()
                pane.mount(widget)
            except NoMatches:
                return

    def set_second(self, widget: Widget) -> None:
        """Set the second pane content."""
        self._second_widget = widget
        if self.is_mounted:
            try:
                pane = self.query_one("#second-pane", Container)
                pane.remove_children()
                pane.mount(widget)
            except NoMatches:
                return

    # Aliases for clarity
    def set_left(self, widget: Widget) -> None:
        """Set left pane (horizontal split)."""
        self.set_first(widget)

    def set_right(self, widget: Widget) -> None:
        """Set right pane (horizontal split)."""
        self.set_second(widget)

    def set_top(self, widget: Widget) -> None:
        """Set top pane (vertical split)."""
        self.set_first(widget)

    def set_bottom(self, widget: Widget) -> None:
        """Set bottom pane (vertical split)."""
        self.set_second(widget)

    def set_ratio(self, ratio: float) -> None:
        """Set the split ratio."""
        self.ratio = max(0.1, min(0.9, ratio))
        self._update_sizes()

    def _update_sizes(self) -> None:
        """Update pane sizes based on ratio."""
        if not self.is_mounted:
            return
        try:
            first = self.query_one("#first-pane", Container)
            second = self.query_one("#second-pane", Container)

            if self.direction == SplitDirection.HORIZONTAL:
                first.styles.width = f"{int(self.ratio * 100)}%"
                second.styles.width = f"{int((1 - self.ratio) * 100)}%"
            else:
                first.styles.height = f"{int(self.ratio * 100)}%"
                second.styles.height = f"{int((1 - self.ratio) * 100)}%"
        except NoMatches:
            return
