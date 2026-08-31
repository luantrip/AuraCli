"""
Shared Loading Components.

Provides spinners, progress indicators, and loading animations.
"""

from __future__ import annotations

from typing import ClassVar

from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import ProgressBar, Static


class LoadingSpinner(Widget):
    """
    Animated loading spinner.

    Example:
        ```python
        spinner = LoadingSpinner(message="Loading...")
        spinner.start()
        # ... do work ...
        spinner.stop()
        ```
    """

    # Spinner animation frames
    FRAMES: ClassVar[list] = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
    DOTS_FRAMES: ClassVar[list] = ["⣾", "⣽", "⣻", "⢿", "⡿", "⣟", "⣯", "⣷"]
    BAR_FRAMES: ClassVar[list] = [
        "▏",
        "▎",
        "▍",
        "▌",
        "▋",
        "▊",
        "▉",
        "█",
        "▉",
        "▊",
        "▋",
        "▌",
        "▍",
        "▎",
    ]

    is_spinning: reactive[bool] = reactive(False)
    frame_index: reactive[int] = reactive(0)
    message: reactive[str] = reactive("")

    def __init__(
        self, message: str = "", style: str = "default", interval: float = 0.1, **kwargs
    ):
        """Initialize the instance."""
        super().__init__(**kwargs)
        self.message = message
        self._interval = interval

        if style == "dots":
            self._frames = self.DOTS_FRAMES
        elif style == "bar":
            self._frames = self.BAR_FRAMES
        else:
            self._frames = self.FRAMES

    def compose(self) -> ComposeResult:
        """Compose the widget layout."""
        with Horizontal():
            yield Static("", classes="spinner-frame", id="frame")
            yield Static(self.message, classes="spinner-message", id="message")

    def start(self) -> None:
        """Start the spinner animation."""
        self.is_spinning = True
        self._animate()

    def stop(self) -> None:
        """Stop the spinner animation."""
        self.is_spinning = False

    def _animate(self) -> None:  # type: ignore[override]
        """Animate the spinner."""
        if not self.is_spinning:
            return

        self.frame_index = (self.frame_index + 1) % len(self._frames)
        self.set_timer(self._interval, self._animate)

    def watch_frame_index(self, value: int) -> None:
        """React to frame index changes."""
        try:
            frame_widget = self.query_one("#frame", Static)
            frame_widget.update(self._frames[value])
        except Exception as error:
            self.log.debug("Spinner frame is not mounted yet: %s", error)

    def watch_message(self, value: str) -> None:
        """React to message changes."""
        try:
            message_widget = self.query_one("#message", Static)
            message_widget.update(value)
        except Exception as error:
            self.log.debug("Spinner message is not mounted yet: %s", error)


class ProgressIndicator(Widget):
    """
    Progress indicator with optional label.

    Example:
        ```python
        progress = ProgressIndicator(label="Downloading")
        progress.update(50, "50% complete")
        ```
    """

    progress: reactive[float] = reactive(0.0)
    label: reactive[str] = reactive("")
    status: reactive[str] = reactive("")

    def __init__(
        self,
        label: str = "",
        total: float = 100.0,
        show_percentage: bool = True,
        **kwargs,
    ):
        """Initialize the instance."""
        super().__init__(**kwargs)
        self.label = label
        self._total = total
        self._show_percentage = show_percentage

    def compose(self) -> ComposeResult:
        """Compose the widget layout."""
        if self.label:
            yield Static(self.label, classes="progress-label", id="label")
        yield ProgressBar(total=self._total, id="progress-bar")
        yield Static("", classes="progress-status", id="status")

    def update(self, progress: float, status: str = "") -> None:
        """Update progress and status."""
        self.progress = progress
        if status:
            self.status = status
        elif self._show_percentage:
            percent = (progress / self._total) * 100
            self.status = f"{percent:.1f}%"

    def watch_progress(self, value: float) -> None:
        """React to progress changes."""
        try:
            bar = self.query_one("#progress-bar", ProgressBar)
            bar.update(progress=value)
        except Exception as error:
            self.log.debug("Progress bar is not mounted yet: %s", error)

    def watch_status(self, value: str) -> None:
        """React to status message changes."""
        try:
            status_widget = self.query_one("#status", Static)
            status_widget.update(value)
        except Exception as error:
            self.log.debug("Progress status is not mounted yet: %s", error)

    def watch_label(self, value: str) -> None:
        """React to label changes."""
        try:
            label_widget = self.query_one("#label", Static)
            label_widget.update(value)
        except Exception as error:
            self.log.debug("Progress label is not mounted yet: %s", error)


class PulseAnimation(Widget):
    """
    Pulsing animation indicator.

    Example:
        ```python
        pulse = PulseAnimation(text="Working...")
        pulse.start()
        ```
    """

    is_pulsing: reactive[bool] = reactive(False)
    text: reactive[str] = reactive("")

    def __init__(self, text: str = "...", interval: float = 0.5, **kwargs):
        """Initialize the widget."""
        super().__init__(**kwargs)
        self.text = text
        self._interval = interval
        self._is_bright = True

    def compose(self) -> ComposeResult:
        """Compose the widget layout."""
        yield Static(self.text, classes="pulse-text", id="pulse")

    def start(self) -> None:
        """Start pulsing."""
        self.is_pulsing = True
        self._animate()

    def stop(self) -> None:
        """Stop pulsing."""
        self.is_pulsing = False

    def _animate(self) -> None:  # type: ignore[override]
        """Advance one animation frame."""
        if not self.is_pulsing:
            return

        self._is_bright = not self._is_bright

        try:
            widget = self.query_one("#pulse", Static)
            if self._is_bright:
                widget.remove_class("pulse-dim")
                widget.add_class("pulse-text")
            else:
                widget.remove_class("pulse-text")
                widget.add_class("pulse-dim")
        except Exception as error:
            self.log.debug("Pulse widget is not mounted yet: %s", error)

        self.set_timer(self._interval, self._animate)
