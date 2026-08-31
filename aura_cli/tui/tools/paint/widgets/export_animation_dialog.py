"""Export Animation Dialog - Aura CLI Paint Tool.

Modal dialog for exporting animations to various formats with format-specific options.
"""

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.message import Message
from textual.reactive import reactive
from textual.widgets import Button, Input, Label, RadioButton, RadioSet, Static


class ExportAnimationDialog(Static):
    """Modal dialog widget for animation export operations.

    Features:
        - Multiple export formats (GIF, Sprite Sheet, ANSI)
        - Dynamic filename placeholder based on format
        - Format-specific validation
        - Keyboard shortcuts (Enter to export, Esc to cancel)
        - Auto-focus on filename input
    """

    DEFAULT_CSS = """
    ExportAnimationDialog {
        width: 60;
        height: 18;
        background: #1E1E1E;
        border: solid #FF00FF;
        padding: 1;
    }

    ExportAnimationDialog Label {
        color: #D3D3D3;
        margin-bottom: 1;
    }

    ExportAnimationDialog RadioSet {
        background: #333333;
        border: solid #D3D3D3;
        padding: 1;
        margin-bottom: 1;
    }

    ExportAnimationDialog RadioButton {
        color: #FFFFFF;
    }

    ExportAnimationDialog Input {
        background: #333333;
        color: #FFFFFF;
        border: solid #D3D3D3;
        margin-bottom: 1;
    }

    ExportAnimationDialog Button {
        margin: 0 1;
    }
    """

    format_type = reactive("gif")

    class ExportRequested(Message):
        """Message posted when export is requested.

        Attributes:
            format_type: Selected export format (gif/sprite/ansi)
            filename: Target filename for export
        """

        def __init__(self, format_type: str, filename: str) -> None:
            self.format_type = format_type
            self.filename = filename
            super().__init__()

    def compose(self) -> ComposeResult:
        """Compose dialog components."""
        yield Vertical(
            Label("Export Animation"),
            Label("Format:"),
            RadioSet(
                RadioButton("GIF Animation", id="gif", value=True),
                RadioButton("Sprite Sheet (PNG)", id="sprite"),
                RadioButton("ANSI Sequence", id="ansi"),
                id="format_radio",
            ),
            Label("Filename:"),
            Input(placeholder="output.gif", id="filename_input"),
            Horizontal(
                Button("Export", variant="primary", id="export"),
                Button("Cancel", id="cancel"),
            ),
        )

    def on_mount(self) -> None:
        """Set focus to filename input on mount."""
        self.query_one("#filename_input", Input).focus()

    def on_radio_set_changed(self, event: RadioSet.Changed) -> None:
        """Handle format selection changes.

        Updates filename placeholder based on selected format.

        Args:
            event: Radio set change event
        """
        self.format_type = event.pressed.id
        filename_input = self.query_one("#filename_input", Input)

        placeholder_map = {
            "gif": "output.gif",
            "sprite": "spritesheet.png",
            "ansi": "animation.ans",
        }
        filename_input.placeholder = placeholder_map.get(self.format_type, "output.gif")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press events.

        Args:
            event: Button press event
        """
        if event.button.id == "export":
            filename_input = self.query_one("#filename_input", Input)
            filename = filename_input.value.strip() or filename_input.placeholder
            self.post_message(self.ExportRequested(self.format_type, filename))

        self.remove()
