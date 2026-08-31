"""Colors Box Widget - Aura CLI Paint Tool.

Color palette widget for selecting foreground and background colors
with double-click to edit functionality.

Features:
    - Dynamic color palette display
    - Primary/secondary color selection
    - Double-click to edit colors
    - Current color and character display
    - Mouse button and Ctrl key support
"""

from typing import Dict, Tuple

from textual import events
from textual.app import ComposeResult
from textual.containers import Container
from textual.message import Message
from textual.reactive import var
from textual.widgets import Button

from .char_input import DOUBLE_CLICK_TIME, CharInput


class ColorsBox(Container):
    """Color palette widget for color selection.

    Displays a grid of color buttons with current color indicator.
    Supports primary (left-click) and secondary (right-click/Ctrl) selection.

    Attributes:
        palette: Tuple of color strings to display
    """

    palette: var[Tuple[str, ...]] = var(())
    """Color palette as tuple (immutable for reactivity)."""

    class ColorSelected(Message):
        """Message posted when color is selected.

        Attributes:
            color: Selected color string
            as_foreground: True for foreground, False for background
        """

        def __init__(self, color: str, as_foreground: bool) -> None:
            self.color = color
            self.as_foreground = as_foreground
            super().__init__()

    class EditColor(Message):
        """Message posted when color is double-clicked for editing.

        Attributes:
            color_index: Index of color in palette
            as_foreground: True for foreground, False for background
        """

        def __init__(self, color_index: int, as_foreground: bool) -> None:
            self.color_index = color_index
            self.as_foreground = as_foreground
            super().__init__()

    def compose(self) -> ComposeResult:
        """Compose color palette components."""
        self.color_by_button: Dict[Button, str] = {}
        with Container(id="palette_selection_box"):
            yield CharInput(id="selected_color_char_input", classes="color_well")
        yield Container(id="available_colors")

    def watch_palette(self, palette: Tuple[str, ...]) -> None:
        """Update color buttons when palette changes.

        Args:
            palette: New color palette
        """
        container = self.query_one("#available_colors")
        buttons = self.query(".color_button").nodes

        for extra_button in buttons[len(palette) :]:
            extra_button.remove()
            del self.color_by_button[extra_button]  # type: ignore

        for _new_color in palette[len(buttons) :]:
            button = Button("", classes="color_button color_well")
            button.can_focus = False
            container.mount(button)
            buttons.append(button)

        for button, color in zip(
            buttons, palette, strict=False
        ):  # Palette may be shorter
            button.styles.background = color
            self.color_by_button[button] = color  # type: ignore

    last_click_time = 0
    last_click_button: Button | None = None

    def on_mouse_down(self, event: events.MouseDown) -> None:
        """Handle mouse button press on color buttons.

        Left-click or Ctrl+click selects color.
        Double-click opens color editor.

        Args:
            event: Mouse down event
        """
        button, _ = self.app.get_widget_at(*event.screen_offset)
        if "color_button" in button.classes:
            assert isinstance(button, Button)
            secondary = event.ctrl or event.button == 3
            self.post_message(
                self.ColorSelected(self.color_by_button[button], secondary)
            )

            if (
                event.time - self.last_click_time < DOUBLE_CLICK_TIME
                and button == self.last_click_button
            ):
                self.post_message(
                    self.EditColor(
                        self.query(".color_button").nodes.index(button), secondary
                    )
                )

            self.last_click_time = event.time
            self.last_click_button = button
