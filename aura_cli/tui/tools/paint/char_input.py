"""Character Input Widget - Aura CLI Paint Tool.

Specialized input widget for single character entry with color display
and character selector integration.

Features:
    - Single character input validation
    - Foreground/background color display
    - Double-click to open character selector
    - Right-click or Ctrl+click to swap colors
    - Custom rendering with color filtering
"""

from typing import TYPE_CHECKING, List

from rich.segment import Segment
from rich.style import Style
from textual import events
from textual.color import Color
from textual.filter import LineFilter
from textual.message import Message
from textual.strip import Strip
from textual.widgets import Input

DOUBLE_CLICK_TIME = 0.8


class CharInput(Input, inherit_bindings=False):
    """Single character input widget with color display.

    Displays current character with selected foreground/background colors.
    Integrates with character selector and color swapping.
    """

    class CharSelected(Message):
        """Message posted when character changes.

        Attributes:
            char: Selected character
        """

        def __init__(self, char: str) -> None:
            self.char = char
            super().__init__()

    class Recolor(LineFilter):
        """Line filter for applying foreground/background colors.

        Attributes:
            style: Rich style with colors
        """

        def __init__(self, fg_color: Color, bg_color: Color) -> None:
            self.style = Style(color=fg_color.rich_color, bgcolor=bg_color.rich_color)
            super().__init__()

        def apply(self, segments: List[Segment], background: Color) -> List[Segment]:
            """Apply color style to segments.

            Args:
                segments: Segments to transform
                background: Background color

            Returns:
                Transformed segments
            """
            return list(Segment.apply_style(segments, post_style=self.style))

    def validate_value(self, value: str) -> str:
        """Limit value to single character.

        Args:
            value: Input value

        Returns:
            Last character or space
        """
        return value[-1] if value else " "

    def on_input_changed(self, event: Input.Changed) -> None:
        """Handle value changes.

        Args:
            event: Input changed event
        """
        with self.prevent(Input.Changed):
            self.post_message(self.CharSelected(event.value))

    def on_paste(self, event: events.Paste) -> None:
        """Handle paste events and file drops.

        Args:
            event: Paste event
        """
        if TYPE_CHECKING:
            from .paint import PaintApp

            assert isinstance(self.app, PaintApp)
        self.app.on_paste(event)

    def validate_cursor_position(self, cursor_position: int) -> int:
        """Force cursor over character.

        Args:
            cursor_position: Requested position

        Returns:
            Always 0
        """
        return 0

    def insert_text_at_cursor(self, text: str) -> None:
        """Insert text limited to single character.

        Args:
            text: Text to insert
        """
        self.value = text[-1] if text else " "

    def render_line(self, y: int) -> Strip:
        """Render line with color filtering.

        Args:
            y: Line index

        Returns:
            Rendered strip with colors applied
        """
        if TYPE_CHECKING:
            from .paint import PaintApp

            assert isinstance(self.app, PaintApp)

        original_strip = super().render_line(y)
        fg_color = Color.parse(self.app.selected_fg_color)
        bg_color = Color.parse(self.app.selected_bg_color)
        return original_strip.apply_filter(
            self.Recolor(fg_color, bg_color), background=bg_color
        )

    last_click_time = 0

    def on_mouse_down(self, event: events.MouseDown) -> None:
        """Handle mouse clicks.

        Right-click or Ctrl+click swaps colors.
        Double-click opens character selector.

        Args:
            event: Mouse down event
        """
        if TYPE_CHECKING:
            from .paint import PaintApp

            assert isinstance(self.app, PaintApp)

        if event.ctrl or event.button == 3:
            self.app.action_swap_colors()
            return

        if event.time - self.last_click_time < DOUBLE_CLICK_TIME:
            self.app.action_open_character_selector()

        self.last_click_time = event.time
