"""Onion Skin Controls Widget - Aura CLI Paint Tool.

Configuration panel for onion skinning animation preview settings.
"""

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.message import Message
from textual.reactive import reactive
from textual.widgets import Checkbox, Label


class OnionSkinControls(Vertical):
    """Configuration widget for onion skinning settings.

    Features:
        - Enable/disable toggle
        - Previous frames count slider
        - Next frames count slider
        - Opacity adjustment slider
        - Real-time value display
        - Reactive properties for all settings
    """

    DEFAULT_CSS = """
    OnionSkinControls {
        height: auto;
        background: #1E1E1E;
        border: solid #333333;
        padding: 1;
    }

    OnionSkinControls Label {
        color: #D3D3D3;
        margin-bottom: 1;
    }

    OnionSkinControls Checkbox {
        background: #333333;
        color: #FFFFFF;
        margin-bottom: 1;
    }

    OnionSkinControls .slider-row {
        height: 3;
        margin-bottom: 1;
    }

    OnionSkinControls .slider-label {
        width: 18;
        color: #D3D3D3;
    }

    OnionSkinControls .slider-value {
        width: 4;
        text-align: right;
        color: #FFFFFF;
    }
    """

    enabled = reactive(False)
    prev_frames = reactive(1)
    next_frames = reactive(1)
    opacity = reactive(30)

    class OnionSkinChanged(Message):
        """Message posted when onion skin settings change.

        Attributes:
            enabled: Whether onion skinning is enabled
            prev_frames: Number of previous frames to show
            next_frames: Number of next frames to show
            opacity: Opacity percentage for onion skin overlay
        """

        def __init__(
            self, enabled: bool, prev_frames: int, next_frames: int, opacity: int
        ) -> None:
            self.enabled = enabled
            self.prev_frames = prev_frames
            self.next_frames = next_frames
            self.opacity = opacity
            super().__init__()

    def compose(self) -> ComposeResult:
        """Compose control components."""
        yield Label("Onion Skinning")
        yield Checkbox("Enable", id="enable_check", value=self.enabled)
        yield Horizontal(
            Label("Previous:", classes="slider-label"),
            Label(str(self.prev_frames), classes="slider-value", id="prev_value"),
            classes="slider-row",
        )
        yield Horizontal(
            Label("Next:", classes="slider-label"),
            Label(str(self.next_frames), classes="slider-value", id="next_value"),
            classes="slider-row",
        )
        yield Horizontal(
            Label("Opacity:", classes="slider-label"),
            Label(f"{self.opacity}%", classes="slider-value", id="opacity_value"),
            classes="slider-row",
        )

    def on_checkbox_changed(self, event: Checkbox.Changed) -> None:
        """Handle checkbox state changes.

        Args:
            event: Checkbox change event
        """
        if event.checkbox.id == "enable_check":
            self.enabled = event.value
            self._emit_change()

    def _emit_change(self) -> None:
        """Emit settings change message with current values."""
        self.post_message(
            self.OnionSkinChanged(
                self.enabled, self.prev_frames, self.next_frames, self.opacity
            )
        )
