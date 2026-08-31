"""ASCII Scrollbar Renderer - Aura CLI Paint Tool.

Alternative scrollbar rendering using only ASCII space characters
for --ascii-only mode compatibility.

Features:
    - ASCII-only rendering (no Unicode)
    - Vertical and horizontal scrollbars
    - Mouse interaction support
    - Configurable colors and thickness
"""

from math import ceil, floor

from rich.color import Color
from rich.segment import Segment, Segments
from rich.style import Style
from textual.scrollbar import ScrollBarRender


class ASCIIScrollBarRender(ScrollBarRender):
    """Scrollbar renderer using only ASCII space characters.

    Provides scrollbar visualization compatible with ASCII-only terminals.
    Uses background colors to create visual distinction.
    """

    @classmethod
    def render_bar(
        cls,
        size: int = 25,
        virtual_size: float = 50,
        window_size: float = 20,
        position: float = 0,
        thickness: int = 1,
        vertical: bool = True,
        back_color: Color | None = None,
        bar_color: Color | None = None,
    ) -> Segments:
        """Render scrollbar with ASCII characters.

        Args:
            size: Visible size of scrollbar
            virtual_size: Total scrollable size
            window_size: Size of visible window
            position: Current scroll position
            thickness: Scrollbar thickness in characters
            vertical: True for vertical, False for horizontal
            back_color: Background track color (defaults to #555555)
            bar_color: Scrollbar thumb color (defaults to bright_magenta)

        Returns:
            Segments for rendering
        """
        if back_color is None:
            back_color = Color.parse("#555555")
        if bar_color is None:
            bar_color = Color.parse("bright_magenta")
        back = back_color
        bar = bar_color

        width_thickness = thickness if vertical else 1

        _Segment = Segment
        _Style = Style
        blank = " " * width_thickness

        foreground_meta = {"@mouse.up": "release", "@mouse.down": "grab"}

        if window_size and size and virtual_size and size != virtual_size:
            bar_ratio = virtual_size / size
            thumb_size = floor(max(1, window_size / bar_ratio))

            position_ratio = position / (virtual_size - window_size)
            position = (size - thumb_size) * position_ratio

            start_index = max(0, int(position))
            end_index = max(0, start_index + ceil(thumb_size))

            upper = {"@mouse.up": "scroll_up"}
            lower = {"@mouse.up": "scroll_down"}

            upper_back_segment = Segment(blank, _Style(bgcolor=back, meta=upper))
            lower_back_segment = Segment(blank, _Style(bgcolor=back, meta=lower))

            segments = [upper_back_segment] * int(size)
            segments[end_index:] = [lower_back_segment] * (size - end_index)

            segments[start_index:end_index] = [
                _Segment(blank, _Style(bgcolor=bar, meta=foreground_meta))
            ] * (end_index - start_index)

        else:
            style = _Style(bgcolor=back)
            segments = [_Segment(blank, style=style)] * int(size)

        if vertical:
            return Segments(segments, new_lines=True)
        else:
            return Segments(([*segments, _Segment.line()]) * thickness, new_lines=False)
