"""Blend Mode Selector Widget - Aura CLI Paint Tool.

Cyclable button selector for layer blend modes with visual feedback.
"""

from typing import ClassVar

from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.message import Message
from textual.reactive import reactive
from textual.widgets import Button, Label

from aura_cli.application.paint.layers import BlendMode


class BlendModeSelector(Horizontal):
    """Cyclable selector widget for layer blend modes.

    Features:
        - 7 blend modes (Normal, Multiply, Screen, Overlay, Add, Difference, Transparent)
        - Click to cycle through modes
        - Visual hover feedback
        - Reactive blend_mode property
        - Aura color palette integration
    """

    DEFAULT_CSS = """
    BlendModeSelector {
        height: 3;
        background: #1E1E1E;
        border: solid #333333;
        padding: 0 1;
    }

    BlendModeSelector Label {
        width: 12;
        color: #D3D3D3;
    }

    BlendModeSelector Button {
        width: 1fr;
        background: #333333;
        color: #FFFFFF;
        border: solid #D3D3D3;
    }

    BlendModeSelector Button:hover {
        background: #FF00FF;
    }
    """

    blend_mode = reactive(BlendMode.NORMAL)

    MODES: ClassVar[list] = [
        BlendMode.NORMAL,
        BlendMode.MULTIPLY,
        BlendMode.SCREEN,
        BlendMode.OVERLAY,
        BlendMode.ADD,
        BlendMode.DIFFERENCE,
        BlendMode.TRANSPARENT,
    ]

    class BlendModeChanged(Message):
        """Message posted when blend mode changes.

        Attributes:
            blend_mode: Selected blend mode
        """

        def __init__(self, blend_mode: BlendMode) -> None:
            self.blend_mode = blend_mode
            super().__init__()

    def compose(self) -> ComposeResult:
        """Compose selector components."""
        yield Label("Blend Mode:")
        yield Button(self.blend_mode.value.title(), id="mode_button")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press to cycle blend modes.

        Args:
            event: Button press event
        """
        if event.button.id == "mode_button":
            current_idx = self.MODES.index(self.blend_mode)
            next_idx = (current_idx + 1) % len(self.MODES)
            self.blend_mode = self.MODES[next_idx]
            event.button.label = self.blend_mode.value.title()
            self.post_message(self.BlendModeChanged(self.blend_mode))
