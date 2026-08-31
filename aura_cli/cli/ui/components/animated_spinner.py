"""
AnimatedSpinner - Advanced spinner with multiple animation styles.

Provides various spinner styles for different contexts:
- Dots: Standard spinner (⠋⠙⠹...)
- Knight Rider: LED bar animation
- Pulse: Pulsing circle
- Wave: Wave pattern
- Blocks: Progress blocks
"""

import contextlib
from dataclasses import dataclass
from enum import Enum
import time
from typing import ClassVar, Optional

from rich.console import Console, RenderableType
from rich.live import Live
from rich.text import Text

from aura_cli.cli.ui.theme_manager import get_theme_manager
from aura_cli.cli.utils.thread_manager import get_thread_manager


class SpinnerStyle(str, Enum):
    """Available spinner animation styles."""

    DOTS = "dots"
    KNIGHT_RIDER = "knight_rider"
    PULSE = "pulse"
    WAVE = "wave"
    BLOCKS = "blocks"
    BOUNCE = "bounce"
    ARROW = "arrow"


@dataclass
class SpinnerConfig:
    """Spinner configuration."""

    style: SpinnerStyle = SpinnerStyle.DOTS
    speed: float = 0.1
    width: int = 10
    color: Optional[str] = None
    secondary_color: Optional[str] = None


class AnimatedSpinner:
    """
    Advanced animated spinner with multiple styles.

    Provides contextual loading indicators with customizable
    animations and colors.
    """

    FRAMES: ClassVar[dict] = {
        SpinnerStyle.DOTS: ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"],
        SpinnerStyle.PULSE: ["○", "◔", "◑", "◕", "●", "◕", "◑", "◔"],
        SpinnerStyle.WAVE: [
            "▁",
            "▂",
            "▃",
            "▄",
            "▅",
            "▆",
            "▇",
            "█",
            "▇",
            "▆",
            "▅",
            "▄",
            "▃",
            "▂",
        ],
        SpinnerStyle.BOUNCE: ["⠁", "⠂", "⠄", "⠂"],
        SpinnerStyle.ARROW: ["←", "↖", "↑", "↗", "→", "↘", "↓", "↙"],
    }

    def __init__(
        self,
        message: str = "",
        config: Optional[SpinnerConfig] = None,
        console: Optional[Console] = None,
    ):
        """Initialize the animated spinner with message, config, and console."""
        self.message = message
        self.config = config or SpinnerConfig()
        self.console = console or Console()
        self._frame = 0
        self._live: Optional[Live] = None
        self._is_spinning = False
        self._knight_rider_pos = 0
        self._knight_rider_direction = 1

    def _get_frame(self) -> str:
        """Get current animation frame."""
        style = self.config.style

        if style == SpinnerStyle.KNIGHT_RIDER:
            return self._get_knight_rider_frame()
        elif style == SpinnerStyle.BLOCKS:
            return self._get_blocks_frame()

        frames = self.FRAMES.get(style, self.FRAMES[SpinnerStyle.DOTS])
        return frames[self._frame % len(frames)]

    def _get_knight_rider_frame(self) -> str:
        """Generate Knight Rider LED bar frame."""
        theme = get_theme_manager()
        width = self.config.width
        self.config.color or theme.get_color("error")
        self.config.secondary_color or theme.get_color("muted")

        pos = self._knight_rider_pos
        bar = ""

        for i in range(width):
            if i == pos:
                bar += "█"
            elif abs(i - pos) == 1:
                bar += "▓"
            elif abs(i - pos) == 2:
                bar += "░"
            else:
                bar += "·"

        self._knight_rider_pos += self._knight_rider_direction
        if self._knight_rider_pos >= width - 1 or self._knight_rider_pos <= 0:
            self._knight_rider_direction *= -1

        return bar

    def _get_blocks_frame(self) -> str:
        """Generate blocks progress frame."""
        width = self.config.width
        filled = self._frame % (width + 1)
        return "█" * filled + "░" * (width - filled)

    def render(self) -> RenderableType:
        """
        Render current spinner state (public interface).

        Returns current frame with message if set.
        """
        return self._render()

    def _render(self) -> RenderableType:
        """Render current spinner state."""
        theme = get_theme_manager()
        color = self.config.color or theme.get_color("accent")

        result = Text()
        frame = self._get_frame()

        if self.config.style == SpinnerStyle.KNIGHT_RIDER:
            result.append("[", style="dim")
            for char in frame:
                if char == "█":
                    result.append(char, style=f"bold {color}")
                elif char == "▓":
                    result.append(char, style=color)
                elif char == "░":
                    result.append(char, style=f"dim {color}")
                else:
                    result.append(char, style="dim")
            result.append("]", style="dim")
        else:
            result.append(frame, style=f"bold {color}")

        if self.message:
            result.append(f" {self.message}", style=theme.get_style("body"))

        return result

    def start(self) -> None:
        """Start the spinner animation."""
        self._is_spinning = True
        self._frame = 0

        self._live = Live(
            self._render(),
            console=self.console,
            refresh_per_second=int(1 / self.config.speed),
            transient=True,
        )
        self._live.start()

        thread_manager = get_thread_manager()
        thread_name = f"animated_spinner_{id(self)}"
        self._thread = thread_manager.register_thread(
            name=thread_name,
            target=self._animate,
            daemon=True,
            shutdown_timeout=1.0,
        )

    def stop(self, final_message: Optional[str] = None) -> None:
        """Stop the spinner."""
        self._is_spinning = False
        live, self._live = self._live, None
        if live:
            if final_message:
                live.update(Text(final_message))
            live.stop()

    def update(self, message: str) -> None:
        """Update spinner message."""
        self.message = message
        live = self._live
        if live:
            live.update(self._render())

    def _animate(self) -> None:
        """Animation loop."""
        while self._is_spinning:
            self._frame += 1
            live = self._live  # local copy — avoids TOCTOU with stop()
            if live is not None:
                with contextlib.suppress(Exception):
                    live.update(self._render())
            time.sleep(self.config.speed)

    def __enter__(self) -> "AnimatedSpinner":
        """Context manager entry."""
        self.start()
        return self

    def __exit__(self, *args) -> None:
        """Context manager exit."""
        self.stop()


class SpinnerFactory:
    """Factory for creating pre-configured spinners."""

    @staticmethod
    def dots(message: str = "", console: Optional[Console] = None) -> AnimatedSpinner:
        """Create dots spinner."""
        return AnimatedSpinner(
            message,
            SpinnerConfig(style=SpinnerStyle.DOTS),
            console,
        )

    @staticmethod
    def knight_rider(
        message: str = "", console: Optional[Console] = None
    ) -> AnimatedSpinner:
        """Create Knight Rider spinner."""
        theme = get_theme_manager()
        return AnimatedSpinner(
            message,
            SpinnerConfig(
                style=SpinnerStyle.KNIGHT_RIDER,
                speed=0.05,
                width=15,
                color=theme.get_color("error"),
            ),
            console,
        )

    @staticmethod
    def pulse(message: str = "", console: Optional[Console] = None) -> AnimatedSpinner:
        """Create pulse spinner."""
        return AnimatedSpinner(
            message,
            SpinnerConfig(style=SpinnerStyle.PULSE, speed=0.15),
            console,
        )

    @staticmethod
    def wave(message: str = "", console: Optional[Console] = None) -> AnimatedSpinner:
        """Create wave spinner."""
        return AnimatedSpinner(
            message,
            SpinnerConfig(style=SpinnerStyle.WAVE, speed=0.08),
            console,
        )

    @staticmethod
    def for_context(
        context: str,
        message: str = "",
        console: Optional[Console] = None,
    ) -> AnimatedSpinner:
        """
        Create spinner appropriate for context.

        Args:
            context: "llm", "tool", "file", "thinking", "loading"
            message: Spinner message
            console: Optional console

        Returns:
            Configured spinner
        """
        theme = get_theme_manager()

        context_configs = {
            "llm": SpinnerConfig(
                style=SpinnerStyle.DOTS,
                color=theme.get_color("accent"),
            ),
            "tool": SpinnerConfig(
                style=SpinnerStyle.BLOCKS,
                color=theme.get_color("warning"),
                width=10,
            ),
            "file": SpinnerConfig(
                style=SpinnerStyle.PULSE,
                color=theme.get_color("success"),
            ),
            "thinking": SpinnerConfig(
                style=SpinnerStyle.WAVE,
                color=theme.get_color("secondary"),
            ),
            "loading": SpinnerConfig(
                style=SpinnerStyle.KNIGHT_RIDER,
                color=theme.get_color("error"),
                width=12,
            ),
        }

        config = context_configs.get(context, SpinnerConfig())
        return AnimatedSpinner(message, config, console)
