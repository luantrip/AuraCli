"""Knight Rider Spinner Widget for Aura TUI.

Implements a sophisticated "Knight Rider" style scanning animation for loading states.
"""

from __future__ import annotations

from dataclasses import dataclass
import logging
from typing import Any, ClassVar, List, Literal, Tuple

from textual.reactive import reactive
from textual.widgets import Static

logger = logging.getLogger(__name__)


@dataclass
class SpinnerConfig:
    """Configuration for the spinner animation."""

    width: int = 20
    style: Literal["block", "diamond", "dot", "wave", "pulse"] = "block"
    color: str = "#00d9ff"
    trail_length: int = 4
    hold_start: int = 2
    hold_end: int = 2
    fps: int = 30


class KnightRiderSpinner(Static):
    """Knight Rider style scanning animation widget."""

    CHAR_STYLES: ClassVar[dict] = {
        "block": ["█", "▓", "▒", "░", " "],
        "diamond": ["◆", "◇", "◈", "○", " "],
        "dot": ["●", "◐", "○", "◌", " "],
        "wave": ["█", "▇", "▆", "▅", "▄", "▃", "▂", "▁", " "],
        "pulse": ["⣿", "⣷", "⣯", "⣟", "⡿", "⢿", "⣻", "⣽", " "],
    }

    message = reactive("Carregando...")
    running = reactive(True)

    def __init__(
        self,
        width: int = 20,
        style: Literal["block", "diamond", "dot", "wave", "pulse"] = "block",
        color: str = "#00d9ff",
        message: str = "Carregando...",
        trail_length: int = 4,
        fps: int = 30,
        **kwargs,
    ):
        """Initialize the Knight Rider spinner with visual style and animation parameters."""
        super().__init__(**kwargs)
        self.config = SpinnerConfig(
            width=width,
            style=style,
            color=color,
            trail_length=trail_length,
            fps=fps,
        )
        self.message = message

        self._frame = 0
        self._position = 0.0
        self._direction = 1
        self._hold_counter = 0
        self._timer: Any = None

    def on_mount(self) -> None:
        """Initialize widget state after mounting."""
        self._start_animation()

    def on_unmount(self) -> None:
        """Clean up resources on unmount."""
        self._stop_animation()

    def _start_animation(self) -> None:
        """Start the animation timer."""
        if self._timer is None:
            interval = 1.0 / self.config.fps
            self._timer = self.set_interval(interval, self._animate)

    def _stop_animation(self) -> None:
        """Stop the animation timer."""
        if self._timer:
            self._timer.stop()
            self._timer = None

    def _animate(self) -> None:  # type: ignore[override]
        """Advance one animation frame."""
        if not self.running:
            return

        self._frame += 1

        if self._hold_counter > 0:
            self._hold_counter -= 1
            self.refresh()
            return

        speed = 0.3
        self._position += speed * self._direction

        if self._position >= self.config.width - 1:
            self._position = self.config.width - 1
            self._direction = -1
            self._hold_counter = self.config.hold_end
        elif self._position <= 0:
            self._position = 0
            self._direction = 1
            self._hold_counter = self.config.hold_start

        self.refresh()

    def render(self) -> str:
        """Render the widget content."""
        chars = self.CHAR_STYLES.get(self.config.style, self.CHAR_STYLES["block"])

        result = []
        for i in range(self.config.width):
            char, _intensity = self._get_char_at_position(i, chars)
            result.append(char)

        bar = "".join(result)

        if self.message:
            return f"{bar}  {self.message}"

        return bar

    def _get_char_at_position(self, pos: int, chars: List[str]) -> Tuple[str, float]:
        """Get the character to render at a given position."""
        distance = abs(pos - self._position)

        if distance < 0.5:
            return chars[0], 1.0
        elif distance < 1.5:
            return chars[min(1, len(chars) - 1)], 0.8
        elif distance < 2.5:
            return chars[min(2, len(chars) - 1)], 0.6
        elif distance < 3.5:
            return chars[min(3, len(chars) - 1)], 0.4
        elif distance < self.config.trail_length + 0.5:
            return chars[min(4, len(chars) - 1)], 0.2
        else:
            return " ", 0.0

    def start(self) -> None:
        """Start the spinner animation."""
        self.running = True
        self._start_animation()

    def stop(self) -> None:
        """Stop the spinner animation."""
        self.running = False
        self._stop_animation()

    def set_message(self, message: str) -> None:
        """Update the spinner message text."""
        self.message = message


class CompactSpinner(Static):
    """Compact single-character spinner for inline use."""

    FRAMES: ClassVar[list] = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]

    message = reactive("")

    def __init__(self, message: str = "", color: str = "#00d9ff", **kwargs):
        """Initialize the widget."""
        super().__init__(**kwargs)
        self.message = message
        self.color = color
        self._frame = 0
        self._timer: Any = None

    def on_mount(self) -> None:
        """Initialize widget state after mounting."""
        self._timer = self.set_interval(0.08, self._animate)

    def on_unmount(self) -> None:
        """Clean up resources on unmount."""
        if self._timer:
            self._timer.stop()

    def _animate(self) -> None:  # type: ignore[override]
        """Advance one animation frame."""
        self._frame = (self._frame + 1) % len(self.FRAMES)
        self.refresh()

    def render(self) -> str:
        """Render the widget content."""
        char = self.FRAMES[self._frame]
        if self.message:
            return f"{char} {self.message}"
        return char


class ProgressSpinner(Static):
    """Progress spinner with percentage display."""

    progress = reactive(0.0)
    message = reactive("")

    def __init__(self, message: str = "", **kwargs):
        """Initialize the widget."""
        super().__init__(**kwargs)
        self.message = message
        self._spinner = "⠋"
        self._spinner_frames = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
        self._frame = 0
        self._timer: Any = None

    def on_mount(self) -> None:
        """Initialize widget state after mounting."""
        self._timer = self.set_interval(0.08, self._animate)

    def on_unmount(self) -> None:
        """Clean up resources on unmount."""
        if self._timer:
            self._timer.stop()

    def _animate(self) -> None:  # type: ignore[override]
        """Advance one animation frame."""
        self._frame = (self._frame + 1) % len(self._spinner_frames)
        self._spinner = self._spinner_frames[self._frame]
        self.refresh()

    def render(self) -> str:
        """Render the widget content."""
        bar_width = 20
        filled = int(bar_width * self.progress)
        empty = bar_width - filled

        bar = "│" + "█" * filled + "░" * empty + "│"
        percent = f" {self.progress * 100:5.1f}%"

        result = f"{self._spinner} {bar}{percent}"

        if self.message:
            result += f"  {self.message}"

        return result

    def set_progress(self, value: float, message: str = "") -> None:
        """Update the progress value."""
        self.progress = max(0.0, min(1.0, value))
        if message:
            self.message = message
