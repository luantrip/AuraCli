"""Canvas Widget - Aura CLI Paint Tool.

Interactive drawing surface for ANSI art with mouse event handling,
magnification, grid display, and layer composition rendering.

Features:
    - Real-time rendering of AnsiArtDocument
    - Mouse event capture and tool integration
    - Magnification support (1x-16x)
    - Optional grid overlay
    - Selection visualization
    - Multi-layer composition rendering
    - Tool preview and cursor display
"""

from typing import TYPE_CHECKING, Any, List, Optional, cast

from rich.color import Color
from rich.segment import Segment
from rich.style import Style
from textual import events
from textual.geometry import Offset, Region, Size
from textual.message import Message
from textual.reactive import reactive
from textual.strip import Strip
from textual.widget import Widget

from aura_cli.application.paint.ansi_art_document import AnsiArtDocument, Selection

from .args import args
from .meta_glyph_font import largest_font_that_fits

if TYPE_CHECKING:
    from aura_cli.application.paint.layers import LayerStack


def scale_region(region: Region, scale: int) -> Region:
    """Scale region by given factor.

    Args:
        region: Region to scale
        scale: Scale factor

    Returns:
        Scaled region
    """
    return Region(
        region.x * scale, region.y * scale, region.width * scale, region.height * scale
    )


class Canvas(Widget):
    """Interactive drawing surface widget for ANSI art.

    Handles mouse events, renders document with layers, and provides
    visual feedback for tools and selections.

    Attributes:
        magnification: Zoom level (1-16x)
        show_grid: Whether to display grid overlay
        cursor_visible: Whether to show cursor
    """

    magnification = reactive(1, layout=True)
    show_grid = reactive(False)
    cursor_visible = reactive(True)
    _cursor_blink_timer: Any = None

    def watch_cursor_visible(self, cursor_visible: bool) -> None:
        """Called when cursor_visible changes. Manages cursor blinking timer."""
        if cursor_visible and self._cursor_blink_timer is None:
            # Start blinking timer
            self._cursor_blink_timer = self.set_interval(0.5, self._toggle_cursor_blink)
        elif not cursor_visible and self._cursor_blink_timer is not None:
            # Stop blinking timer
            if hasattr(self._cursor_blink_timer, "stop"):
                self._cursor_blink_timer.stop()
            self._cursor_blink_timer = None

    def _toggle_cursor_blink(self) -> None:
        """Toggle cursor visibility for blinking effect."""
        self.cursor_visible = not self.cursor_visible

    class ToolStart(Message):
        """Message posted when tool drawing starts.

        Attributes:
            x: Mouse X coordinate
            y: Mouse Y coordinate
            button: Mouse button pressed
            ctrl: Whether Ctrl key is held
        """

        def __init__(self, mouse_down_event: events.MouseDown) -> None:
            self.x = mouse_down_event.x
            self.y = mouse_down_event.y
            self.button = mouse_down_event.button
            self.ctrl = mouse_down_event.ctrl
            super().__init__()

    class ToolUpdate(Message):
        """Message posted when dragging tool on canvas.

        Attributes:
            x: Mouse X coordinate
            y: Mouse Y coordinate
        """

        def __init__(self, mouse_move_event: events.MouseMove) -> None:
            self.x = mouse_move_event.x
            self.y = mouse_move_event.y
            super().__init__()

    class ToolStop(Message):
        """Message posted when tool drawing stops.

        Attributes:
            x: Mouse X coordinate
            y: Mouse Y coordinate
        """

        def __init__(self, mouse_up_event: events.MouseUp) -> None:
            self.x = mouse_up_event.x
            self.y = mouse_up_event.y
            super().__init__()

    class ToolPreviewUpdate(Message):
        """Message posted when mouse moves without button pressed.

        Attributes:
            x: Mouse X coordinate
            y: Mouse Y coordinate
        """

        def __init__(self, mouse_move_event: events.MouseMove) -> None:
            self.x = mouse_move_event.x
            self.y = mouse_move_event.y
            super().__init__()

    class ToolPreviewStop(Message):
        """Message posted when mouse leaves canvas during preview."""

        def __init__(self) -> None:
            super().__init__()

    def __init__(self, **kwargs: Any) -> None:
        """Initialize canvas widget.

        Args:
            **kwargs: Widget initialization arguments
        """
        super().__init__(**kwargs)
        self.image: AnsiArtDocument | None = None
        self.pointer_active: bool = False
        self.magnifier_preview_region: Optional[Region] = None
        self.select_preview_region: Optional[Region] = None
        self.which_button: Optional[int] = None
        self.layer_stack: Optional[LayerStack] = None
        self._composed_image: Optional[AnsiArtDocument] = None

    def on_mouse_down(self, event: events.MouseDown) -> None:
        """Handle mouse button press.

        Starts tool drawing or cancels action if both buttons pressed.

        Args:
            event: Mouse down event
        """
        if self.app.has_class("view_bitmap"):
            # Exiting is handled by the PaintApp.
            return

        self.fix_mouse_event(event)  # not needed, pointer isn't captured yet.
        event.x //= self.magnification
        event.y //= self.magnification

        if self.pointer_active and self.which_button != event.button:
            if TYPE_CHECKING:
                from .paint import Paint
            cast("Paint", self.app).stop_action_in_progress()
            return

        self.post_message(self.ToolStart(event))
        self.pointer_active = True
        self.which_button = event.button
        self.capture_mouse(True)

    def fix_mouse_event(self, event: events.MouseEvent) -> None:
        """Fix mouse coordinates relative to widget.

        Calculates widget-relative coordinates from screen coordinates
        to work around inconsistencies during mouse capture.

        Args:
            event: Mouse event to fix
        """
        offset = event.screen_offset - self.region.offset
        event.x = offset.x
        event.y = offset.y

    def on_mouse_move(self, event: events.MouseMove) -> None:
        """Handle mouse movement.

        Updates tool action if drawing, or tool preview if hovering.

        Args:
            event: Mouse move event
        """
        self.fix_mouse_event(event)
        event.x //= self.magnification
        event.y //= self.magnification

        if self.pointer_active:
            self.post_message(self.ToolUpdate(event))
        else:
            # I put this in the else block just for performance.
            # Hopefully it wouldn't matter much, but
            # the pointer should never be active in View Bitmap mode.
            if self.app.has_class("view_bitmap"):
                return
            self.post_message(self.ToolPreviewUpdate(event))

    def on_mouse_up(self, event: events.MouseUp) -> None:
        """Handle mouse button release.

        Stops current tool action and releases mouse capture.

        Args:
            event: Mouse up event
        """
        self.fix_mouse_event(event)
        event.x //= self.magnification
        event.y //= self.magnification

        if self.pointer_active:
            self.post_message(self.ToolStop(event))
        self.pointer_active = False
        self.capture_mouse(False)

    def on_leave(self, event: events.Leave) -> None:
        """Handle mouse leaving canvas.

        Stops tool preview if not actively drawing.

        Args:
            event: Leave event
        """
        if not self.pointer_active:
            self.post_message(self.ToolPreviewStop())

    def get_content_width(self, container: Size, _viewport: Size) -> int:
        """Calculate intrinsic width of widget.

        Args:
            container: Container size
            _viewport: Viewport size

        Returns:
            Width in characters multiplied by magnification
        """
        if self.image is None:
            return 0
        return self.image.width * self.magnification

    def get_content_height(self, container: Size, _viewport: Size, width: int) -> int:
        """Calculate intrinsic height of widget.

        Args:
            container: Container size
            _viewport: Viewport size
            width: Available width

        Returns:
            Height in characters multiplied by magnification
        """
        if self.image is None:
            return 0
        return self.image.height * self.magnification

    def _get_render_image(self) -> AnsiArtDocument:
        """Get image to render with layer composition.

        Returns composed image from layer stack if available,
        otherwise returns base image.

        Returns:
            Document to render
        """
        if not self.layer_stack or not self.image:
            return self.image if self.image else AnsiArtDocument(1, 1)

        active_layer = self.layer_stack.active_layer
        if active_layer and active_layer.visible:
            return self.image

        return self.image

    @staticmethod
    def _within_text_selection(
        textbox: "Selection", cell_x: int, cell_y: int, cursor_visible: bool
    ) -> bool:
        """Return True if cell is within the text selection highlight range."""
        if cell_x >= textbox.region.right or cell_x < textbox.region.x:
            return False

        def to_idx(offset: "Offset") -> int:
            return offset.y * textbox.region.width + offset.x

        start = to_idx(textbox.text_selection_start)
        end = to_idx(textbox.text_selection_end)
        lo, hi = min(start, end), max(start, end)
        cell_idx = to_idx(Offset(cell_x, cell_y) - textbox.region.offset)
        if lo == hi and not cursor_visible:
            return False
        return lo <= cell_idx <= hi

    def _should_invert_cell(
        self,
        x: int,
        y: int,
        sel: "Optional[Selection]",
        magnifier_preview_region: "Optional[Region]",
        inner_magnifier_preview_region: "Optional[Region]",
        select_preview_region: "Optional[Region]",
        inner_select_preview_region: "Optional[Region]",
        selection_region: "Optional[Region]",
        inner_selection_region: "Optional[Region]",
    ) -> bool:
        """Return True if this cell should have its colors inverted."""
        return (
            (
                self.magnifier_preview_region
                and magnifier_preview_region is not None
                and magnifier_preview_region.contains(x, y)
                and inner_magnifier_preview_region is not None
                and (not inner_magnifier_preview_region.contains(x, y))
            )
            or (
                self.select_preview_region
                and select_preview_region is not None
                and select_preview_region.contains(x, y)
                and inner_select_preview_region is not None
                and (not inner_select_preview_region.contains(x, y))
            )
            or (
                sel
                and (not sel.textbox_mode)
                and (self.app.selection_drag_offset is None)
                and selection_region is not None
                and selection_region.contains(x, y)
                and inner_selection_region is not None
                and (not inner_selection_region.contains(x, y))
            )
            or (
                sel
                and sel.textbox_mode
                and self._within_text_selection(sel, x, y, self.cursor_visible)
            )
        )

    def _apply_magnification_char(
        self,
        ch: str,
        x: int,
        y: int,
        magnification: int,
        show_grid: bool,
        style: "Style",
    ) -> "tuple[str, Style]":
        """Apply magnification rendering: big_ch and grid overlay. Returns (ch, style)."""
        if magnification > 1:
            ch = self.big_ch(ch, x % magnification, y % magnification, magnification)
            if (show_grid and x % magnification == 0) or y % magnification == 0:
                # Not overriding `bgcolor` here, because:
                # Its actually useful to see the background color of the cell,
                # as it lets you distinguish between a space " " and a full block "█".
                # Plus this lets the grid be more subtle, visually taking up less than a cell.
                # That said, in --ascii-only mode, the background color is visible past the border
                # of the cell, as the border is centered in a cell, not flush with the left/top edge,
                # having less characters to work with, so it's a closer call, and might make sense
                # to use space characters instead, making for a thicker but more coherent grid.
                fg = "#c0c0c0" if (x + y) % 2 == 0 else "#808080"
                if x % magnification == 0 and y % magnification == 0:
                    ch = "+" if args.ascii_only else "▛"  # "┼" # (🭽 may render as wide)
                elif x % magnification == 0:
                    ch = "|" if args.ascii_only else "▌"  # "┆" # (▏, not 🭰)
                elif y % magnification == 0:
                    ch = "-" if args.ascii_only else "▀"  # "┄" # (▔, not 🭶)
                style += Style.from_color(color=Color.parse(fg))
        return ch, style

    def render_line(self, y: int) -> Strip:
        """Render single line of canvas.

        Handles magnification, grid display, selection visualisation,
        and layer composition.

        Args:
            y: Line index relative to widget top

        Returns:
            Strip containing rendered segments
        """
        render_image = self._get_render_image()
        assert render_image is not None
        # self.size.width/height already is multiplied by self.magnification.
        if y >= self.size.height:
            return Strip.blank(self.size.width)
        segments: List[Segment] = []
        sel = render_image.selection
        magnification = (
            self.magnification
        )  # reactive.__get__ is a performance bottleneck

        # Avoiding "possibly unbound" errors.
        magnifier_preview_region = None
        inner_magnifier_preview_region = None
        select_preview_region = None
        inner_select_preview_region = None
        selection_region = None
        inner_selection_region = None

        if self.magnifier_preview_region:
            magnifier_preview_region = scale_region(
                self.magnifier_preview_region, magnification
            )
            inner_magnifier_preview_region = magnifier_preview_region.shrink(
                (1, 1, 1, 1)
            )
        if self.select_preview_region:
            select_preview_region = scale_region(
                self.select_preview_region, magnification
            )
            inner_select_preview_region = select_preview_region.shrink((1, 1, 1, 1))
        if sel:
            selection_region = scale_region(sel.region, magnification)
            inner_selection_region = selection_region.shrink((1, 1, 1, 1))
        show_grid = (
            magnification >= 4 and self.show_grid
        )  # avoiding reactive.__get__ in loop, not as much of a bottleneck though
        for x in range(self.size.width):
            cell_x = x // magnification
            cell_y = y // magnification
            try:
                if (
                    sel
                    and sel.contained_image
                    and sel.region.contains(cell_x, cell_y)
                    and (
                        sel.mask is None
                        or sel.mask[cell_y - sel.region.y][cell_x - sel.region.x]
                    )
                ):
                    ch = sel.contained_image.ch[cell_y - sel.region.y][
                        cell_x - sel.region.x
                    ]
                    style = sel.contained_image.st[cell_y - sel.region.y][
                        cell_x - sel.region.x
                    ]
                else:
                    ch = render_image.ch[cell_y][cell_x]
                    style = render_image.st[cell_y][cell_x]
            except IndexError:
                # This should be easier to debug visually.
                ch = "?"
                style = Style.from_color(
                    color=Color.parse("#cccccc"), bgcolor=Color.parse("#555555")
                )
            ch, style = self._apply_magnification_char(
                ch, x, y, magnification, show_grid, style
            )
            assert style.color is not None
            assert style.bgcolor is not None

            if TYPE_CHECKING:
                from .paint import Paint

                assert isinstance(self.app, Paint)
            if self._should_invert_cell(
                x,
                y,
                sel,
                magnifier_preview_region,
                inner_magnifier_preview_region,
                select_preview_region,
                inner_select_preview_region,
                selection_region,
                inner_selection_region,
            ):
                # invert the colors
                if TYPE_CHECKING:
                    assert style.color.triplet is not None
                    assert style.bgcolor.triplet is not None
                style = Style.from_color(
                    color=Color.from_rgb(
                        255 - style.color.triplet.red,
                        255 - style.color.triplet.green,
                        255 - style.color.triplet.blue,
                    ),
                    bgcolor=Color.from_rgb(
                        255 - style.bgcolor.triplet.red,
                        255 - style.bgcolor.triplet.green,
                        255 - style.bgcolor.triplet.blue,
                    ),
                )
            segments.append(Segment(ch, style))
        return Strip(segments, self.size.width)

    def refresh_scaled_region(self, region: Region) -> None:
        """Refresh a region of the widget, scaled by the magnification."""
        if self.magnification == 1:
            self.refresh(region)
            return
        # Scale the region by magnification. A 1-cell padding was previously
        # added here as a workaround for a rendering artifact that has since been fixed.
        self.refresh(
            Region(
                region.x * self.magnification,
                region.y * self.magnification,
                region.width * self.magnification,
                region.height * self.magnification,
            )
        )

    def watch_magnification(self) -> None:
        """Called when magnification changes."""
        self.active_meta_glyph_font = largest_font_that_fits(
            self.magnification, self.magnification
        )

    @staticmethod
    def _big_ch_gradient(ch: str, x: int, y: int, magnification: int) -> str:
        """Handle fractional block characters for magnification."""
        _GRADIENTS = [
            ("█▇▆▅▄▃▂▁", "y", False),  # top-to-bottom fill
            (" ▏▎▍▌▋▊▉█", "x", False),  # left-to-right fill
            (" ▔🮂🮃▀🮄🮅🮆█", "y", True),  # top fill
            ("█🮋🮊🮉▐🮈🮇▕ ", "x", True),  # right fill
        ]
        for gradient, axis, invert in _GRADIENTS:
            if ch not in gradient:
                continue
            index = gradient.index(ch)
            if axis == "y":
                threshold = int(index / 8 * magnification)
                pos = y
            else:
                threshold = int(index / 8 * magnification)
                pos = x
            if pos == threshold:
                return gradient[index * magnification % 8]
            if invert:
                return "█" if pos < threshold else " "
            else:
                return "█" if pos > threshold else " "
        return ""

    def _big_ch_diagonal(self, ch: str, x: int, y: int, magnification: int) -> str:
        """Handle corner triangles and diagonal characters for magnification."""
        d1 = x - y
        d2 = x + y + 1 - magnification
        _DIAG = {
            "◣": ("█" if d1 < 0 else " " if d1 > 0 else "◣"),
            "◥": ("█" if d1 > 0 else " " if d1 < 0 else "◥"),
            "◢": ("█" if d2 > 0 else " " if d2 < 0 else "◢"),
            "◤": ("█" if d2 < 0 else " " if d2 > 0 else "◤"),
            "╱": ("╱" if d2 == 0 else " "),
            "╲": ("╲" if d1 == 0 else " "),
            "/": ("/" if d2 == 0 else " "),
            "\\": ("\\" if d1 == 0 else " "),
        }
        if ch in _DIAG:
            return _DIAG[ch]
        if ch == "╳":
            return "╲" if d1 == 0 else "╱" if d2 == 0 else " "
        return ""

    def big_ch(self, ch: str, x: int, y: int, magnification: int) -> str:
        """Return a character part of a meta-glyph."""
        if self.active_meta_glyph_font and ch in self.active_meta_glyph_font.glyphs:
            glyph_lines = self.active_meta_glyph_font.glyphs[ch]
            x -= (magnification - self.active_meta_glyph_font.width) // 2
            y -= (magnification - self.active_meta_glyph_font.height) // 2
            if y >= len(glyph_lines) or y < 0:
                return " "
            glyph_line = glyph_lines[y]
            if x >= len(glyph_line) or x < 0:
                return " "
            return glyph_line[x]
        match ch:
            case " ":
                return " "
            case "░":
                return "░"
            case "▒":
                return "▒"
            case "▓":
                return "▓"
            case "█":
                return "█"
            # These are now obsolete special cases of below fractional block character handling.
            # case "▄":
            #     return "█" if y >= magnification // 2 else " "
            # case "▀":
            #     return "█" if y < magnification // 2 else " "
            # case "▌":
            #     return "█" if x < magnification // 2 else " "
            # case "▐":
            #     return "█" if x >= magnification // 2 else " "
            # Corner triangles
            case ch if ch in "◣◥◢◤╱╲╳/\\":
                result = self._big_ch_diagonal(ch, x, y, magnification)
                if result:
                    return result
            case _:
                pass
        # Fall back to showing the character in a single cell, approximately centered.
        if x == magnification // 2 and y == magnification // 2:
            return ch
        else:
            return " "
