"""Opacity Slider Widget - Aura CLI Paint Tool.

Provides an interactive slider for controlling layer opacity with visual feedback
and click-to-adjust functionality.
"""

from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.message import Message
from textual.reactive import reactive
from textual.widgets import Label, Static


class OpacitySlider(Horizontal):
    """Interactive slider widget for layer opacity control.

    Features:
        - Visual track with gradient fill
        - Click-to-adjust interaction
        - Real-time value display (0-100%)
        - Reactive opacity property
        - Aura color palette integration
    """

    DEFAULT_CSS = """
    OpacitySlider {
        height: 3;
        background: #1E1E1E;
        border: solid #333333;
        padding: 0 1;
    }

    OpacitySlider Label {
        width: 10;
        color: #D3D3D3;
    }

    OpacitySlider .slider-track {
        width: 1fr;
        height: 1;
        background: #333333;
    }

    OpacitySlider .slider-fill {
        background: #FF00FF;
        height: 1;
    }

    OpacitySlider .value-label {
        width: 6;
        text-align: right;
        color: #FFFFFF;
    }
    """

    opacity = reactive(100)

    class OpacityChanged(Message):
        """Message posted when opacity value changes.

        Attributes:
            opacity: Normalized opacity value (0.0-1.0)
        """

        def __init__(self, opacity: float) -> None:
            self.opacity = opacity
            super().__init__()

    def compose(self) -> ComposeResult:
        """Compose slider components."""
        yield Label("Opacity:")
        yield Static("", classes="slider-track", id="track")
        yield Label("100%", classes="value-label", id="value")

    def on_mount(self) -> None:
        """Initialize display on mount."""
        self._update_display()

    def on_click(self, event) -> None:
        """Handle click events on slider track.

        Args:
            event: Click event with screen coordinates
        """
        track = self.query_one("#track")
        if track.region.contains(event.screen_offset):
            rel_x = event.screen_offset.x - track.region.x
            width = track.region.width
            self.opacity = int((rel_x / width) * 100) if width > 0 else 100
            self._update_display()
            self.post_message(self.OpacityChanged(self.opacity / 100.0))

    def _update_display(self) -> None:
        """Update visual representation of slider value."""
        value_label = self.query_one("#value", Label)
        value_label.update(f"{self.opacity}%")

        track = self.query_one("#track")
        fill_width = int((self.opacity / 100.0) * track.region.width)
        track.styles.background = (
            f"linear-gradient(90deg, #FF00FF {fill_width}ch, #333333 {fill_width}ch)"
        )
