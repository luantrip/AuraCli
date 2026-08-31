"""Loading Widget for Aura TUI.

Animated loading indicator with Nebula theme for command processing and LLM queries.
"""

from typing import ClassVar, Optional

from textual import on
from textual.containers import Horizontal
from textual.css.query import NoMatches
from textual.message import Message
from textual.reactive import reactive
from textual.widgets import Label, Static

import aura_cli.tui.constants as tui_constants


class AuraLoadingIndicator(Static):
    """Animated loading indicator with Nebula theme.

    Features:
    - Animated spinner with hexagon frames
    - Configurable status message
    - Show/hide with reactive properties
    - CSS-based animations
    """

    class Show(Message):
        """Posted to show the loading indicator."""

        def __init__(self, message: Optional[str] = None) -> None:
            """Initialize the instance."""
            self.message = message
            super().__init__()

    class Hide(Message):
        """Posted to hide the loading indicator."""

    message: reactive[str] = reactive("")
    is_visible: reactive[bool] = reactive(False)

    SPINNER_FRAMES: ClassVar[list[str]] = ["⬡", "⬢", "⬡", "⬢"]
    _frame_index: int = 0

    def __init__(self, message: str = "", **kwargs):
        """Initialize the instance."""
        super().__init__(**kwargs)
        self._spinner_frames = self._build_spinner_frames()
        self._frame_index = 0
        self.message = message

    @staticmethod
    def _build_spinner_frames() -> list[str]:
        if tui_constants.ACTIVE_GLYPH_MODE == "ascii":
            return ["...", "..", ".", ".."]
        return ["⬡", "⬢", "⬡", "⬢"]

    def compose(self):
        """Compose loading indicator structure."""
        with Horizontal():
            yield Label(
                tui_constants.get_glyph("LOADING"), id="spinner", classes="spinner"
            )
            yield Label("", id="message", classes="message")
            yield Label(
                "" if tui_constants.ACTIVE_GLYPH_MODE == "ascii" else "...",
                id="dots",
                classes="dots",
            )

    def on_mount(self) -> None:
        """Start animation timer when mounted."""
        self.set_interval(0.25, self._animate)
        self.watch_is_visible(self.is_visible)
        try:
            msg_label = self.query_one("#message", Label)
            msg_label.update(self.message)
        except NoMatches:
            return

    def _animate(self) -> None:  # type: ignore[override]
        """Advance animation frame."""
        if self.is_visible:
            self._frame_index = (self._frame_index + 1) % len(self._spinner_frames)
            spinner = self.query_one("#spinner", Label)
            spinner.update(self._spinner_frames[self._frame_index])

            dots_count = (self._frame_index % 3) + 1
            dots = self.query_one("#dots", Label)
            dots.update("." * dots_count)

    def watch_message(self, message: str) -> None:
        """Update message when it changes."""
        try:
            msg_label = self.query_one("#message", Label)
            msg_label.update(message)
        except NoMatches:
            return

    def watch_is_visible(self, visible: bool) -> None:
        """Update visibility when it changes."""
        if visible:
            self.remove_class("hidden")
        else:
            self.add_class("hidden")

    def show(self, message: str | None = None) -> None:
        """Show the loading indicator with optional message."""
        if message is not None:
            self.message = message
        self.is_visible = True

    def hide(self) -> None:
        """Hide the loading indicator."""
        self.is_visible = False

    @on(Show)
    def on_show(self, event: Show) -> None:
        """Handle widget show event."""
        self.show(event.message)

    @on(Hide)
    def on_hide(self, event: Hide) -> None:
        """Handle widget hide event."""
        self.hide()


class AuraProgressBar(Static):
    """Progress bar with Nebula theme styling.

    Features:
    - Progress display with percentage
    - Configurable label
    - CSS-based styling
    """

    progress: reactive[float] = reactive(0.0)
    label: reactive[str] = reactive("")

    BAR_WIDTH = 30

    def __init__(self, label: str = "", **kwargs):
        """Initialize the instance."""
        super().__init__(**kwargs)
        self.label = label

    def compose(self):
        """Compose progress bar structure."""
        with Horizontal():
            if self.label:
                yield Label("", id="progress-label", classes="progress-label")
            yield Static(
                "", id="progress-bar-container", classes="progress-bar-container"
            )
            yield Label("", id="progress-percentage", classes="progress-percentage")

    def on_mount(self) -> None:
        """Initialize display after mount."""
        self._update_display()
        if self.label:
            try:
                label_widget = self.query_one("#progress-label", Label)
                label_widget.update(f"{self.label} ")
            except NoMatches:
                return

    def watch_progress(self, progress: float) -> None:
        """Update progress bar when value changes."""
        self._update_display()

    def watch_label(self, label: str) -> None:
        """Update label when it changes."""
        try:
            if label:
                label_widget = self.query_one("#progress-label", Label)
                label_widget.update(f"{label} ")
            self._update_display()
        except NoMatches:
            return

    def _update_display(self) -> None:
        """Update the visual display of the progress bar."""
        try:
            filled_width = int(self.BAR_WIDTH * (self.progress / 100))
            empty_width = self.BAR_WIDTH - filled_width

            bar_container = self.query_one("#progress-bar-container", Static)
            fill_text = "█" * filled_width + "░" * empty_width
            bar_container.update(fill_text)

            if filled_width > 0:
                bar_container.add_class("progress-bar-fill")
                if self.progress >= 100:
                    bar_container.add_class("complete")
            else:
                bar_container.remove_class("progress-bar-fill", "complete")

            percentage = self.query_one("#progress-percentage", Label)
            percentage.update(f"{self.progress:.0f}%")
            percentage.remove_class("complete")
            if self.progress >= 100:
                percentage.add_class("complete")
        except NoMatches:
            return

    def set_progress(self, value: float, label: str | None = None) -> None:
        """Update progress value (0-100)."""
        self.progress = max(0.0, min(100.0, value))
        if label:
            self.label = label
