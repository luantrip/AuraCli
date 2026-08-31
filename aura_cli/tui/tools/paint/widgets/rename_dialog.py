"""Rename Layer Dialog - Aura CLI Paint Tool.

Modal dialog for renaming layers with validation and keyboard shortcuts.
"""

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.message import Message
from textual.widgets import Button, Input, Label, Static


class RenameLayerDialog(Static):
    """Modal dialog widget for layer renaming operations.

    Features:
        - Input validation (non-empty names)
        - Keyboard shortcuts (Enter to confirm, Esc to cancel)
        - Auto-focus on input field
        - Aura color palette styling
    """

    DEFAULT_CSS = """
    RenameLayerDialog {
        width: 50;
        height: 11;
        background: #1E1E1E;
        border: solid #FF00FF;
        padding: 1;
    }

    RenameLayerDialog Label {
        color: #D3D3D3;
        margin-bottom: 1;
    }

    RenameLayerDialog Input {
        background: #333333;
        color: #FFFFFF;
        border: solid #D3D3D3;
        margin-bottom: 1;
    }

    RenameLayerDialog Button {
        margin: 0 1;
    }
    """

    class LayerRenamed(Message):
        """Message posted when layer is successfully renamed.

        Attributes:
            layer_id: Unique identifier of the renamed layer
            new_name: New name for the layer
        """

        def __init__(self, layer_id: str, new_name: str) -> None:
            self.layer_id = layer_id
            self.new_name = new_name
            super().__init__()

    def __init__(self, layer_id: str, current_name: str) -> None:
        """Initialize rename dialog.

        Args:
            layer_id: Unique identifier of layer to rename
            current_name: Current name to pre-fill in input
        """
        super().__init__()
        self.layer_id = layer_id
        self.current_name = current_name

    def compose(self) -> ComposeResult:
        """Compose dialog components."""
        yield Vertical(
            Label("Rename Layer"),
            Input(value=self.current_name, placeholder="Layer name", id="name_input"),
            Horizontal(
                Button("OK", variant="primary", id="ok"),
                Button("Cancel", id="cancel"),
            ),
        )

    def on_mount(self) -> None:
        """Set focus to input field on mount."""
        self.query_one("#name_input", Input).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press events.

        Args:
            event: Button press event
        """
        if event.button.id == "ok":
            name_input = self.query_one("#name_input", Input)
            new_name = name_input.value.strip()
            if new_name:
                self.post_message(self.LayerRenamed(self.layer_id, new_name))
        self.remove()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle Enter key submission.

        Args:
            event: Input submission event
        """
        new_name = event.value.strip()
        if new_name:
            self.post_message(self.LayerRenamed(self.layer_id, new_name))
        self.remove()
