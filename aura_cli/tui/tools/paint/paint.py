#!/usr/bin/env python3

"""AuraPaint - native AuraCli terminal art editor.

Full-featured MS Paint clone for the terminal with ANSI art support.

Features:
    - 16 drawing tools (Pencil, Brush, Line, Rectangle, Ellipse, etc.)
    - Multi-layer system with blend modes and opacity
    - Animation support with timeline and onion skinning
    - Color picker with palette management
    - Text tool with character selection
    - Undo/redo with efficient region updates
    - Multiple file formats (ANSI, PNG, SVG, HTML, etc.)
    - AI assistant integration for natural language drawing
    - Wallpaper export for desktop backgrounds
    - Localization support (26 languages)
    - Keyboard shortcuts and menu system
"""

import asyncio
import io
import logging
import os
import re
import shlex
import sys
from typing import Any, Callable, ClassVar, Iterator, List, Optional, Set, Tuple
from uuid import uuid4

from PIL import Image, UnidentifiedImageError
from rich.style import Style
from rich.text import Text
from textual import events, on, work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.color import Color
from textual.containers import Container, Horizontal, Vertical
from textual.css._style_properties import BorderDefinition
from textual.dom import DOMNode
from textual.geometry import Offset, Region, Size
from textual.reactive import var
from textual.widget import Widget
from textual.widgets import Button, Input, RadioButton, RadioSet, Static
from textual.widgets._header import HeaderIcon
from textual.worker import get_current_worker  # type: ignore

from aura_cli.application.paint.action import Action
from aura_cli.application.paint.ansi_art_document import (
    AnsiArtDocument,
    FormatWriteNotSupported,
    Selection,
)
from aura_cli.application.paint.brush import (
    BrushKind,
    BrushSettings,
    stamp_cell,
)
from aura_cli.application.paint.brush import (
    stamp_brush as apply_brush,
)
from aura_cli.application.paint.document_service import sample_document_cell
from aura_cli.application.paint.drawing import DrawShape, apply_points, shape_points
from aura_cli.application.paint.graphics_primitives import (
    bezier_curve_walk,
    bresenham_walk,
    flood_fill,
    is_inside_polygon,
    polygon_walk,
    polyline_walk,
    quadratic_curve_walk,
)
from aura_cli.application.paint.history import PaintHistory
from aura_cli.application.paint.layers import LayerStack
from aura_cli.application.paint.localization.i18n import get as _
from aura_cli.application.paint.localization.i18n import load_language
from aura_cli.application.paint.paint_agent import PaintAgent
from aura_cli.application.paint.palette_data import (
    DEFAULT_PALETTE,
)
from aura_cli.application.paint.text_selection import (
    selected_text,
    selected_text_range,
)
from aura_cli.application.paint.transformations import (
    flip_horizontal,
    flip_vertical,
    rotate,
    stretch_skew,
)

TEXT_CURSOR_KEYS = frozenset(
    {"left", "right", "up", "down", "home", "end", "pageup", "pagedown", "insert"}
)
from aura_cli.application.paint.viewport import (
    document_corner,
    magnifier_transition,
    next_magnification,
)

from .__init__ import __version__
from .args import args, get_help_text
from .ascii_mode import set_ascii_only_mode
from .auto_restart import restart_on_changes, restart_program
from .canvas import Canvas
from .char_input import CharInput
from .character_picker import CharacterSelectorDialogWindow
from .chat_window import ChatWindow  # NEW: Import ChatWindow
from .colors_box import ColorsBox
from .edit_colors import EditColorsDialogWindow
from .file_dialogs import OpenDialogWindow, SaveAsDialogWindow
from .icons import (
    get_help_icon_markup,
    get_paint_icon,
    get_question_icon,
    get_warning_icon,
    get_windows_icon_markup,
    header_icon_text,
)
from .layer_panel import LayerManagementPanel  # NEW: Import LayerManagementPanel
from .menus import Menu, MenuBar
from .rasterize_ansi_art import rasterize
from .tool import Tool
from .toolbox import ToolsBox
from .wallpaper import get_config_dir, set_wallpaper
from .windows import DialogWindow, MessageBox, Window

MAX_FILE_SIZE = 500000  # 500 KB
logger = logging.getLogger(__name__)

load_language(args.language)


class AuraPaint(App[None]):
    """Native MS Paint-like image editor for terminal workflows."""

    CSS_PATH = "paint.css"

    AUTO_FOCUS = None

    BINDINGS: ClassVar[list] = [
        Binding("ctrl+alt+c", "toggle_chat_popup", _("Toggle Chat")),
        Binding("ctrl+q", "exit", _("Quit")),
        Binding("ctrl+s", "save", _("Save")),
        Binding("ctrl+shift+s", "save_as", _("Save As")),
        Binding("ctrl+p", "print", _("Print")),
        Binding("ctrl+o", "open", _("Open")),
        Binding("ctrl+n", "new", _("New")),
        Binding("ctrl+shift+n", "clear_image", _("Clear Image")),
        Binding("ctrl+t", "toggle_tools_box", _("Toggle Tools Box")),
        Binding("ctrl+l", "toggle_colors_box", _("Toggle Colors Box")),
        Binding("ctrl+z", "undo", _("Undo")),
        Binding("ctrl+shift+z,shift+ctrl+z,ctrl+y,f4", "redo", _("Repeat")),
        Binding("ctrl+x", "cut", _("Cut")),
        Binding("ctrl+c", "copy(True)", _("Copy")),
        Binding("ctrl+v", "paste", _("Paste")),
        Binding("ctrl+g", "toggle_grid", _("Show Grid")),
        Binding("ctrl+f", "view_bitmap", _("View Bitmap")),
        Binding("ctrl+r", "flip_rotate", _("Flip/Rotate")),
        Binding("ctrl+w", "stretch_skew", _("Stretch/Skew")),
        Binding(
            "ctrl+i,tab",
            "invert_colors_unless_should_switch_focus",
            _("Invert Colors"),
            priority=True,
        ),
        Binding("ctrl+e", "attributes", _("Attributes")),
        Binding("delete", "clear_selection(True)", _("Clear Selection")),
        Binding("ctrl+a", "select_all", _("Select All")),
        Binding("ctrl+pageup", "normal_size", _("Normal Size")),
        Binding("ctrl+pagedown", "large_size", _("Large Size")),
        Binding("ctrl+d", "toggle_dark", _("Toggle Dark Mode")),
        Binding("escape", "cancel", _("Cancel")),
        Binding("f1", "help_topics", _("Help Topics")),
        Binding("f2", "reload", _("Reload")),
        Binding("f12", "toggle_inspector", _("Toggle Inspector")),
    ]

    show_tools_box = var(True)
    """Whether to show the tools box."""
    show_colors_box = var(True)
    """Whether to show the tools box."""
    show_status_bar = var(True)
    """Whether to show the status bar."""
    show_chat_popup = var(False)  # NEW: Reactive variable for chat popup visibility

    palette = var(DEFAULT_PALETTE)
    """The colors to show in the colors box. This is a tuple for immutability, since mutations would not trigger watch_palette."""
    selected_tool = var(Tool.pencil)
    """The currently selected tool."""
    return_to_tool = var(Tool.pencil)
    """Tool to switch to after using the Magnifier or Pick Color tools."""
    selected_bg_color = var(DEFAULT_PALETTE[0])
    """The currently selected background color. Unlike MS Paint, this acts as the primary color."""
    selected_fg_color = var(DEFAULT_PALETTE[len(DEFAULT_PALETTE) // 2])
    """The currently selected foreground (text) color."""
    selected_char = var(" ")
    """The character to draw with."""
    file_path = var(None)
    """The path to the file being edited."""
    selection_opaque = var(True)
    """Whether the selection should be drawn opaque (True) or transparent (False)."""
    show_thumbnail = var(False)
    """Whether to show the thumbnail preview."""

    image = var(AnsiArtDocument.from_text("Not Loaded"))
    """The document being edited. Contains the selection, if any."""
    image_initialized = False
    """Whether the image is ready. This flag exists to avoid type checking woes if I were to allow image to be None."""

    magnification = var(1)
    """Current magnification level."""
    return_to_magnification = var(4)
    """Saved zoomed-in magnification level."""
    show_grid = var(False)
    """Whether to show the grid. Only applies when zoomed in to 400% or more."""
    old_scroll_offset = var(Offset(0, 0))
    """The scroll offset before View Bitmap mode was entered."""
    cursor_visible = var(True)
    """Whether the cursor is visible. Used for blinking effect."""

    undos: List[Action]
    """Past actions that can be undone"""
    redos: List[Action]
    """Future actions that can be redone"""
    preview_action: Optional[Action] = None
    """A temporary undo state for tool previews"""
    saved_undo_count = 0
    """Used to determine if the document has been modified since the last save, in is_document_modified()"""
    backup_saved_undo_count = 0
    """Used to determine if the document has been modified since the last backup save"""
    save_backup_after_cancel_preview = False
    """Flag to postpone saving the backup until a tool preview action is reverted, so as not to save it into the backup file"""
    backup_folder: Optional[str] = None
    """The folder to save a temporary backup file to. If None, will save alongside the file being edited."""
    backup_checked_for: Optional[str] = None
    """The file path last checked for a backup save.

    This is tracked to prevent discarding Untitled.ans~ when loading a document on startup.
    Indicates that the file path either was loaded (recovered) or was not found.
    Not set when failing to load a backup, since the file maybe shouldn't be discarded in that case.
    """

    mouse_gesture_cancelled = False
    """For Undo/Redo, to interrupt the current action"""
    mouse_at_start: Offset = Offset(0, 0)
    """Mouse position at mouse down.

    Used for shape tools that draw between the mouse down and up points (Line, Rectangle, Ellipse, Rounded Rectangle),
    the Select tool (defining a box similarly to Rectangle), and also used to detect double-click, for the Polygon tool.
    """
    mouse_previous: Offset = Offset(0, 0)
    """Previous mouse position, for brush tools (Pencil, Brush, Eraser, Airbrush)"""
    selection_drag_offset: Offset | None = None
    """For Select tool, indicates that the selection is being moved, and defines the offset of the selection from the mouse"""
    selecting_text: bool = False
    """Used for Text tool"""
    tool_points: List[Offset]
    """Used for Curve, Polygon, or Free-Form Select tools"""
    polygon_last_click_time: float = 0
    """Used for Polygon tool to detect double-click"""
    color_eraser_mode: bool = False
    """Used for Eraser/Color Eraser tool, when using the right mouse button"""

    background_tasks: Set[asyncio.Task[None]]
    """Stores references to Task objects so they don't get garbage collected."""

    TITLE = _("AuraPaint")

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        set_ascii_only_mode(args.ascii_only)

        # Operational editor state belongs to one Paint host. Keeping these
        # mutable collections on the class leaked history across instances.
        self.history = PaintHistory()
        self.undos = self.history.undos
        self.redos = self.history.redos
        self.tool_points = []
        self.background_tasks = set()

        llm_client = None
        try:
            from aura_cli.core.llm.base import get_llm_client

            llm_client = get_llm_client()
        except Exception as error:
            logger.debug("Optional Paint LLM client is unavailable", exc_info=error)

        self.agent = PaintAgent(self, llm_client=llm_client)
        self.layer_stack: Optional[LayerStack] = (
            None  # NEW: Layer stack for multi-layer support
        )

    def watch_file_path(self, file_path: Optional[str]) -> None:
        """Called when file_path changes."""
        if file_path is None:
            self.sub_title = _("Untitled")
        else:
            self.sub_title = os.path.basename(file_path)

    def watch_show_tools_box(self, show_tools_box: bool) -> None:
        """Called when show_tools_box changes."""
        self.query_one("#tools_box", ToolsBox).display = show_tools_box

    def watch_show_colors_box(self, show_colors_box: bool) -> None:
        """Called when show_colors_box changes."""
        self.query_one("#colors_box", ColorsBox).display = show_colors_box

    def watch_show_status_bar(self, show_status_bar: bool) -> None:
        """Called when show_status_bar changes."""
        self.query_one("#status_bar").display = show_status_bar

    def action_toggle_chat_popup(self) -> None:
        """Toggle the chat popup visibility."""
        self.show_chat_popup = not self.show_chat_popup

    def watch_show_chat_popup(self, show_chat_popup: bool) -> None:
        """Called when show_chat_popup changes."""
        if show_chat_popup:
            self.mount(self.chat_window)
            self.chat_window.focus()
        else:
            self.chat_window.remove()

    def watch_selected_tool(self, selected_tool: Tool) -> None:
        """Called when selected_tool changes."""
        self.query_one("ToolsBox", ToolsBox).show_selected_tool(selected_tool)

    def watch_palette(self, palette: Tuple[str, ...]) -> None:
        """Called when palette changes."""
        self.query_one("ColorsBox", ColorsBox).palette = palette

    def watch_selected_bg_color(self, selected_bg_color: str) -> None:
        """Called when selected_bg_color changes."""
        self.query_one(
            "#selected_color_char_input", CharInput
        ).styles.background = selected_bg_color

        self.update_textbox_style(Style(bgcolor=selected_bg_color))
        self.draw_tool_preview_on_canvas()

    def watch_selected_fg_color(self, selected_fg_color: str) -> None:
        """Called when selected_fg_color changes."""
        # self.query_one("#selected_color_char_input", CharInput).styles.color = selected_fg_color
        # CharInput now handles this itself, because styles.color never worked to color the Input's text.
        # Well, it still needs to be updated.
        self.query_one("#selected_color_char_input", CharInput).refresh()

        self.update_textbox_style(Style(color=selected_fg_color))
        self.draw_tool_preview_on_canvas()

    def watch_selected_char(self, selected_char: str) -> None:
        """Called when selected_char changes."""
        self.query_one("#selected_color_char_input", CharInput).value = selected_char

    def watch_magnification(self, old_magnification: int, magnification: int) -> None:
        """Called when magnification changes."""
        self.canvas.magnification = magnification
        if old_magnification != 1:
            self.return_to_magnification = old_magnification

    def watch_show_grid(self, show_grid: bool) -> None:
        """Called when show_grid changes."""
        self.canvas.show_grid = show_grid

    def update_textbox_style(self, style: Style) -> None:
        """Apply a style to the whole textbox."""
        if (
            self.image.selection
            and self.image.selection.textbox_mode
            and not self.image.selection.cursor_mode
        ):
            assert self.image.selection.contained_image is not None, (
                "textbox_mode without contained_image"
            )
            for y in range(self.image.selection.region.height):
                for x in range(self.image.selection.region.width):
                    self.image.selection.contained_image.st[y][x] += style
            self.canvas.refresh_scaled_region(self.image.selection.region)

    def stamp_brush(
        self, x: int, y: int, affected_region_base: Optional[Region] = None
    ) -> Region:
        """Draws the current brush at the given coordinates, with special handling for different tools."""
        return apply_brush(
            self.image, x, y, self._brush_settings(), affected_region_base
        )

    def _brush_settings(self, *, erase_mode: bool = False) -> BrushSettings:
        kind = {
            Tool.brush: BrushKind.BRUSH,
            Tool.eraser: BrushKind.ERASER,
            Tool.airbrush: BrushKind.AIRBRUSH,
            Tool.free_form_select: BrushKind.FREE_SELECT,
        }.get(self.selected_tool, BrushKind.ERASER if erase_mode else BrushKind.PENCIL)
        return BrushSettings(
            kind=kind,
            character=self.selected_char,
            foreground=self.selected_fg_color,
            background=self.selected_bg_color,
            dark_mode=self.dark,
            color_eraser=self.color_eraser_mode,
        )

    def stamp_char(
        self,
        x: int,
        y: int,
        char_override: Optional[str] = None,
        erase_mode: bool = False,
    ) -> None:
        """Modifies the cell at the given coordinates, with special handling for different tools."""
        stamp_cell(
            self.image,
            x,
            y,
            self._brush_settings(erase_mode=erase_mode),
            erase_mode=erase_mode,
            character_override=char_override,
        )

    def erase_region(
        self, region: Region, mask: Optional[List[List[bool]]] = None
    ) -> None:
        """Clears the given region."""
        for x in range(region.width):
            for y in range(region.height):
                if mask is None or mask[y][x]:
                    self.stamp_char(x + region.x, y + region.y, erase_mode=True)

    def _draw_from_generator(
        self, gen: Iterator[Tuple[int, int]], deduplicate: bool = False
    ) -> Region:
        """Draw from a point generator (DRY helper for draw functions).

        Args:
            gen: Iterator of (x, y) coordinates
            deduplicate: If True, skip already processed points (for color inversion)

        Returns:
            Affected region
        """
        return apply_points(gen, self.stamp_brush, deduplicate=deduplicate)

    def _draw_point_tool(
        self, start: Offset, end: Offset, affected_region: Optional[Region] = None
    ) -> Region:
        """Draw using point-based tools (pencil, brush, eraser, airbrush).

        Args:
            start: Starting point
            end: Ending point
            affected_region: Existing affected region to union with

        Returns:
            Updated affected region
        """
        return apply_points(
            shape_points(DrawShape.LINE, start, end),
            self.stamp_brush,
            affected_region,
        )

    def _draw_line_tool(
        self, start: Offset, end: Offset, affected_region: Optional[Region] = None
    ) -> Region:
        """Draw a line using the line tool.

        Args:
            start: Starting point
            end: Ending point
            affected_region: Existing affected region to union with

        Returns:
            Updated affected region
        """
        return apply_points(
            shape_points(DrawShape.LINE, start, end),
            self.stamp_brush,
            affected_region,
        )

    def _draw_rectangle_tool(
        self, start: Offset, end: Offset, affected_region: Optional[Region] = None
    ) -> Region:
        """Draw a rectangle outline.

        Args:
            start: Starting corner
            end: Ending corner
            affected_region: Existing affected region to union with

        Returns:
            Updated affected region
        """
        return apply_points(
            shape_points(DrawShape.RECTANGLE, start, end),
            self.stamp_brush,
            affected_region,
        )

    def _draw_rounded_rectangle_tool(
        self, start: Offset, end: Offset, affected_region: Optional[Region] = None
    ) -> Region:
        """Draw a rounded rectangle outline.

        Args:
            start: Starting corner
            end: Ending corner
            affected_region: Existing affected region to union with

        Returns:
            Updated affected region
        """
        return apply_points(
            shape_points(DrawShape.ROUNDED_RECTANGLE, start, end),
            self.stamp_brush,
            affected_region,
        )

    def _draw_ellipse_tool(
        self, start: Offset, end: Offset, affected_region: Optional[Region] = None
    ) -> Region:
        """Draw an ellipse outline.

        Args:
            start: Starting corner
            end: Ending corner
            affected_region: Existing affected region to union with

        Returns:
            Updated affected region
        """
        return apply_points(
            shape_points(DrawShape.ELLIPSE, start, end),
            self.stamp_brush,
            affected_region,
        )

    def _create_undo_state(
        self,
        action_name: str,
        region: Optional[Region] = None,
        is_full_update: bool = False,
    ) -> Action:
        """Create an undo state helper.

        Args:
            action_name: Name of the action
            region: Affected region (optional)
            is_full_update: If True, captures full document state

        Returns:
            Action object ready to be updated
        """
        self.image_at_start = AnsiArtDocument(self.image.width, self.image.height)
        self.image_at_start.copy_region(self.image)
        action = Action(action_name)
        self.add_action(action)
        if region:
            action.region = region.intersection(self._get_full_region())
        elif is_full_update:
            action.region = self._get_full_region()
            action.is_full_update = True
        return action

    def _get_full_region(self) -> Region:
        """Get full document region.

        Returns:
            Region covering entire document
        """
        return Region(0, 0, self.image.width, self.image.height)

    def _handle_file_error(
        self, file_path: str, operation: str, error: Exception
    ) -> None:
        """Handle file operation errors.

        Args:
            file_path: Path to the file
            operation: Operation name (Open, Save, Paste, etc.)
            error: Exception that occurred
        """
        error_msg = str(error)
        if isinstance(error, PermissionError):
            self.message_box(operation, _("%1: Permission denied.", file_path), "ok")
        elif isinstance(error, FileNotFoundError):
            self.message_box(operation, _("%1: File not found.", file_path), "ok")
        else:
            self.message_box(operation, _("%1: %2", file_path, error_msg), "ok")

    def _handle_operation_error(
        self,
        operation: str,
        error: Exception,
        context: Optional[str] = None,
    ) -> None:
        """Handle generic operation errors.

        Args:
            operation: Operation name
            error: Exception that occurred
            context: Additional context message (optional)
        """
        error_msg = str(error)
        error_type = type(error).__name__

        if isinstance(error, PermissionError):
            message = _("%1: Permission denied.", operation)
        elif isinstance(error, FileNotFoundError):
            message = _("%1: File not found.", operation)
        elif isinstance(error, ValueError):
            message = _("%1: Invalid value: %2", operation, error_msg)
        elif isinstance(error, TypeError):
            message = _("%1: Type error: %2", operation, error_msg)
        else:
            message = _("%1: %2 (%3)", operation, error_msg, error_type)

        if context:
            message = f"{context}\n{message}"

        self.message_box(operation, message, "ok")

    def _handle_validation_error(
        self, field: str, value: Any, expected: str, operation: str = "Validation"
    ) -> None:
        """Handle validation errors.

        Args:
            field: Field name that failed validation
            value: Invalid value provided
            expected: Expected format/type/range
            operation: Operation name (default: "Validation")
        """
        message = _("Invalid %1: %2\nExpected: %3", field, str(value), expected)
        self.message_box(operation, message, "ok")

    def draw_current_free_form_select_polyline(self) -> Region:
        """Inverts the colors along a polyline defined by tool_points, for Free-Form Select tool preview."""
        # Could optimize to not use stamp_brush, since it's always a single character here.
        gen = polyline_walk(self.tool_points)
        return self._draw_from_generator(gen, deduplicate=True)

    def draw_current_polyline(self) -> Region:
        """Draws a polyline from tool_points, for Polygon tool preview."""
        gen = polyline_walk(self.tool_points)
        return self._draw_from_generator(gen)

    def draw_current_polygon(self) -> Region:
        """Draws a polygon from tool_points, for Polygon tool."""
        gen = polygon_walk(self.tool_points)
        return self._draw_from_generator(gen)

    def draw_current_curve(self) -> Region:
        """Draws a curve (or line) from tool_points, for Curve tool."""
        points = self.tool_points
        if len(points) == 4:
            gen = bezier_curve_walk(
                points[0].x,
                points[0].y,
                points[2].x,
                points[2].y,
                points[3].x,
                points[3].y,
                points[1].x,
                points[1].y,
            )
        elif len(points) == 3:
            gen = quadratic_curve_walk(
                points[0].x,
                points[0].y,
                points[2].x,
                points[2].y,
                points[1].x,
                points[1].y,
            )
        elif len(points) == 2:
            gen = bresenham_walk(
                points[0].x,
                points[0].y,
                points[1].x,
                points[1].y,
            )
        else:
            gen = iter(points)
        return self._draw_from_generator(gen)

    def finalize_polygon_or_curve(self) -> None:
        """Finalizes the polygon or curve shape, creating an undo state."""
        self.cancel_preview()

        if self.selected_tool not in [Tool.polygon, Tool.curve]:
            return

        if self.selected_tool == Tool.polygon and len(self.tool_points) < 3:
            return
        if self.selected_tool == Tool.curve and len(self.tool_points) < 2:
            return

        # Create undo state
        action = self._create_undo_state(self.selected_tool.get_name())

        if self.selected_tool == Tool.polygon:
            affected_region = self.draw_current_polygon()
        else:
            affected_region = self.draw_current_curve()

        action.region = affected_region.intersection(self._get_full_region())
        action.update(self.image_at_start)
        self.canvas.refresh_scaled_region(affected_region)

        self.tool_points = []

    def action_cancel(self) -> None:
        """Action to end the current tool activity, via Escape key."""
        if self.app.focused:
            self.app.set_focus(None)
            return
        self.stop_action_in_progress()

    def stop_action_in_progress(self) -> None:
        """Finalizes the selection, or cancels other tools."""
        self.cancel_preview()
        self.meld_selection()
        self.tool_points = []
        self.mouse_gesture_cancelled = True
        self.get_widget_by_id("status_coords", Static).update("")
        self.get_widget_by_id("status_dimensions", Static).update("")
        if self.selected_tool in [Tool.pick_color, Tool.magnifier]:
            self.selected_tool = self.return_to_tool

    def action_undo(self) -> None:
        """Undoes the last action."""
        # Have to grab the cursor position before stop_action_in_progress because it will meld the selection.
        cursor_position_before = None
        if self.image.selection and self.image.selection.cursor_mode:
            cursor_position_before = self.image.selection.region.offset

        self.stop_action_in_progress()

        outcome = self.history.undo(
            self.image,
            full_region=self._get_full_region(),
            cursor_position=cursor_position_before,
            layer_stack=self.layer_stack,
            inverse_name=lambda name: _("Undo") + " " + name,
        )
        if outcome.changed:
            self._refresh_after_history_change(outcome.layer_state_restored)
            self.canvas.refresh(layout=True)

    def action_redo(self) -> None:
        """Redoes the last undone action."""
        # Have to grab the cursor position before stop_action_in_progress because it will meld the selection.
        cursor_position_before = None
        if self.image.selection and self.image.selection.cursor_mode:
            cursor_position_before = self.image.selection.region.offset

        self.stop_action_in_progress()

        outcome = self.history.redo(
            self.image,
            full_region=self._get_full_region(),
            cursor_position=cursor_position_before,
            layer_stack=self.layer_stack,
            inverse_name=lambda name: _("Undo") + " " + name,
        )
        if outcome.changed:
            self._refresh_after_history_change(outcome.layer_state_restored)
            self.canvas.refresh(layout=True)

    def _refresh_after_history_change(self, layer_state_restored: bool) -> None:
        if not self.layer_stack or not layer_state_restored:
            return
        if self.layer_stack.active_layer:
            self._sync_layer_to_document(self.layer_stack.active_layer.id)
        self.query_one("#layer_panel", LayerManagementPanel).refresh_layers(
            self.layer_stack
        )

    def add_action(self, action: Action) -> None:
        """Adds an action to the undo stack, clearing redos."""
        self.history.add(action)

    def close_windows(self, selector: str) -> None:
        """Close all windows matching the CSS selector."""
        for window in self.query(selector).nodes:
            assert isinstance(window, Window), (
                f"Expected a Window for query '{selector}', but got {window.css_identifier}"
            )
            window.close()

    def start_backup_interval(self) -> None:
        """Auto-save a backup file periodically."""
        self.backup_interval = 10
        self.set_interval(self.backup_interval, self.save_backup)

    def get_backup_file_path(self, session_number: Optional[int] = None) -> str:
        """Returns the path to the backup file.

        Args:
            session_number: Optional session number for numbered backups

        Returns:
            Path to backup file
        """
        from .file_ops import get_backup_file_path as _get_backup_file_path

        return _get_backup_file_path(self, session_number)

    def save_backup(self) -> None:
        """Save to the backup file if there have been changes since it was saved."""
        from .file_ops import save_backup as _save_backup

        _save_backup(self)

    def recover_from_backup(self) -> None:
        """Recover from the backup file, if it exists."""
        from .file_ops import recover_from_backup as _recover_from_backup

        _recover_from_backup(self)

    def action_save(self) -> None:
        """Start the save action, but don't wait for the Save As dialog to close if it's a new file."""
        from .file_ops import save as _save

        async def save_ignoring_result() -> None:
            await _save(self)

        task = asyncio.create_task(save_ignoring_result())
        self.background_tasks.add(task)
        task.add_done_callback(self.background_tasks.discard)

    def write_file_path(
        self, file_path: str, content: bytes, dialog_title: str
    ) -> bool:
        """Write a file, showing an error message and returning False if it fails."""
        from .file_ops import write_file_path as _write_file_path

        return _write_file_path(self, file_path, content, dialog_title)

    def reload_after_save(self, content: bytes, file_path: str) -> bool:
        """Reload the document from saved content, to show information loss from the file format.

        Unlike `open_from_file_path`, this method:
        - doesn't short circuit when the file path matches the current file path, crucially
        - skips backup management (discarding or checking for a backup)
        - skips the file system, which is more efficient
        - is undoable
        """
        from .file_ops import reload_after_save as _reload_after_save

        return _reload_after_save(self, content, file_path)

    def update_palette_from_format_id(self, format_id: str | None) -> None:
        """Update the palette based on the file format.

        In the future, this should update from attributes set when loading the file,
        such as whether it supports color, and if not, it could show pattern fills,
        such as ░▒▓█... that's not a lot of patterns, and you could get those from the
        character picker, but it might be nice to have them more accessible,
        that or to make the character picker a dockable window.
        """
        from .file_ops import (
            update_palette_from_format_id as _update_palette_from_format_id,
        )

        _update_palette_from_format_id(self, format_id)

    async def save(self) -> bool:
        """Save the image to a file.

        Note that this method will never return if the user cancels the Save As dialog.
        """
        from .file_ops import save as _save

        return await _save(self)

    def action_save_as(self) -> None:
        """Show the save as dialog, without waiting for it to close."""
        from .file_ops import save_as as _save_as

        task = asyncio.create_task(_save_as(self))
        self.background_tasks.add(task)
        task.add_done_callback(self.background_tasks.discard)

    async def save_as(self) -> None:
        """Save the image as a new file."""
        from .file_ops import save_as as _save_as

        await _save_as(self)

    def action_copy_to(self) -> None:
        """Save the selection to a file."""
        # DON'T stop_action_in_progress() here, because we want to keep the selection.
        self.close_windows("SaveAsDialogWindow, OpenDialogWindow")

        if self.get_selected_content() is None:
            return

        def handle_selected_file_path(file_path: str) -> None:
            def on_save_confirmed():
                async def async_on_save_confirmed():
                    try:
                        content = self.get_selected_content(file_path)
                    except FormatWriteNotSupported as e:
                        self.message_box(_("Copy To"), e.localized_message, "ok")
                        return
                    if content is None:
                        self.message_box(_("Copy To"), _("No selection."), "ok")
                        return
                    if self.write_file_path(file_path, content, _("Copy To")):
                        window.close()

                task = asyncio.create_task(async_on_save_confirmed())
                self.background_tasks.add(task)
                task.add_done_callback(self.background_tasks.discard)

            if os.path.exists(file_path):
                self.confirm_overwrite(file_path, on_save_confirmed)
            else:
                on_save_confirmed()

        window = SaveAsDialogWindow(
            title=_("Copy To"),
            handle_selected_file_path=handle_selected_file_path,
            selected_file_path=os.path.dirname(self.file_path or ""),
            auto_add_default_extension=".ans",
        )
        self.mount(window)

    def confirm_overwrite(self, file_path: str, callback: Callable[[], None]) -> None:
        """Asks the user if they want to overwrite a file."""
        from .file_ops import confirm_overwrite as _confirm_overwrite

        _confirm_overwrite(self, file_path, callback)

    def confirm_no_undo(self, callback: Callable[[], None]) -> None:
        """Asks the user to confirm that they want to continue with a permanent action."""
        from .file_ops import confirm_no_undo as _confirm_no_undo

        _confirm_no_undo(self, callback)

    def prompt_save_changes(self, file_path: str, callback: Callable[[], None]) -> None:
        """Asks the user if they want to save changes to a file."""
        from .file_ops import prompt_save_changes as _prompt_save_changes

        _prompt_save_changes(self, file_path, callback)

    def confirm_lose_color_information(self, callback: Callable[[], None]) -> None:
        """Confirms discarding color information when saving as a plain text file."""
        from .file_ops import (
            confirm_lose_color_information as _confirm_lose_color_information,
        )

        _confirm_lose_color_information(self, callback)

    def confirm_lose_text_information(self, callback: Callable[[], None]) -> None:
        """Confirms discarding text information when saving as a plain text file."""
        from .file_ops import (
            confirm_lose_text_information as _confirm_lose_text_information,
        )

        _confirm_lose_text_information(self, callback)

    def confirm_save_non_openable_file(self, callback: Callable[[], None]) -> None:
        """Confirms saving into a format that can only be saved, not opened."""
        from .file_ops import (
            confirm_save_non_openable_file as _confirm_save_non_openable_file,
        )

        _confirm_save_non_openable_file(self, callback)

    def confirm_information_loss(
        self, format_id: str | None, callback: Callable[[bool], None]
    ) -> None:
        """Confirms discarding information when saving as a particular format. Callback variant. Never calls back if unconfirmed.

        The callback argument is whether there's information loss AND the file is openable.
        This is used to determine whether the file should be reloaded to show the information loss.
        It can't be reloaded if it's not openable.
        Some formats like PDF (currently) are color-only and can't be opened.
        """
        from .file_ops import confirm_information_loss as _confirm_information_loss

        _confirm_information_loss(self, format_id, callback)

    async def confirm_information_loss_async(self, format_id: str | None) -> bool:
        """Confirms discarding information when saving as a particular format. Awaitable variant, which uses the callback variant."""
        from .file_ops import (
            confirm_information_loss_async as _confirm_information_loss_async,
        )

        return await _confirm_information_loss_async(self, format_id)

    def is_document_modified(self) -> bool:
        """Returns whether the document has been modified since the last save."""
        from .file_ops import is_document_modified as _is_document_modified

        return _is_document_modified(self)

    def discard_backup(self) -> None:
        """Deletes the backup file, if it exists."""
        from .file_ops import discard_backup as _discard_backup

        _discard_backup(self)

    def discard_backup_and_exit(self) -> None:
        """Exit the program immediately, deleting the backup file."""
        self.discard_backup()
        self.exit()

    def action_exit(self) -> None:
        """Exit the program, prompting to save changes if necessary."""
        if self.is_document_modified():
            self.prompt_save_changes(
                self.file_path or _("Untitled"), self.discard_backup_and_exit
            )
        else:
            self.discard_backup_and_exit()

    def action_reload(self) -> None:
        """Reload the program, prompting to save changes if necessary."""
        if self.is_document_modified():
            self.prompt_save_changes(self.file_path or _("Untitled"), restart_program)
        else:
            restart_program()

    def action_update_screenshot(self) -> None:
        """Update the screenshot on the readme."""
        folder = os.path.join(os.path.dirname(__file__), "..", "..")
        self.save_screenshot(filename="screenshot.svg", path=folder)

    def message_box(
        self,
        title: str,
        message: Widget | str,
        button_types: str = "ok",
        callback: Callable[[Button], None] | None = None,
        icon_widget: Widget | None = None,
        error: Exception | None = None,
    ) -> None:
        """Show a warning message box with the given title, message, and buttons."""

        if icon_widget is None:
            icon_widget = get_warning_icon()

        # self.close_windows("#message_box")

        self.bell()

        def handle_button(button: Button) -> None:
            if callback:
                callback(button)
            window.close()

        window = MessageBox(
            title=title,
            icon_widget=icon_widget,
            message=message,
            error=error,
            button_types=button_types,
            handle_button=handle_button,
        )
        self.mount(window)

    def open_from_file_path(
        self, file_path: str, opened_callback: Callable[[], None]
    ) -> None:
        """Opens the given file for editing, prompting to save changes if necessary."""
        from .file_ops import open_from_file_path as _open_from_file_path

        _open_from_file_path(self, file_path, opened_callback)

    def action_open(self) -> None:
        """Show dialog to open an image from a file."""

        def handle_selected_file_path(file_path: str) -> None:
            self.open_from_file_path(file_path, window.close)

        self.close_windows("SaveAsDialogWindow, OpenDialogWindow")
        window = OpenDialogWindow(
            title=_("Open"),
            handle_selected_file_path=handle_selected_file_path,
            selected_file_path=self.file_path,
        )
        self.mount(window)

    def action_paste_from(self) -> None:
        """Paste a file as a selection."""

        def handle_selected_file_path(file_path: str) -> None:
            try:
                if os.path.getsize(file_path) > MAX_FILE_SIZE:
                    self.message_box(
                        _("Paste"), _("The file is too large to open."), "ok"
                    )
                    return

                file_ext = os.path.splitext(file_path)[1].lower()
                image_extensions = {
                    ".png",
                    ".jpg",
                    ".jpeg",
                    ".gif",
                    ".bmp",
                    ".webp",
                    ".tiff",
                    ".tif",
                }

                if file_ext in image_extensions:
                    try:
                        with open(file_path, "rb") as f:
                            image_bytes = f.read()
                        ansi_doc = AnsiArtDocument.from_image_format(image_bytes)
                        ansi_art = ansi_doc.get_ansi()
                        self.paste(ansi_art)
                        window.close()
                        return
                    except UnidentifiedImageError:
                        self.message_box(
                            _("Paste"),
                            _(
                                "This is not a valid image file, or its format is not currently supported."
                            ),
                            "ok",
                        )
                        return
                    except Exception as e:
                        context = _("Failed to convert image to ANSI art")
                        self._handle_operation_error(_("Paste"), e, context=context)
                        return

                with open(file_path, encoding="utf-8") as f:
                    self.paste(f.read())
                window.close()
            except Exception as e:
                self._handle_file_error(file_path, _("Paste"), e)

        self.close_windows("SaveAsDialogWindow, OpenDialogWindow")
        window = OpenDialogWindow(
            title=_("Paste From"),
            handle_selected_file_path=handle_selected_file_path,
            selected_file_path=os.path.dirname(self.file_path or ""),
        )
        self.mount(window)

    def action_new(self, *, force: bool = False, manage_backup: bool = True) -> None:
        """Create a new image, discarding the backup file for the old file path, and undos/redos.

        This method is used as part of opening files as well,
        in which case force=True and recover=False,
        because prompting and recovering are handled outside.
        """
        if self.is_document_modified() and not force:

            def go_ahead():
                self.action_new(force=True, manage_backup=manage_backup)

            self.prompt_save_changes(self.file_path or _("Untitled"), go_ahead)
            return

        if manage_backup:
            self.discard_backup()  # for OLD file_path (must be done before changing self.file_path)

        self.image = AnsiArtDocument(80, 24)
        self.canvas.image = self.image
        self.canvas.refresh(layout=True)
        self.file_path = None
        self.saved_undo_count = 0
        self.backup_saved_undo_count = 0
        self.history.clear()
        self.preview_action = None
        self.selected_bg_color = self.palette[0]
        self.selected_fg_color = self.palette[len(self.palette) // 2]
        self.selected_char = " "

        if manage_backup:
            self.recover_from_backup()

    def action_open_character_selector(self) -> None:
        """Show dialog to select a character."""
        self.close_windows("#character_selector_dialog")

        def handle_selected_character(character: str) -> None:
            self.selected_char = character
            window.close()

        window = CharacterSelectorDialogWindow(
            id="character_selector_dialog",
            handle_selected_character=handle_selected_character,
            selected_character=self.selected_char,
            title=_("Choose Character"),
        )
        self.mount(window)

    def action_swap_colors(self) -> None:
        """Swap the foreground and background colors."""
        self.selected_bg_color, self.selected_fg_color = (
            self.selected_fg_color,
            self.selected_bg_color,
        )

    def action_edit_colors(
        self, color_palette_index: int | None = None, as_foreground: bool = False
    ) -> None:
        """Show dialog to edit colors."""
        self.close_windows("#edit_colors_dialog")

        def handle_selected_color(color: str) -> None:
            if as_foreground:
                self.selected_fg_color = color
            else:
                self.selected_bg_color = color
            if color_palette_index is not None:
                self.palette = (
                    *self.palette[:color_palette_index],
                    color,
                    *self.palette[color_palette_index + 1 :],
                )
            window.close()

        window = EditColorsDialogWindow(
            id="edit_colors_dialog",
            handle_selected_color=handle_selected_color,
            selected_color=self.selected_bg_color,
            title=_("Edit Colors"),
        )
        self.mount(window)

    def read_palette(self, file_content: str) -> Tuple[str, ...]:
        """Read a GIMP Palette file."""
        format_name = "GIMP Palette"
        lines = file_content.splitlines()
        if lines[0] != format_name:
            raise ValueError(f"Not a {format_name}.")

        colors: List[str] = []
        line_index = 0
        while line_index + 1 < len(lines):
            line_index += 1
            line = lines[line_index]

            if line[0] == "#" or line == "":
                continue

            if line.startswith("Name:"):
                # palette.name = line.split(":", 1)[1].strip()
                continue

            if line.startswith("Columns:"):
                # palette.number_of_columns = int(line.split(":", 1)[1])
                continue

            r_g_b_name = re.match(
                r"^\s*([0-9]+)\s+([0-9]+)\s+([0-9]+)(?:\s+(.*))?$", line
            )
            if not r_g_b_name:
                raise ValueError(
                    f"Line {line_index + 1} doesn't match pattern of "
                    f"red green blue name."
                )

            red = int(r_g_b_name[1])
            green = int(r_g_b_name[2])
            blue = int(r_g_b_name[3])
            # name = r_g_b_name[4]
            colors.append(f"#{red:02x}{green:02x}{blue:02x}")

        return tuple(colors)

    def load_palette(self, file_content: str) -> None:
        """Load a palette from a GIMP palette file."""
        try:
            new_colors = self.read_palette(file_content)
        except ValueError as e:
            self.message_box(
                _("Paint"), _("Unexpected file format.") + "\n" + str(e), "ok"
            )
            return
        except Exception as e:
            self._handle_operation_error(
                _("Read palette"),
                e,
                context=_("Failed to read palette file."),
            )
            return
        self.palette = new_colors[: len(self.palette)] + (new_colors[0],) * (
            len(self.palette) - len(new_colors)
        )

    def action_get_colors(self) -> None:
        """Show a dialog to select a palette file to load."""

        def handle_selected_file_path(file_path: str) -> None:
            try:
                with open(file_path, encoding="utf-8") as f:
                    self.load_palette(f.read())
            except UnicodeDecodeError:
                self.message_box(
                    _("Open"),
                    file_path
                    + "\n"
                    + _("Paint cannot read this file.")
                    + "\n"
                    + _("Unexpected file format.")
                    + "\n"
                    + _("Only GIMP Palette files (*.gpl) are supported for now."),
                    "ok",
                )
            except FileNotFoundError:
                self.message_box(
                    _("Open"),
                    file_path
                    + "\n"
                    + _("File not found.")
                    + "\n"
                    + _("Please verify that the correct path and file name are given."),
                    "ok",
                )
            except IsADirectoryError:
                error_msg = f"{file_path}\n{_('Invalid file.')}"
                self.message_box(_("Open"), error_msg, "ok")
            except PermissionError:
                error_msg = f"{file_path}\n{_('Access denied.')}"
                self.message_box(_("Open"), error_msg, "ok")
            except Exception as e:
                context = _("An unexpected error occurred while reading %1.", file_path)
                self._handle_operation_error(_("Open"), e, context=context)
            else:
                window.close()

        self.close_windows("SaveAsDialogWindow, OpenDialogWindow")
        window = OpenDialogWindow(
            title=_("Get Colors"),
            handle_selected_file_path=handle_selected_file_path,
            selected_file_path=self.file_path,
        )
        self.mount(window)

    def action_save_colors(self) -> None:
        """Show a dialog to save the current palette to a file."""

        def handle_selected_file_path(file_path: str) -> None:
            color_lines: List[str] = []
            for color_str in self.palette:
                red, green, blue = Color.parse(color_str).rgb
                red = str(red).ljust(3, " ")
                green = str(green).ljust(3, " ")
                blue = str(blue).ljust(3, " ")
                name = ""
                color_line = f"{red} {green} {blue}   {name}"
                color_lines.append(color_line)

            newline = "\n"  # f-strings are stupid, at least until Python 3.12
            # https://docs.python.org/3.12/whatsnew/3.12.html#pep-701-syntactic-formalization-of-f-strings
            palette_str = f"""GIMP Palette
Name: Saved Colors
Columns: {len(self.palette) // 2}
{newline.join(color_lines)}
"""

            palette_bytes = palette_str.encode("utf-8")
            if file_path[-4:].lower() != ".gpl":
                file_path += ".gpl"
            success = self.write_file_path(file_path, palette_bytes, _("Save Colors"))
            if success:
                window.close()

        self.close_windows("SaveAsDialogWindow, OpenDialogWindow")
        window = SaveAsDialogWindow(
            title=_("Save Colors"),
            handle_selected_file_path=handle_selected_file_path,
            selected_file_path=self.file_path,
        )
        self.mount(window)

    @on(ChatWindow.MessageSent)
    async def on_chat_window_message_sent(self, event: ChatWindow.MessageSent) -> None:
        """Handle messages sent from the chat window."""
        self.log(f"User message: {event.message_text}")
        await self.agent.process_message(event.message_text)

    def send_message_to_chat(
        self, sender: str, message: str, message_type: str = "agent"
    ) -> None:
        """Send a message to the chat window."""
        if self.chat_window:
            self.chat_window.add_message(sender, message, message_type)

    def action_print_preview(self) -> None:
        """Show print preview of the current image."""
        from .print_utils import show_print_preview

        show_print_preview(self)

    def action_page_setup(self) -> None:
        """Configure page settings for printing."""
        from .print_utils import show_page_setup

        show_page_setup(self)

    def action_print(self) -> None:
        """Print the current image."""
        from .print_utils import print_image

        print_image(self)

    def action_send(self) -> None:
        """Export image to a file in various formats."""
        from .file_ops import export_image as _export_image

        task = asyncio.create_task(_export_image(self))
        self.background_tasks.add(task)
        task.add_done_callback(self.background_tasks.discard)

    def action_set_as_wallpaper_tiled(self) -> None:
        """Tile the image as the wallpaper."""
        self.set_as_wallpaper(tiled=True)

    def action_set_as_wallpaper_centered(self) -> None:
        """Center the image as the wallpaper."""
        self.set_as_wallpaper(tiled=False)

    # worker thread helps keep the UI responsive
    @work(exclusive=True, thread=True)
    def set_as_wallpaper(self, tiled: bool) -> None:
        """Set the image as the wallpaper."""
        try:
            wallpaper_dir = os.path.join(get_config_dir("aura-paint"), "wallpaper")
            os.makedirs(wallpaper_dir, exist_ok=True)
            # svg = self.image.get_svg()
            # image_path = os.path.join(dir, "wallpaper.svg")
            # with open(image_path, "w", encoding="utf-8") as f:
            #     f.write(svg)

            image_path = os.path.join(wallpaper_dir, f"wallpaper_{uuid4()}.png")
            keep_files = 5
            files = os.listdir(wallpaper_dir)
            files.sort(key=lambda f: os.path.getmtime(os.path.join(wallpaper_dir, f)))
            for file in files[:-keep_files]:
                os.remove(os.path.join(wallpaper_dir, file))

            screen_size = self.get_screen_size()
            im = rasterize(self.image)
            im_w, im_h = im.size
            if tiled:
                new_im = Image.new("RGBA", screen_size)
                w, h = new_im.size
                for i in range(0, w, im_w):
                    for j in range(0, h, im_h):
                        new_im.paste(im, (i, j))
            else:
                new_im = Image.new("RGBA", screen_size)
                w, h = new_im.size
                new_im.paste(im, (w // 2 - im_w // 2, h // 2 - im_h // 2))
            new_im.save(image_path)
            if get_current_worker().is_cancelled:
                return  # You'd have to be really fast with the menus to cancel it...
            set_wallpaper(image_path)
        except Exception as e:
            # self.message_box(_("Paint"), _("Failed to set the wallpaper."),
            #                  "ok", error=e)
            # Because this is running in a thread, we can't directly access
            # the UI.
            self.call_from_thread(
                self.message_box,
                _("Paint"),
                _("Failed to set the wallpaper."),
                "ok",
                error=e,
            )

    def get_screen_size(self) -> Size:
        """Get the screen size.

        Tests for DPI scaling are in tests/unit/tui/tools/paint/test_dpi_scaling.py
        """
        try:
            # special macOS handling to avoid a Python rocket icon bouncing in the dock
            # (with screeninfo module it bounced; with tkinter it didn't, but still it stayed there indefinitely)
            if sys.platform == "darwin":
                from Quartz import CGDisplayBounds, CGMainDisplayID

                main_monitor = CGDisplayBounds(CGMainDisplayID())
                return Size(int(main_monitor.size.width), int(main_monitor.size.height))

            # from screeninfo import get_monitors
            # largest_area = 0
            # largest_monitor = None
            # for m in get_monitors():
            #     area = m.width * m.height
            #     if area > largest_area:
            #         largest_area = area
            #         largest_monitor = m
            # assert largest_monitor is not None, "No monitors found."
            # return largest_monitor.width, largest_monitor.height

            import tkinter

            root = tkinter.Tk()
            root.withdraw()
            size = Size(root.winfo_screenwidth(), root.winfo_screenheight())
            root.destroy()
            return size
        except Exception as e:
            print("Failed to get screen size:", e)
            return Size(1920, 1080)

    def action_recent_file(self) -> None:
        """Show dialog to open a recently opened file."""
        from .recent_files_dialog import RecentFilesDialogWindow

        def handle_selected_file_path(file_path: str) -> None:
            self.open_from_file_path(file_path, window.close)

        self.close_windows(
            "RecentFilesDialogWindow, SaveAsDialogWindow, OpenDialogWindow"
        )
        window = RecentFilesDialogWindow(
            title=_("Recent Files"),
            handle_selected_file_path=handle_selected_file_path,
        )
        self.mount(window)

    def action_cut(self) -> None:
        """Cut the selection to the clipboard."""
        if self.action_copy():
            self.action_clear_selection()

    def get_selected_content(self, file_path: str | None = None) -> bytes | None:
        """Returns the content of the selection, or underlying the selection if it hasn't been cut out yet.

        For a textbox, returns the selected text within the textbox. May include ANSI escape sequences, either way.

        Raises FormatWriteNotSupported if the file_path implies a format that can't be encoded.
        Defaults to ANSI if `file_path` is None (or empty string).
        """
        sel = self.image.selection
        if sel is None:
            return None
        had_contained_image = sel.contained_image is not None
        try:
            if sel.contained_image is None:
                # Temporarily copy underlying image.
                # Don't want to make an undo state, unlike when cutting out a selection when you drag it.
                sel.copy_from_document(self.image)
                assert sel.contained_image is not None
            if sel.textbox_mode:
                text = selected_text(sel).encode("utf-8")
            else:
                format_id = (
                    AnsiArtDocument.format_from_extension(file_path)
                    if file_path
                    else "ANSI"
                )
                text = sel.contained_image.encode_to_format(format_id)
        finally:
            if not had_contained_image:
                sel.contained_image = None
        return text

    def action_copy(self, from_ctrl_c: bool = False) -> bool:
        """Copy the selection to the clipboard."""
        try:
            content = self.get_selected_content()
            if content is None:
                if from_ctrl_c:
                    message = "Pressione Ctrl+Q para sair."
                    self.get_widget_by_id("status_text", Static).update(message)
                return False
            # Avoid redundant encoding/decoding by keeping as bytes when possible
            import pyperclip  # type: ignore

            # Try to copy as image format if content is image bytes
            if isinstance(content, bytes):
                try:
                    # Check if it's a valid image format
                    Image.open(io.BytesIO(content))
                    # Try to copy as image (if pyperclip supports it)
                    try:
                        pyperclip.copy(content, format="image")
                        return True
                    except (TypeError, AttributeError) as error:
                        # Fallback to text if image format not supported
                        logger.debug(
                            "Clipboard adapter does not support image copy",
                            exc_info=error,
                        )
                except (UnidentifiedImageError, Exception) as error:
                    # Not an image, decode as text
                    logger.debug("Clipboard content is not an image", exc_info=error)

            # Copy as text (ANSI art)
            text = content.decode("utf-8") if isinstance(content, bytes) else content
            pyperclip.copy(text)
        except Exception as e:
            self._handle_operation_error(
                _("Copy to clipboard"),
                e,
                context=_("Failed to copy to the clipboard."),
            )
            return False
        return True

    def action_paste(self) -> None:
        """Paste the clipboard (ANSI art allowed), either as a selection, or into a textbox."""
        try:
            import pyperclip  # type: ignore

            # Try to get image from clipboard first (if available)
            try:
                clipboard_image = pyperclip.paste(format="image")
                if clipboard_image:
                    ansi_doc = AnsiArtDocument.from_image_format(clipboard_image)
                    ansi_art = ansi_doc.get_ansi()
                    self.paste(ansi_art)
                    return
            except (TypeError, AttributeError, ValueError) as error:
                logger.debug(
                    "Clipboard adapter does not expose image paste", exc_info=error
                )

            text: str = pyperclip.paste()
            if not text:
                return
            self.paste(text)
        except Exception as e:
            self._handle_operation_error(
                _("Paste from clipboard"),
                e,
                context=_("Error getting the Clipboard Data!"),
            )
            return

    def paste(self, text: str) -> None:
        """Paste the given text (ANSI art allowed), either as a selection, or into a textbox."""
        if self.image.selection and self.image.selection.textbox_mode:
            pasted_image = AnsiArtDocument.from_text(
                text,
                default_bg=self.selected_bg_color,
                default_fg=self.selected_fg_color,
            )
            textbox = self.image.selection
            assert textbox.contained_image is not None
            paste_region = Region(
                *textbox.text_selection_start, pasted_image.width, pasted_image.height
            )
            if (
                paste_region.right > textbox.region.width
                or paste_region.bottom > textbox.region.height
            ):
                self.message_box(
                    _("Paint"),
                    _("Not enough room to paste text.")
                    + "\n\n"
                    + _("Enlarge the text area and try again."),
                    "ok",
                )
                return
            textbox.contained_image.copy_region(
                source=pasted_image, target_region=paste_region
            )
            textbox.textbox_edited = True
            self.canvas.refresh_scaled_region(textbox.region)
            return
        pasted_image = AnsiArtDocument.from_text(text)

        def do_the_paste() -> None:
            self.stop_action_in_progress()
            self.image.selection = Selection(
                Region.from_offset(
                    self.get_document_coords_at_top_left_corner(),
                    (pasted_image.width, pasted_image.height),
                )
            )
            self.image.selection.contained_image = pasted_image
            self.image.selection.pasted = (
                True  # create undo state when finalizing selection
            )
            self.canvas.refresh_scaled_region(self.image.selection.region)
            self.selected_tool = Tool.select

        if (
            pasted_image.width > self.image.width
            or pasted_image.height > self.image.height
        ):
            message = (
                _("The image in the clipboard is larger than the bitmap.")
                + "\n"
                + _("Would you like the bitmap enlarged?")
            )

            def handle_button(button: Button) -> None:
                if button.has_class("yes"):
                    self.resize_document(
                        max(pasted_image.width, self.image.width),
                        max(pasted_image.height, self.image.height),
                    )
                    do_the_paste()
                elif button.has_class("no"):
                    do_the_paste()

            title = get_windows_icon_markup() + " " + _("Paint")
            self.message_box(
                title,
                message,
                "yes/no/cancel",
                handle_button,
                icon_widget=get_question_icon(),
            )
        else:
            do_the_paste()

    def action_select_all(self) -> None:
        """Select the entire image, or in a textbox, all the text."""
        if self.image.selection and self.image.selection.textbox_mode:
            assert self.image.selection.contained_image is not None
            self.image.selection.text_selection_start = Offset(0, 0)
            self.image.selection.text_selection_end = Offset(
                self.image.selection.contained_image.width - 1,
                self.image.selection.contained_image.height - 1,
            )
            self.canvas.refresh_scaled_region(self.image.selection.region)
        else:
            self.stop_action_in_progress()
            self.image.selection = Selection(self._get_full_region())
            self.canvas.refresh()
            self.selected_tool = Tool.select

    def action_text_toolbar(self) -> None:
        """Show text formatting toolbar for textbox selections."""
        if not self.image.selection or not self.image.selection.textbox_mode:
            self.message_box(
                _("Text Toolbar"),
                _("Text toolbar is only available when editing text."),
                "ok",
            )
            return
        self.message_box(
            _("Text Toolbar"),
            _(
                "Text formatting options:\n\n"
                "Foreground color: Use color picker\n"
                "Background color: Use color picker\n"
                "Character: Use character selector\n\n"
                "Opções avançadas de formatação disponíveis via color picker e character selector."
            ),
            "ok",
        )

    def action_normal_size(self) -> None:
        """Zoom to 1x."""
        self.magnification = 1

    def action_large_size(self) -> None:
        """Zoom to 4x."""
        self.magnification = 4

    def action_custom_zoom(self) -> None:
        """Show dialog to set zoom level."""
        self.close_windows("#zoom_dialog")

        def handle_button(button: Button) -> None:
            if button.has_class("ok"):
                radio_button = window.content.query_one(RadioSet).pressed_button
                assert radio_button is not None
                assert radio_button.id is not None
                self.magnification = int(radio_button.id.split("_")[1])
                window.close()
            else:
                window.close()

        window = DialogWindow(
            id="zoom_dialog",
            title=_("Custom Zoom"),
            handle_button=handle_button,
        )
        window.content.mount(
            Vertical(
                Horizontal(
                    Static(_("Current zoom:")),
                    Static(str(self.magnification * 100) + "%"),
                ),
                RadioSet(
                    RadioButton(_("100%"), id="value_1"),
                    RadioButton(_("200%"), id="value_2"),
                    RadioButton(_("400%"), id="value_4"),
                    RadioButton(_("600%"), id="value_6"),
                    RadioButton(_("800%"), id="value_8"),
                    classes="autofocus",
                ),
            ),
            Container(
                Button(_("OK"), classes="ok submit", variant="primary"),
                Button(_("Cancel"), classes="cancel"),
                classes="buttons",
            ),
        )
        window.content.query_one(
            "#value_" + str(self.magnification), RadioButton
        ).value = True
        window.content.query_one(RadioSet).border_title = _("Zoom to")

        def reorder_radio_buttons() -> None:
            """Visually reorder the radio buttons to top-down, left-right.

            (If I reorder them in the DOM, the navigation order won't be right.)

            This needs to be run after the buttons are mounted so that their positions are known.
            """
            radio_buttons = window.content.query(RadioButton)
            radio_button_absolute_positions = [
                radio_button.region.offset for radio_button in radio_buttons
            ]
            order = [0, 3, 1, 4, 2]
            radio_button_absolute_target_positions = [
                radio_button_absolute_positions[order[i]]
                for i in range(len(radio_buttons))
            ]
            for (
                radio_button,
                radio_button_absolute_position,
                radio_button_absolute_target_position,
            ) in zip(
                radio_buttons,
                radio_button_absolute_positions,
                radio_button_absolute_target_positions,
                strict=True,
            ):
                relative_position = (
                    radio_button_absolute_target_position
                    - radio_button_absolute_position
                )
                radio_button.styles.offset = relative_position

        self.mount(window)
        # Reorder radio buttons after layout but before rendering to avoid flash
        # Using call_after_refresh ensures layout is complete but rendering hasn't started
        self.call_after_refresh(reorder_radio_buttons)

    def action_toggle_grid(self) -> None:
        """Toggle the grid setting. Note that it's only shown at 4x zoom or higher."""
        self.show_grid = not self.show_grid

    def action_toggle_thumbnail(self) -> None:
        """Toggle thumbnail preview display."""
        self.show_thumbnail = not self.show_thumbnail
        self.canvas.refresh()

    def action_view_bitmap(self) -> None:
        """Shows the image in full-screen, without the UI."""
        self.cancel_preview()
        self.toggle_class("view_bitmap")
        if self.has_class("view_bitmap"):
            # entering View Bitmap mode
            self.old_scroll_offset = self.editing_area.scroll_offset
            self.canvas.magnification = 1  # without setting self.magnification, so we can restore the canvas to the current setting
            # Keep the left/top of the image in place in the viewport, when the image is larger than the viewport.
            adjusted_x = self.editing_area.scroll_x // self.magnification
            adjusted_y = self.editing_area.scroll_y // self.magnification
            self.editing_area.scroll_to(adjusted_x, adjusted_y, animate=False)
        else:
            # exiting View Bitmap mode
            self.canvas.magnification = self.magnification
            # This relies on the call_after_refresh in this method, for the magnification to affect the scrollable region.
            # I doubt this is considered part of the API contract, so it may break in the future.
            # Also, ideally we would update the screen in one go, without a flash of the wrong scroll position.
            self.editing_area.scroll_to(*self.old_scroll_offset, animate=False)

    def action_flip_rotate(self) -> None:
        """Show dialog to flip or rotate the image."""
        self.close_windows("#flip_rotate_dialog")

        def handle_button(button: Button) -> None:
            if button.has_class("ok"):
                if window.content.query_one("#flip_horizontal", RadioButton).value:
                    self.action_flip_horizontal()
                elif window.content.query_one("#flip_vertical", RadioButton).value:
                    self.action_flip_vertical()
                elif window.content.query_one("#rotate_by_angle", RadioButton).value:
                    radio_button = window.content.query_one(
                        "#angle", RadioSet
                    ).pressed_button
                    assert radio_button is not None, (
                        "There should always be a pressed button; one should've been selected initially."
                    )
                    assert radio_button.id is not None, (
                        "Each radio button should have been given an ID."
                    )
                    angle = int(radio_button.id.split("_")[-1])
                    self.action_rotate_by_angle(angle)
            window.close()

        window = DialogWindow(
            id="flip_rotate_dialog",
            title=_("Flip/Rotate"),
            handle_button=handle_button,
        )
        window.content.mount(
            Container(
                RadioSet(
                    RadioButton(
                        _("Flip horizontal"), id="flip_horizontal", classes="autofocus"
                    ),
                    RadioButton(_("Flip vertical"), id="flip_vertical"),
                    RadioButton(_("Rotate by angle"), id="rotate_by_angle"),
                    classes="autofocus",
                    id="flip_rotate_radio_set",
                ),
                RadioSet(
                    RadioButton(_("90°"), id="angle_90"),
                    RadioButton(_("180°"), id="angle_180"),
                    RadioButton(_("270°"), id="angle_270"),
                    classes="autofocus",
                    id="angle",
                ),
                id="flip_rotate_fieldset",
                classes="fieldset",
            ),
            Container(
                Button(_("OK"), classes="ok submit", variant="primary"),
                Button(_("Cancel"), classes="cancel"),
                classes="buttons",
            ),
        )
        window.content.query_one("#flip_rotate_fieldset", Container).border_title = _(
            "Flip or rotate"
        )
        window.content.query_one("#flip_horizontal", RadioButton).value = True
        window.content.query_one("#angle_90", RadioButton).value = True
        self.mount(window)

    @on(RadioSet.Changed, "#flip_rotate_radio_set")
    def conditionally_enable_angle_radio_buttons(self, event: RadioSet.Changed) -> None:
        """Enable/disable the angle radio buttons based on the logically-outer radio selection."""
        self.query_one("#angle", RadioSet).disabled = (
            event.pressed.id != "rotate_by_angle"
        )

    def action_flip_horizontal(self) -> None:
        """Flip the image horizontally."""
        action = self._create_undo_state(_("Flip horizontal"), is_full_update=True)
        action.update(self.image)
        flip_horizontal(self.image)
        self.canvas.refresh()

    def action_flip_vertical(self) -> None:
        """Flip the image vertically."""
        action = self._create_undo_state(_("Flip vertical"), is_full_update=True)
        action.update(self.image)
        flip_vertical(self.image)
        self.canvas.refresh()

    def action_rotate_by_angle(self, angle: int) -> None:
        """Rotate the image by the given angle, one of 90, 180, or 270."""
        action = self._create_undo_state(_("Rotate by angle"), is_full_update=True)
        action.update(self.image)
        rotate(self.image, angle)
        self.canvas.refresh(layout=True)

    def action_stretch_skew(self) -> None:
        """Open the stretch/skew dialog."""
        self.close_windows("#stretch_skew_dialog")

        def handle_button(button: Button) -> None:
            if button.has_class("ok"):
                horizontal_stretch = float(
                    window.content.query_one("#horizontal_stretch", Input).value
                )
                vertical_stretch = float(
                    window.content.query_one("#vertical_stretch", Input).value
                )
                horizontal_skew = float(
                    window.content.query_one("#horizontal_skew", Input).value
                )
                vertical_skew = float(
                    window.content.query_one("#vertical_skew", Input).value
                )
                self.action_stretch_skew_by(
                    horizontal_stretch, vertical_stretch, horizontal_skew, vertical_skew
                )
            window.close()

        window = DialogWindow(
            id="stretch_skew_dialog",
            title=_("Stretch/Skew"),
            handle_button=handle_button,
        )
        try:
            file_name = (
                "stretch_skew_icons_full_ascii.ans"
                if args.ascii_only
                else "stretch_skew_icons.ans"
            )
            with open(
                os.path.join(os.path.dirname(__file__), file_name), encoding="utf-8"
            ) as f:
                icons_ansi = f.read()
                icons_doc = AnsiArtDocument.from_ansi(icons_ansi)
                icons_rich_markup = icons_doc.get_rich_console_markup()
                icons_rich_markup = icons_rich_markup.replace("on #004040", "").replace(
                    "on rgb(0,64,64)", ""
                )
                icon_height = icons_doc.height // 4
                lines = icons_rich_markup.split("\n")
                icons: List[Text | str] = []
                for i in range(4):
                    icon_markup = "\n".join(
                        lines[i * icon_height : (i + 1) * icon_height]
                    )
                    icons.append(Text.from_markup(icon_markup))
        except Exception as e:
            print("Failed to load icons for Stretch/Skew dialog:", repr(e))
            icons = [""] * 4
        window.content.mount(
            Container(
                Horizontal(
                    Static(icons[0], classes="stretch_skew_icon"),
                    Static(_("Horizontal:"), classes="left-label"),
                    Input(value="100", id="horizontal_stretch", classes="autofocus"),
                    Static(_("%"), classes="right-label"),
                ),
                Horizontal(
                    Static(icons[1], classes="stretch_skew_icon"),
                    Static(_("Vertical:"), classes="left-label"),
                    Input(value="100", id="vertical_stretch"),
                    Static(_("%"), classes="right-label"),
                ),
                id="stretch_fieldset",
                classes="fieldset",
            ),
            Container(
                Horizontal(
                    Static(icons[2], classes="stretch_skew_icon"),
                    Static(_("Horizontal:"), classes="left-label"),
                    Input(value="0", id="horizontal_skew"),
                    Static(_("Degrees"), classes="right-label"),
                ),
                Horizontal(
                    Static(icons[3], classes="stretch_skew_icon"),
                    Static(_("Vertical:"), classes="left-label"),
                    Input(value="0", id="vertical_skew"),
                    Static(_("Degrees"), classes="right-label"),
                ),
                id="skew_fieldset",
                classes="fieldset",
            ),
            Container(
                Button(_("OK"), classes="ok submit", variant="primary"),
                Button(_("Cancel"), classes="cancel"),
                classes="buttons",
            ),
        )
        window.content.query_one("#stretch_fieldset", Container).border_title = _(
            "Stretch"
        )
        window.content.query_one("#skew_fieldset", Container).border_title = _("Skew")
        window.content.query_one("#horizontal_stretch", Input).value = "100"
        window.content.query_one("#vertical_stretch", Input).value = "100"
        window.content.query_one("#horizontal_skew", Input).value = "0"
        window.content.query_one("#vertical_skew", Input).value = "0"
        self.mount(window)

    def action_stretch_skew_by(
        self,
        horizontal_stretch: float,
        vertical_stretch: float,
        horizontal_skew: float,
        vertical_skew: float,
    ) -> None:
        """Stretch/skew the image by the given amounts."""

        action = self._create_undo_state(_("Stretch/skew"), is_full_update=True)
        action.update(self.image)
        stretch_skew(
            self.image,
            horizontal_percent=horizontal_stretch,
            vertical_percent=vertical_stretch,
            horizontal_degrees=horizontal_skew,
            vertical_degrees=vertical_skew,
        )
        self.canvas.refresh(layout=True)

    def action_invert_colors_unless_should_switch_focus(self) -> None:
        """Try to distinguish between Tab and Ctrl+I scenarios."""
        # pretty simple heuristic, but seems effective
        # I didn't make the dialogs modal, but it's OK if this
        # assumes you'll be interacting with the modal rather than the canvas
        # (even though you can, for instance, draw on the canvas while the dialog is open)
        if self.query(DialogWindow):
            # self.action_focus_next()
            # DialogWindow has a special focus_next action that wraps within the dialog.
            # await self.run_action("focus_next", self.query_one(DialogWindow))
            # There may be multiple dialogs open, so we need to find the one that's focused.
            node: DOMNode | None = self.focused
            while node is not None:
                if isinstance(node, DialogWindow):
                    # await self.run_action("focus_next", node)
                    node.action_focus_next()
                    return
                node = node.parent
            self.action_focus_next()
        else:
            self.action_invert_colors()

    def action_invert_colors(self) -> None:
        """Invert the colors of the image or selection."""
        self.cancel_preview()
        sel = self.image.selection
        if sel:
            if sel.textbox_mode:
                return
            if sel.contained_image is None:
                self.extract_to_selection()
                assert sel.contained_image is not None
            sel.contained_image.invert()
            self.canvas.refresh_scaled_region(sel.region)
        else:
            action = self._create_undo_state(_("Invert Colors"), is_full_update=True)
            action.update(self.image)

            self.image.invert()
            self.canvas.refresh()

    def resize_document(self, width: int, height: int) -> None:
        """Resize the document, creating an undo state, and refresh the canvas."""
        self.cancel_preview()

        # Capture current viewport scroll position before resize
        try:
            scroll_x, scroll_y = self.editing_area.scroll_offset
            viewport_x = scroll_x / self.magnification if self.magnification > 0 else 0
            viewport_y = scroll_y / self.magnification if self.magnification > 0 else 0
        except (AttributeError, TypeError):
            viewport_x = viewport_y = 0

        # Create undo state (full update for resize)
        self._create_undo_state(
            _("Attributes"),
            self._get_full_region(),
            is_full_update=True,
        )

        self.image.resize(
            width,
            height,
            default_bg=self.selected_bg_color,
            default_fg=self.selected_fg_color,
        )

        # Keep the top left corner of the viewport in the same place after resize
        # This provides better UX by maintaining user's view position
        try:
            # Restore scroll position after resize
            new_scroll_x = int(viewport_x * self.magnification)
            new_scroll_y = int(viewport_y * self.magnification)
            self.editing_area.scroll_to(new_scroll_x, new_scroll_y, animate=False)
        except (AttributeError, TypeError) as error:
            # Fallback if scroll_to not available
            logger.debug("Viewport scroll restoration unavailable", exc_info=error)

        self.canvas.refresh(layout=True)

    def action_attributes(self) -> None:
        """Show dialog to set the image attributes."""
        self.close_windows("#attributes_dialog")

        def handle_button(button: Button) -> None:
            if button.has_class("ok"):
                try:
                    width = int(window.content.query_one("#width_input", Input).value)
                    height = int(window.content.query_one("#height_input", Input).value)
                    if width < 1 or height < 1:
                        raise ValueError

                    self.resize_document(width, height)
                    window.close()

                except ValueError:
                    self.message_box(
                        _("Attributes"), _("Please enter a positive integer."), "ok"
                    )
            else:
                window.close()

        window = DialogWindow(
            id="attributes_dialog",
            title=_("Attributes"),
            handle_button=handle_button,
        )
        window.content.mount(
            Vertical(
                Horizontal(
                    Static(_("Width:")),
                    Input(
                        id="width_input",
                        value=str(self.image.width),
                        classes="autofocus",
                    ),
                ),
                Horizontal(
                    Static(_("Height:")),
                    Input(id="height_input", value=str(self.image.height)),
                ),
            ),
            Container(
                Button(_("OK"), classes="ok submit", variant="primary"),
                Button(_("Cancel"), classes="cancel"),
                classes="buttons",
            ),
        )
        self.mount(window)

    def action_clear_image(self) -> None:
        """Clear the image, creating an undo state."""
        self.cancel_preview()
        # Create undo state (full update for clear)
        self._create_undo_state(
            _("Clear Image"),
            self._get_full_region(),
            is_full_update=True,
        )

        self.image.clear()

        self.canvas.refresh()

    def action_draw_opaque(self) -> None:
        """Toggle opaque/transparent selection mode."""
        self.selection_opaque = not self.selection_opaque
        if self.image.selection:
            self.canvas.refresh()

    def action_help_topics(self) -> None:
        """Show the Help Topics dialog."""
        self.close_windows("#help_dialog")
        # "Paint Help" is the title in MS Paint,
        # but we don't have translations for that.
        # This works in English, but probably sounds weird in other languages.
        title = _("Paint") + " " + _("Help")

        title = get_help_icon_markup() + " " + title

        def handle_button(button: Button) -> None:
            window.close()

        window = DialogWindow(
            id="help_dialog",
            title=title,
            handle_button=handle_button,
            allow_maximize=True,
            allow_minimize=True,
        )
        help_text = get_help_text()
        window.content.mount(
            Container(Static(help_text, markup=False), classes="help_text_container")
        )
        window.content.mount(Button(_("OK"), classes="ok submit"))
        self.mount(window)

    def action_about_paint(self) -> None:
        """Show the About Paint dialog."""
        self.close_windows("#about_paint_dialog")
        message = Static(
            f"""[b]AuraPaint[/b]

[i]Arte ANSI nativa da AuraCli para o terminal.[/i]

[b]Version:[/b] {__version__}
[b]Maintainer:[/b] AuraCli
[b]License:[/b] MIT (with upstream Textual Paint attribution)
[b]Status:[/b] Bounded context nativo da AuraCli
"""
        )

        def handle_button(button: Button) -> None:
            window.close()

        window = MessageBox(
            id="about_paint_dialog",
            title=_("About AuraPaint"),
            handle_button=handle_button,
            icon_widget=get_paint_icon(),
            message=message,
        )
        self.mount(window)

    def action_toggle_inspector(self) -> None:
        """Toggle the DOM inspector."""
        if not args.inspect_layout:
            return
        # importing the inspector adds instrumentation which can slow down startup
        from .inspector import Inspector

        inspector = self.query_one(Inspector)
        inspector.display = not inspector.display
        if not inspector.display:
            inspector.picking = False

    def compose(self) -> ComposeResult:
        """Add our widgets."""
        from .ui.compose import create_compose

        yield from create_compose(self)

    def on_mount(self) -> None:
        """Called when the app is mounted."""
        # Image can be set from the outside, via CLI
        if not self.image_initialized:
            self.image = AnsiArtDocument(80, 24)
            self.image_initialized = True
        self.canvas = self.query_one("#canvas", Canvas)
        self.canvas.image = self.image
        self.editing_area = self.query_one("#editing_area", Container)
        self.query_one(HeaderIcon).icon = header_icon_text  # type: ignore

        # NEW: Initialize layer stack
        self.layer_stack = LayerStack(width=self.image.width, height=self.image.height)
        self.canvas.layer_stack = self.layer_stack  # NEW: Pass layer_stack to canvas

        # NEW: Sync initial document content to first layer
        if self.layer_stack.active_layer:
            self._sync_document_to_layer(self.layer_stack.active_layer.id)

        layer_panel = self.query_one("#layer_panel", LayerManagementPanel)
        layer_panel.refresh_layers(self.layer_stack)

        # Cursor blinking is now handled in Canvas for better encapsulation
        # Canvas manages its own cursor_visible reactive property
        self.canvas.cursor_visible = True

    def toggle_cursor_visible(self) -> None:
        """Toggle cursor visibility (delegates to Canvas)."""
        self.canvas.cursor_visible = not self.canvas.cursor_visible
        """Toggle visibility of the cursor for the purposes of 'cursor blink'."""
        self.cursor_visible = not self.cursor_visible

    def watch_cursor_visible(self) -> None:
        """When the cursor visibility is toggled, ensure the row is refreshed."""
        if self.image.selection is not None and self.image.selection.textbox_mode:
            self.canvas.cursor_visible = self.cursor_visible
            # More granular refresh: only refresh the cursor cell for textbox
            # Use text_selection_start as cursor position
            if self.image.selection.text_selection_start is not None:
                cursor_pos = self.image.selection.text_selection_start
                # Refresh only the cursor cell (1x1 region) relative to selection
                abs_x = self.image.selection.region.x + cursor_pos.x
                abs_y = self.image.selection.region.y + cursor_pos.y
                cursor_region = Region(abs_x, abs_y, 1, 1)
                self.canvas.refresh_scaled_region(cursor_region)
            else:
                # Fallback to full region if cursor position not available
                self.canvas.refresh_scaled_region(self.image.selection.region)

    def restart_cursor_blink_cycle(self) -> None:
        """Restart the cursor blink cycle (delegates to Canvas)."""
        self.canvas.cursor_visible = True
        if self.cursor_blink_timer:
            self.cursor_blink_timer.reset()

    # NEW: Layer synchronization methods
    def _sync_document_to_layer(self, layer_id: str) -> None:
        """Copy current document content to specified layer."""
        if self.layer_stack:
            self.layer_stack.store_document(layer_id, self.image)

    def _sync_layer_to_document(self, layer_id: str) -> None:
        """Copy layer content to current document."""
        if not self.layer_stack:
            return

        if self.layer_stack.load_document(layer_id, self.image):
            self.canvas.refresh()

    # NEW: Layer Management Panel Handlers
    def on_layer_management_panel_layer_added(
        self, message: LayerManagementPanel.LayerAdded
    ) -> None:
        """Handle layer added event."""
        if self.layer_stack:
            action = self._create_undo_state("Add Layer", is_full_update=True)
            action.update_layer_state(self.layer_stack)

            self.layer_stack.add_layer(f"Layer {self.layer_stack.layer_count + 1}")
            layer_panel = self.query_one("#layer_panel", LayerManagementPanel)
            layer_panel.refresh_layers(self.layer_stack)

    def on_layer_management_panel_layer_deleted(
        self, message: LayerManagementPanel.LayerDeleted
    ) -> None:
        """Handle layer deleted event."""
        if self.layer_stack and self.layer_stack.remove_layer(message.layer_id):
            action = self._create_undo_state("Delete Layer", is_full_update=True)
            action.update_layer_state(self.layer_stack)

            layer_panel = self.query_one("#layer_panel", LayerManagementPanel)
            layer_panel.refresh_layers(self.layer_stack)

    def on_layer_management_panel_layer_moved(
        self, message: LayerManagementPanel.LayerMoved
    ) -> None:
        """Handle layer moved event."""
        if not self.layer_stack:
            return

        action = self._create_undo_state("Move Layer", is_full_update=True)
        action.update_layer_state(self.layer_stack)

        if message.direction > 0:
            self.layer_stack.move_layer_up(message.layer_id)
        else:
            self.layer_stack.move_layer_down(message.layer_id)
        layer_panel = self.query_one("#layer_panel", LayerManagementPanel)
        layer_panel.refresh_layers(self.layer_stack)

    def on_layer_management_panel_layer_selected(
        self, message: LayerManagementPanel.LayerSelected
    ) -> None:
        """Handle layer selected event."""
        if not self.layer_stack:
            return

        old_active = self.layer_stack.active_layer
        if old_active:
            self._sync_document_to_layer(old_active.id)

        # Set new active layer
        self.layer_stack.set_active_layer(message.layer_id)

        # Load new active layer to document
        self._sync_layer_to_document(message.layer_id)

    def pick_color(self, x: int, y: int) -> None:
        """Select a color from the image."""
        sample = sample_document_cell(self.image, x, y)
        if sample is None:
            return
        self.selected_bg_color = sample.background
        self.selected_fg_color = sample.foreground
        self.selected_char = sample.character

    def get_document_coords_at_top_left_corner(self) -> Offset:
        """Returns the document coordinates of the top left corner of the viewport, clamped to the document."""
        return document_corner(
            scroll_offset=self.editing_area.scroll_offset,
            canvas_offset=self.canvas.virtual_region.offset,
            magnification=self.magnification,
            document_size=Size(self.image.width, self.image.height),
        )

    def get_prospective_magnification(self) -> int:
        """Returns the magnification result on click with the Magnifier tool."""
        return next_magnification(self.magnification, self.return_to_magnification)

    def magnifier_click(self, x: int, y: int) -> None:
        """Zooms in or out on the image."""

        transition = magnifier_transition(
            click=Offset(x, y),
            viewport_size=self.editing_area.size,
            current_magnification=self.magnification,
            return_magnification=self.return_to_magnification,
        )

        # Fix flickering by using batch_update
        with self.batch_update():
            self.magnification = transition.magnification
            self.canvas.magnification = self.magnification

        if transition.scroll_target is not None:
            self.editing_area.scroll_to(
                *transition.scroll_target,
                animate=False,
            )
            # `scroll_to` uses `call_after_refresh`.
            # `_scroll_to` is the same thing but without call_after_refresh.
            # But it doesn't work correctly, because the layout isn't updated yet.
            # And if I call:
            # self.screen._refresh_layout()
            # beforehand, it's back to the flickering.
            # I also tried calling:
            # self.editing_area.refresh(layout=True, repaint=False)
            # But it's back to the incorrect scroll position.
            # self.editing_area._scroll_to(
            #     (x - w / 2) * self.magnification / prev_magnification,
            #     (y - h / 2) * self.magnification / prev_magnification,
            #     animate=False,
            # )

    def extract_to_selection(self, erase_underlying: bool = True) -> None:
        """Extracts image data underlying the selection from the document into the selection.

        This creates an undo state with the current tool's name, which should be Select or Free-Form Select.
        """
        sel = self.image.selection
        assert sel is not None, "extract_to_selection called without a selection"
        assert sel.contained_image is None, (
            "extract_to_selection called after a selection was already extracted"
        )
        # Create undo state
        action = self._create_undo_state(self.selected_tool.get_name())
        sel.copy_from_document(self.image)
        if erase_underlying:
            self.erase_region(sel.region, sel.mask)

        # Optimize the region storage for Text, Select, and Free-Form Select tools
        # This is the intended behavior, in that it allows the user to undo the
        # selection and any changes to it as one action. But it's not efficient for large images.
        # Optimization: Use union of selection region and previous action region when melding
        # For now, we use full canvas region to ensure correctness, but this could be optimized
        # by tracking the union of regions during melding operations.
        affected_region = self._get_full_region()

        # Update action with actual affected region
        action.region = affected_region.intersection(self._get_full_region())
        # Re-capture the region since it may have changed
        action.update(self.image_at_start)
        self.canvas.refresh_scaled_region(affected_region)

    def on_canvas_tool_start(self, event: Canvas.ToolStart) -> None:
        """Called when the user starts drawing on the canvas."""
        event.stop()
        self.cancel_preview()

        self.mouse_gesture_cancelled = False

        if self.selected_tool == Tool.pick_color:
            self.pick_color(event.x, event.y)
            return

        if self.selected_tool == Tool.magnifier:
            self.magnifier_click(event.x, event.y)
            return

        self.mouse_at_start = Offset(event.x, event.y)
        self.mouse_previous = self.mouse_at_start
        self.color_eraser_mode = self.selected_tool == Tool.eraser and event.button == 3

        if self.selected_tool in [Tool.curve, Tool.polygon]:
            self.tool_points.append(Offset(event.x, event.y))
            if self.selected_tool == Tool.curve:
                self.make_preview(self.draw_current_curve)
            else:
                # polyline until finished
                self.make_preview(
                    self.draw_current_polyline, show_dimensions_in_status_bar=True
                )
            return

        if self.selected_tool == Tool.free_form_select:
            self.tool_points = [Offset(event.x, event.y)]

        if self.selected_tool in [Tool.select, Tool.free_form_select, Tool.text]:
            sel = self.image.selection
            if sel and sel.region.contains_point(self.mouse_at_start):
                if self.selected_tool == Tool.text:
                    # Place cursor at mouse position
                    offset_in_textbox = Offset(*self.mouse_at_start) - sel.region.offset
                    # clamping isn't needed here, unlike while dragging
                    sel.text_selection_start = offset_in_textbox
                    sel.text_selection_end = offset_in_textbox
                    self.canvas.refresh_scaled_region(sel.region)
                    self.selecting_text = True
                    return
                # Start dragging the selection.
                self.selection_drag_offset = Offset(
                    sel.region.x - self.mouse_at_start.x,
                    sel.region.y - self.mouse_at_start.y,
                )
                if sel.contained_image:
                    # Already cut out, don't replace the image data.
                    if event.ctrl:
                        # If pasted, it needs an undo state.
                        # Otherwise, one should have been already created.
                        if sel.pasted:
                            # Flag renamed for clarity: pasted indicates paste operation needs undo
                            sel.pasted = False  # don't create undo when melding again

                            action = self._create_undo_state("Paste")
                            # The region must be the whole canvas, because when the selection
                            # is melded with the canvas, it could be anywhere.
                            # This could be optimized, see extract_to_selection.
                            action.region = Region(
                                0, 0, self.image.width, self.image.height
                            )
                            action.update(self.image)
                        sel.copy_to_document(
                            self.image, transparent=not self.selection_opaque
                        )
                        # Don't need to refresh canvas since selection occludes the affected region,
                        # and has the same content anyway, being a stamp.
                    return
                self.extract_to_selection(not event.ctrl)
                return
            self.meld_selection()
            return

        action = self._create_undo_state(self.selected_tool.get_name())

        affected_region = None
        if self.selected_tool == Tool.pencil or self.selected_tool == Tool.brush:
            affected_region = self.stamp_brush(event.x, event.y)
        elif self.selected_tool == Tool.fill:
            affected_region = flood_fill(
                self.image,
                event.x,
                event.y,
                self.selected_char,
                self.selected_fg_color,
                self.selected_bg_color,
            )

        if affected_region:
            action.region = affected_region
            action.region = action.region.intersection(self._get_full_region())
            action.update(self.image_at_start)
            self.canvas.refresh_scaled_region(affected_region)
        else:
            # Flood fill didn't affect anything.
            # Following MS Paint, we still created an undo action.
            # We need a region to avoid an error/warning when undoing.
            # But we don't need to refresh the canvas.
            action.region = Region(0, 0, 0, 0)

    def cancel_preview(self) -> None:
        """Revert the currently previewed action."""
        if self.preview_action:
            assert self.preview_action.region is not None, (
                "region should have been initialized for preview_action"
            )
            self.preview_action.undo(self.image)
            self.canvas.refresh_scaled_region(self.preview_action.region)
            self.preview_action = None
        if self.canvas.magnifier_preview_region:
            region = self.canvas.magnifier_preview_region
            self.canvas.magnifier_preview_region = None
            self.canvas.refresh_scaled_region(region)
        if self.canvas.select_preview_region:
            region = self.canvas.select_preview_region
            self.canvas.select_preview_region = None
            self.canvas.refresh_scaled_region(region)

        # To avoid saving with a tool preview as part of the image data,
        # or interrupting the user's flow by canceling the preview occasionally to auto-save a backup,
        # we postpone auto-saving the backup until the image is clean of any previews.
        if self.save_backup_after_cancel_preview:
            self.save_backup()
            self.save_backup_after_cancel_preview = False

    def image_has_preview(self) -> bool:
        """Return whether the image data contains a tool preview. The document should not be saved in this state."""
        return self.preview_action is not None
        # Regarding self.canvas.magnifier_preview_region, self.canvas.select_preview_region:
        # These previews are not stored in the image data, so they don't count.

    def make_preview(
        self,
        draw_proc: Callable[[], Region],
        show_dimensions_in_status_bar: bool = False,
    ) -> None:
        """Preview the result of a draw operation, using a temporary action. Optionally preview dimensions in status bar."""
        self.cancel_preview()
        image_before = AnsiArtDocument(self.image.width, self.image.height)
        image_before.copy_region(self.image)
        affected_region = draw_proc()
        if affected_region:
            self.preview_action = Action(self.selected_tool.get_name())
            self.preview_action.region = affected_region.intersection(
                self._get_full_region()
            )
            self.preview_action.update(image_before)
            self.canvas.refresh_scaled_region(affected_region)
            if show_dimensions_in_status_bar:
                self.get_widget_by_id("status_dimensions", Static).update(
                    f"{self.preview_action.region.width}x{self.preview_action.region.height}"
                )

    def on_canvas_tool_preview_update(self, event: Canvas.ToolPreviewUpdate) -> None:
        """Called when the user is hovering over the canvas but not drawing yet."""
        event.stop()

        self.get_widget_by_id("status_coords", Static).update(f"{event.x},{event.y}")

        self.draw_tool_preview_on_canvas(Offset(event.x, event.y))

    def draw_tool_preview_on_canvas(self, mouse: Offset | None = None) -> None:
        """Update the tool preview on the canvas, if applicable."""
        self.cancel_preview()

        if self.selected_tool in [
            Tool.brush,
            Tool.pencil,
            Tool.eraser,
            Tool.curve,
            Tool.polygon,
        ]:
            if self.selected_tool == Tool.curve:
                self.make_preview(self.draw_current_curve)
            elif self.selected_tool == Tool.polygon:
                # polyline until finished
                self.make_preview(
                    self.draw_current_polyline, show_dimensions_in_status_bar=True
                )
            elif mouse is not None:
                self.make_preview(lambda: self.stamp_brush(mouse.x, mouse.y))
        elif self.selected_tool == Tool.magnifier and mouse is not None:
            prospective_magnification = self.get_prospective_magnification()

            if prospective_magnification < self.magnification:
                return  # hide if clicking would zoom out

            # prospective viewport size in document coords
            w = self.editing_area.size.width // prospective_magnification
            h = self.editing_area.size.height // prospective_magnification

            rect_x1 = mouse.x - w // 2
            rect_y1 = mouse.y - h // 2

            # try to move rect into bounds without squishing
            rect_x1 = max(0, rect_x1)
            rect_y1 = max(0, rect_y1)
            rect_x1 = min(self.image.width - w, rect_x1)
            rect_y1 = min(self.image.height - h, rect_y1)

            rect_x2 = rect_x1 + w
            rect_y2 = rect_y1 + h

            # clamp rect to bounds (with squishing)
            rect_x1 = max(0, rect_x1)
            rect_y1 = max(0, rect_y1)
            rect_x2 = min(self.image.width, rect_x2)
            rect_y2 = min(self.image.height, rect_y2)

            rect_w = rect_x2 - rect_x1
            rect_h = rect_y2 - rect_y1
            rect_x = rect_x1
            rect_y = rect_y1

            self.canvas.magnifier_preview_region = Region(
                rect_x, rect_y, rect_w, rect_h
            )
            self.canvas.refresh_scaled_region(self.canvas.magnifier_preview_region)

    def on_canvas_tool_preview_stop(self, event: Canvas.ToolPreviewStop) -> None:
        """Called when the user stops hovering over the canvas (while previewing, not drawing)."""
        event.stop()
        # Curve and Polygon persist when the mouse leaves the canvas,
        # since they're more stateful in their UI. It's confusing if
        # what you started drawing disappears.
        # Other tools should hide their preview, since they only preview
        # what will happen if you click on the canvas.
        if self.selected_tool not in [Tool.curve, Tool.polygon]:
            self.cancel_preview()
        self.get_widget_by_id("status_coords", Static).update("")

    def get_select_region(self, start: Offset, end: Offset) -> Region:
        """Returns the minimum region that contains the cells at the start and end offsets."""
        # Region.from_corners requires the first point to be the top left,
        # and it doesn't ensure the width and height are non-zero, so it doesn't work here.
        # We want to treat the inputs as cells, not points,
        # so we need to add 1 to the bottom/right.
        x1, y1 = start
        x2, y2 = end
        x1, x2 = min(x1, x2), max(x1, x2)
        y1, y2 = min(y1, y2), max(y1, y2)
        region = Region(x1, y1, x2 - x1 + 1, y2 - y1 + 1)
        # Clamp to the document bounds.
        return region.intersection(self._get_full_region())

    def meld_or_clear_selection(self, meld: bool) -> None:
        """Merges the selection into the image, or deletes it if meld is False."""
        if not self.image.selection:
            return

        if self.image.selection.textbox_mode:
            # The Text tool creates an undo state only when you switch tools
            # or click outside the textbox, melding the textbox into the image.
            # If you're deleting the textbox, an undo state doesn't need to be created.
            # even if you backspaced it all, to match MS Paint.
            if not self.image.selection.textbox_edited:
                meld = False

            make_undo_state = meld
        else:
            # Flag indicates whether an undo state should be created
            # True if: selection has no contained_image (needs extraction) OR was pasted
            make_undo_state = (
                self.image.selection.contained_image is None and not meld
            ) or self.image.selection.pasted

        if make_undo_state:
            # Create undo state using helper
            action = self._create_undo_state(self.selected_tool.get_name())

        region = self.image.selection.region
        if meld:
            self.image.selection.copy_to_document(
                self.image, transparent=not self.selection_opaque
            )
        else:
            if self.image.selection.contained_image is None:
                # It hasn't been cut out yet, so we need to erase it.
                self.erase_region(region, self.image.selection.mask)
        self.image.selection = None
        self.canvas.refresh_scaled_region(region)
        self.selection_drag_offset = None
        self.selecting_text = False

        if make_undo_state:
            # Update action with actual affected region
            action.region = region.intersection(self._get_full_region())
            # Re-capture the region since it may have changed
            action.update(self.image_at_start)
            self.canvas.refresh_scaled_region(region)

    def meld_selection(self) -> None:
        """Draw the selection onto the image and dissolve the selection."""
        self.meld_or_clear_selection(meld=True)

    def action_clear_selection(self, from_key_binding: bool = False) -> None:
        """Delete the selection and its contents, or if using the Text tool, delete text."""
        sel = self.image.selection
        if sel is None:
            return
        if sel.textbox_mode:
            if not from_key_binding:
                self.on_key(events.Key("delete", None))
        else:
            self.meld_or_clear_selection(meld=False)

    def _update_tool_status(self, event: "Canvas.ToolUpdate") -> None:
        """Update status bar coords/dimensions during tool drag."""
        if self.selected_tool != Tool.select:
            if self.selected_tool in [
                Tool.line,
                Tool.rectangle,
                Tool.ellipse,
                Tool.rounded_rectangle,
            ]:  # , Tool.curve
                # Display is allowed to go negative, unlike for the Select tool, handled below.
                # Also, Polygon gets both coords and dimensions.
                # Unlike MS Paint, Free-Form Select displays the dimensions of the resulting selection,
                # (rather than the difference between the mouse position and the starting point,)
                # which seems better to me.
                # Also, unlike MS Paint, Curve displays mouse coords rather than dimensions,
                # where "dimensions" are the difference between the mouse position and the starting point.
                # I don't know that this is better, but my mouse_at_start currently is set on mouse down for in-progress curves,
                # so it wouldn't match MS Paint unless I changed that or used the tool_points list.
                # I don't know that anyone looks at the status bar while drawing a curve.
                # If they do, they should probably be using a graphing calculator instead or something.
                self.get_widget_by_id("status_dimensions", Static).update(
                    f"{event.x - self.mouse_at_start.x}x{event.y - self.mouse_at_start.y}"
                )
            else:
                self.get_widget_by_id("status_coords", Static).update(
                    f"{event.x},{event.y}"
                )

    def _handle_select_drag(self, event: "Canvas.ToolUpdate") -> None:
        """Handle drag for select/free_form_select/text tools."""
        if self.selected_tool in [Tool.select, Tool.free_form_select, Tool.text]:
            sel = self.image.selection
            if self.selecting_text:
                assert sel is not None, (
                    "selecting_text should only be set if there's a selection"
                )
                offset_in_textbox = Offset(event.x, event.y) - sel.region.offset
                offset_in_textbox = Offset(
                    min(max(0, offset_in_textbox.x), sel.region.width - 1),
                    min(max(0, offset_in_textbox.y), sel.region.height - 1),
                )
                sel.text_selection_end = offset_in_textbox
                self.canvas.refresh_scaled_region(sel.region)
            elif self.selection_drag_offset is not None:
                assert sel is not None, (
                    "selection_drag_offset should only be set if there's a selection"
                )
                offset = (
                    self.selection_drag_offset.x + event.x,
                    self.selection_drag_offset.y + event.y,
                )
                # Handles constraints and canvas refresh.
                self.move_selection_absolute(*offset)
            elif self.selected_tool == Tool.free_form_select:
                self.tool_points.append(Offset(event.x, event.y))
                self.make_preview(
                    self.draw_current_free_form_select_polyline,
                    show_dimensions_in_status_bar=True,
                )
            else:
                self.canvas.select_preview_region = self.get_select_region(
                    self.mouse_at_start, Offset(event.x, event.y)
                )
                self.canvas.refresh_scaled_region(self.canvas.select_preview_region)
                self.get_widget_by_id("status_dimensions", Static).update(
                    f"{self.canvas.select_preview_region.width}x{self.canvas.select_preview_region.height}"
                )
            return

    def _handle_curve_polygon_drag(self, event: "Canvas.ToolUpdate") -> None:
        """Handle drag for curve/polygon tools."""
        if self.selected_tool in [Tool.curve, Tool.polygon]:
            if len(self.tool_points) < 2:
                self.tool_points.append(Offset(event.x, event.y))
            self.tool_points[-1] = Offset(event.x, event.y)

            if self.selected_tool == Tool.curve:
                self.make_preview(self.draw_current_curve)
            elif self.selected_tool == Tool.polygon:
                # polyline until finished
                self.make_preview(
                    self.draw_current_polyline, show_dimensions_in_status_bar=True
                )
            return

    def _apply_draw_tool(
        self,
        event: "Canvas.ToolUpdate",
        action: "Action",
        affected_region: "Optional[Region]",
    ) -> "Optional[Region]":
        """Dispatch to the correct draw tool and return the affected region."""
        if self.selected_tool in [Tool.pencil, Tool.brush, Tool.eraser, Tool.airbrush]:
            affected_region = self._draw_point_tool(
                self.mouse_previous, Offset(event.x, event.y), affected_region
            )
        elif self.selected_tool == Tool.line:
            affected_region = self._draw_line_tool(
                self.mouse_at_start, Offset(event.x, event.y), affected_region
            )
        elif self.selected_tool == Tool.rectangle:
            affected_region = self._draw_rectangle_tool(
                self.mouse_at_start, Offset(event.x, event.y), affected_region
            )
        elif self.selected_tool == Tool.rounded_rectangle:
            affected_region = self._draw_rounded_rectangle_tool(
                self.mouse_at_start, Offset(event.x, event.y), affected_region
            )
        elif self.selected_tool == Tool.ellipse:
            affected_region = self._draw_ellipse_tool(
                self.mouse_at_start, Offset(event.x, event.y), affected_region
            )
        else:
            import logging as _log

            _log.getLogger(__name__).debug(
                f"Ferramenta não implementada no loop de desenho: {self.selected_tool}"
            )

    def on_canvas_tool_update(self, event: Canvas.ToolUpdate) -> None:
        """Called when the user is drawing on the canvas.

        Several tools do a preview of sorts here, even though it's not the ToolPreviewUpdate event.
        # Note: These events describe when they occur (mouse up after drag),
        # rather than what action they perform, to keep semantics flexible.
        """
        event.stop()
        self.cancel_preview()

        if self.mouse_gesture_cancelled:
            return

        self._update_tool_status(event)

        if self.selected_tool == Tool.pick_color:
            self.pick_color(event.x, event.y)
            return

        if self.selected_tool in [Tool.fill, Tool.magnifier]:
            return

        if self.selected_tool in [Tool.select, Tool.free_form_select, Tool.text]:
            self._handle_select_drag(event)
            return
        if self.selected_tool in [Tool.curve, Tool.polygon]:
            self._handle_curve_polygon_drag(event)
            return
        # The remaining tools work by updating an undo state created on mouse down.
        assert len(self.undos) > 0, (
            "No undo state to update. The undo state should have been created in on_canvas_tool_start, or if the gesture was canceled, execution shouldn't reach here."
        )

        action = self.undos[-1]
        affected_region = None

        replace_action = self.selected_tool in [
            Tool.ellipse,
            Tool.rectangle,
            Tool.line,
            Tool.rounded_rectangle,
        ]
        old_action: Optional[Action] = None  # avoid "possibly unbound"
        if replace_action:
            old_action = self.undos.pop()
            old_action.undo(self.image)
            action = Action(self.selected_tool.get_name(), affected_region)
            self.undos.append(action)

        affected_region = self._apply_draw_tool(event, action, affected_region)

        # Update action region and image data
        if action.region and affected_region:
            action.region = action.region.union(affected_region)
        elif affected_region:
            action.region = affected_region
        if action.region:
            action.region = action.region.intersection(self._get_full_region())
            action.update(self.image_at_start)

        # Only for refreshing, include replaced action region
        # (The new action is allowed to shrink the region compared to the old one)
        if affected_region:
            if replace_action:
                assert old_action is not None, (
                    "old_action should have been set if replace_action is True"
                )
                affected_region = affected_region.union(old_action.region)
            self.canvas.refresh_scaled_region(affected_region)

        self.mouse_previous = Offset(event.x, event.y)

    def on_canvas_tool_stop(self, event: Canvas.ToolStop) -> None:
        """Called when releasing the mouse button after drawing/dragging on the canvas."""
        # Clear the selection preview in case the mouse has moved.
        # (I don't know of any guarantee that it won't.)
        self.cancel_preview()

        self.get_widget_by_id("status_dimensions", Static).update("")

        self.color_eraser_mode = False  # reset for preview

        if self.mouse_gesture_cancelled:
            return

        if self.selection_drag_offset is not None:
            # Done dragging selection
            self.selection_drag_offset = None
            # Refresh to show border, which is hidden while dragging
            assert self.image.selection is not None, (
                "Dragging selection without selection"
            )
            self.canvas.refresh_scaled_region(self.image.selection.region)
            return
        if self.selecting_text:
            # Done selecting text
            self.selecting_text = False
            return

        assert self.mouse_at_start is not None, (
            "mouse_at_start should be set on mouse down"
        )
        if self.selected_tool in [Tool.select, Tool.free_form_select, Tool.text]:
            # Finish making a selection
            if self.selected_tool == Tool.free_form_select:
                # Find bounds of the polygon
                min_x = min(p.x for p in self.tool_points)
                max_x = max(p.x for p in self.tool_points)
                min_y = min(p.y for p in self.tool_points)
                max_y = max(p.y for p in self.tool_points)
                select_region = Region(
                    min_x, min_y, max_x - min_x + 1, max_y - min_y + 1
                )
                select_region = select_region.intersection(self._get_full_region())
            else:
                select_region = self.get_select_region(
                    self.mouse_at_start, Offset(event.x, event.y)
                )
            if self.image.selection:
                # This shouldn't happen, because it should meld
                # the selection on mouse down.
                self.meld_selection()
            self.image.selection = Selection(select_region)
            self.image.selection.textbox_mode = self.selected_tool == Tool.text
            if self.image.selection.textbox_mode:
                free_typing_mode = (
                    select_region.width == 1 and select_region.height == 1
                )
                if free_typing_mode:
                    # self.extract_to_selection(erase_underlying=False)
                    self.image.selection.copy_from_document(self.image)
                    self.image.selection.cursor_mode = True
                else:
                    self.image.selection.contained_image = AnsiArtDocument(
                        self.image.selection.region.width,
                        self.image.selection.region.height,
                        default_fg=self.selected_fg_color,
                        default_bg=self.selected_bg_color,
                    )
            if self.selected_tool == Tool.free_form_select:
                # Define the mask for the selection using the polygon
                self.image.selection.mask = [
                    [
                        is_inside_polygon(
                            x + select_region.x, y + select_region.y, self.tool_points
                        )
                        for x in range(select_region.width)
                    ]
                    for y in range(select_region.height)
                ]
            self.canvas.refresh_scaled_region(select_region)
        elif self.selected_tool == Tool.curve:
            # Maybe finish drawing a curve
            if len(self.tool_points) >= 4:
                self.finalize_polygon_or_curve()
            else:
                # Most likely just drawing the preview we just cancelled.
                self.make_preview(self.draw_current_curve)
        elif self.selected_tool == Tool.polygon:
            # Maybe finish drawing a polygon

            # Check if the distance between the first and last point is small enough,
            # or if the user double-clicked.
            close_gap_threshold_cells = 2
            double_click_threshold_seconds = 0.5
            double_click_threshold_cells = 2
            time_since_last_click = event.time - self.polygon_last_click_time
            enough_points = len(self.tool_points) >= 3
            closed_gap = (
                abs(self.tool_points[0].x - event.x) <= close_gap_threshold_cells
                and abs(self.tool_points[0].y - event.y) <= close_gap_threshold_cells
            )

            double_clicked = (
                time_since_last_click < double_click_threshold_seconds
                and
                # Distance during second click (from press to release)
                abs(self.mouse_at_start.x - event.x) <= double_click_threshold_cells
                and abs(self.mouse_at_start.y - event.y) <= double_click_threshold_cells
                and
                # Distance between first and second clicks
                # Use distance between first mouse down and current mouse up for double-click detection
                # This provides more accurate detection than using second mouse down
                len(self.tool_points) >= 2
                and abs(self.tool_points[-2].x - event.x)
                <= double_click_threshold_cells
                and abs(self.tool_points[-2].y - event.y)
                <= double_click_threshold_cells
            )
            if enough_points and (closed_gap or double_clicked):
                self.finalize_polygon_or_curve()
            else:
                # Most likely just drawing the preview we just cancelled.
                self.make_preview(
                    self.draw_current_polyline, show_dimensions_in_status_bar=True
                )  # polyline until finished

            self.polygon_last_click_time = event.time
        elif self.selected_tool in [Tool.pick_color, Tool.magnifier]:
            self.selected_tool = self.return_to_tool

        # Not reliably unset, so might as well not rely on it. (See early returns above.)
        # self.mouse_at_start = None

    def move_selection_absolute(self, x: int, y: int) -> None:
        """Positions the selection relative to the document."""
        # Constrain to have at least one row/column within the bounds of the document.
        sel = self.image.selection
        assert sel is not None, "move_selection_absolute called without a selection"
        if sel.contained_image is None:
            self.extract_to_selection()
        offset = Offset(
            max(1 - sel.region.width, min(self.image.width - 1, x)),
            max(1 - sel.region.height, min(self.image.height - 1, y)),
        )
        old_region = sel.region
        sel.region = Region.from_offset(offset, sel.region.size)
        combined_region = old_region.union(sel.region)
        self.canvas.refresh_scaled_region(combined_region)
        # Don't scroll the selection into view, because it's problematic with large selections.
        # self.editing_area.scroll_to_region(Region(
        #     sel.region.x * self.magnification + self.canvas.styles.margin.left,
        #     sel.region.y * self.magnification + self.canvas.styles.margin.top,
        #     sel.region.width * self.magnification,
        #     sel.region.height * self.magnification,
        # ), animate=False)

    def move_selection_relative(self, delta_x: int, delta_y: int) -> None:
        """Moves the selection relative to its current position."""
        sel = self.image.selection
        assert sel is not None, "move_selection_relative called without a selection"
        self.move_selection_absolute(
            sel.region.offset.x + delta_x, sel.region.offset.y + delta_y
        )

    def _handle_create_text_cursor(self, key: str, event: "events.Key") -> None:
        """Create initial text cursor when no selection exists."""
        if not self.image.selection and key in TEXT_CURSOR_KEYS:
            # Switch to the Text tool
            self.selected_tool = Tool.text
            # Ensure focus is not on the CharInput
            self.app.set_focus(None)
            # Create an initial cursor, at top left corner of viewport
            self.image.selection = Selection(
                Region.from_offset(
                    self.get_document_coords_at_top_left_corner(), (1, 1)
                )
            )
            self.image.selection.textbox_mode = True
            self.image.selection.cursor_mode = True
            self.image.selection.copy_from_document(self.image)
            # Avoid returning for home/end/pageup/pagedown to allow the cursor to start in different places.
            # This would be weird for arrow keys, unless perhaps it started from the side opposite the arrow direction,
            # which would make it so that repeating the key would always do something.
            # There's also an argument for always starting at the top left, for consistency.
            if key not in ["home", "end", "pageup", "pagedown"]:
                self.canvas.refresh_scaled_region(self.image.selection.region)
                return

    def _handle_selection_move_key(self, key: str, event: "events.Key") -> None:
        """Move selection with arrow keys (smear if shift held)."""
        if self.image.selection and not self.image.selection.textbox_mode:
            # Smear selection if shift is held (duplicate while moving)
            if key == "left":
                if event.shift:
                    # Smear: duplicate selection while moving
                    self.image.selection.copy_to_document(
                        self.image, transparent=not self.selection_opaque
                    )
                self.move_selection_relative(-1, 0)
            elif key == "right":
                if event.shift:
                    # Smear: duplicate selection while moving
                    self.image.selection.copy_to_document(
                        self.image, transparent=not self.selection_opaque
                    )
                self.move_selection_relative(1, 0)
            elif key == "up":
                if event.shift:
                    # Smear: duplicate selection while moving
                    self.image.selection.copy_to_document(
                        self.image, transparent=not self.selection_opaque
                    )
                self.move_selection_relative(0, -1)
            elif key == "down":
                if event.shift:
                    # Smear: duplicate selection while moving
                    self.image.selection.copy_to_document(
                        self.image, transparent=not self.selection_opaque
                    )
                self.move_selection_relative(0, 1)

    def _handle_textbox_edit_key(
        self,
        key: str,
        event: "events.Key",
        textbox: "Selection",
        image: "AnsiArtDocument",
        x: int,
        y: int,
    ) -> "tuple[int, int]":
        """Handle backspace/delete/printable in textbox. Returns new (x, y)."""
        w, h = image.width, image.height
        if key == "backspace":
            if textbox.text_selection_end == textbox.text_selection_start:
                x = max(0, x - 1)
                # Undoable even in textbox (for free-typing mode)
                if image == self.image:
                    action = self._create_undo_state(
                        _("Backspace Character"), Region(x, y, 1, 1)
                    )
                    action.cursor_position_before = Offset(x, y)
                image.ch[y][x] = " "
            else:
                self._delete_selected_text(textbox)
                x, y = textbox.text_selection_end
            textbox.textbox_edited = True
        elif key == "delete":
            if textbox.text_selection_end == textbox.text_selection_start:
                # Undoable even in textbox (for free-typing mode)
                if image == self.image:
                    action = self._create_undo_state(
                        _("Delete Character"), Region(x, y, 1, 1)
                    )
                    action.cursor_position_before = Offset(x, y)
                image.ch[y][x] = " "
                x = min(w - 1, x + 1)
            else:
                self._delete_selected_text(textbox)
                x, y = textbox.text_selection_end
            textbox.textbox_edited = True
        elif key == "home":
            x = 0
        elif key == "end":
            x = w - 1
        elif key == "pageup":
            y = 0
        elif key == "pagedown":
            y = h - 1
        elif event.is_printable:
            assert event.character is not None, (
                "is_printable should imply character is not None"
            )
            # Type a character into the textbox or document.

            # Undoable even in textbox (for free-typing mode)
            if image == self.image:
                action = self._create_undo_state(
                    _("Type Character"), Region(x, y, 1, 1)
                )
                action.cursor_position_before = Offset(x, y)
            image.ch[y][x] = event.character
            # x = min(w - 1, x + 1)
            x += 1
            if x >= w:
                x = 0
                # y = min(h - 1, y + 1)
                y += 1
                if y >= h:
                    y = h - 1
                    x = w - 1
            textbox.textbox_edited = True

        return x, y

    @staticmethod
    def _delete_selected_text(textbox: "Selection") -> None:
        """Delete selected textbox cells and collapse the cursor to its start."""
        assert textbox.contained_image is not None, (
            "Textbox mode should always have contained_image, to edit as text."
        )
        for offset in selected_text_range(textbox):
            textbox.contained_image.ch[offset.y][offset.x] = " "
        textbox.textbox_edited = True
        textbox.text_selection_end = textbox.text_selection_start = min(
            textbox.text_selection_start,
            textbox.text_selection_end,
        )

    def _move_textbox_cursor(
        self,
        key: str,
        event: "events.Key",
        textbox: "Selection",
        image: "AnsiArtDocument",
        x: int,
        y: int,
    ) -> "tuple[int, int]":
        """Move textbox cursor based on key. Returns new (x, y)."""
        w, h = image.width, image.height
        if key == "enter":
            x = 0
            y += 1
            if y >= h:
                y = h - 1
            # textbox.textbox_edited = True
        elif key == "left":
            x = max(0, x - 1)
        elif key == "right":
            x = min(w - 1, x + 1)
        elif key == "up":
            y = max(0, y - 1)
        elif key == "down":
            y = min(h - 1, y + 1)
        elif key in ("backspace", "delete") or event.is_printable:
            x, y = self._handle_textbox_edit_key(key, event, textbox, image, x, y)
            textbox.text_selection_end = Offset(x, y)
        else:
            textbox.text_selection_start = Offset(x, y)
            textbox.text_selection_end = Offset(x, y)

        return x, y

    def _handle_textbox_key(self, key: str, event: "events.Key") -> None:
        """Handle key input in textbox/cursor mode."""
        if self.image.selection and self.image.selection.textbox_mode:
            self.restart_cursor_blink_cycle()

            textbox = self.image.selection
            assert textbox.contained_image is not None, (
                "Textbox mode should always have contained_image, to edit as text."
            )

            free_typing_mode = textbox.cursor_mode

            # Delete selected text if any, when typing
            if (
                self.image.selection
                and self.image.selection.textbox_mode
                and self.image.selection.text_selection_start
                != self.image.selection.text_selection_end
            ):
                # Delete selected text before typing
                textbox = self.image.selection
                start = textbox.text_selection_start
                end = textbox.text_selection_end
                for y in range(start.y, end.y + 1):
                    x_start = start.x if y == start.y else 0
                    x_end = end.x if y == end.y else textbox.region.width - 1
                    for x in range(x_start, x_end + 1):
                        if textbox.contained_image:
                            textbox.contained_image.ch[y][x] = " "
                textbox.text_selection_end = textbox.text_selection_start

            # Whether or not shift is held, we start with the end point.
            # Then once we've moved this point, we update the end point,
            # and we update the start point unless shift is held.
            # This way, the cursor jumps to (near) the end point if you
            # hit an arrow key without shift, but with shift it will extend
            # the selection.
            x, y = textbox.text_selection_end
            image = textbox.contained_image
            # For free-typing mode, the AnsiArtDocument to be edited
            # is the whole canvas instead of the textbox, and x and y are relative to the canvas.
            if free_typing_mode:
                x, y = textbox.region.offset
                image = self.image
            _w, _h = image.width, image.height

            x, y = self._move_textbox_cursor(key, event, textbox, image, x, y)
            if free_typing_mode:
                select_region = Region(x, y, 1, 1)
                # Don't meld the textbox, since the document should already be modified, with undo states already created.
                # if textbox.textbox_edited:
                #     self.meld_selection()
                self.image.selection = Selection(select_region)
                self.image.selection.textbox_mode = True
                self.image.selection.cursor_mode = True
                # self.extract_to_selection(erase_underlying=False)
                self.image.selection.copy_from_document(self.image)
                self.canvas.refresh_scaled_region(select_region)

                # Prevent animation for small movements, but preserve it for page up/down and home/end
                # This improves UX by avoiding distracting animations for single-cell movements
                is_large_movement = key in ("pageup", "pagedown", "home", "end")
                scroll_region = Region(
                    x * self.magnification + self.canvas.styles.margin.left,
                    y * self.magnification + self.canvas.styles.margin.top,
                    self.magnification,
                    self.magnification,
                )
                # Use animate parameter if available, otherwise always animate
                try:
                    self.editing_area.scroll_to_region(
                        scroll_region, animate=is_large_movement
                    )
                except TypeError:
                    # Fallback if animate parameter not supported
                    self.editing_area.scroll_to_region(scroll_region)

            self.canvas.refresh_scaled_region(textbox.region)

    def on_key(self, event: events.Key) -> None:
        """Called when the user presses a key."""

        if len(self.screen_stack) > 1:  # type: ignore
            # Avoid error if command palette is open, and you press an arrow key,
            # thereby creating a cursor and switching to the Text tool.
            # (NoMatches: No nodes match <DOMQuery query='ToolsBox'>)
            return

        if self.focused is not None:
            # Avoid double-acting arrow keys when dialogs are open.
            return

        key = event.key
        shift = key.startswith("shift+")
        if shift:
            key = key[len("shift+") :]
        if "ctrl" in key:
            # Don't interfere with Ctrl+C, Ctrl+V, etc.
            # and don't double-handle Ctrl+F (View Bitmap)
            return
        if key == "escape":
            return

        if self.has_class("view_bitmap"):
            self.call_later(self.action_view_bitmap)
            return

        if not self.image.selection and key in TEXT_CURSOR_KEYS:
            self._handle_create_text_cursor(key, event)
            return
        if self.image.selection and not self.image.selection.textbox_mode:
            self._handle_selection_move_key(key, event)
        if self.image.selection and self.image.selection.textbox_mode:
            self._handle_textbox_key(key, event)

    def on_paste(self, event: events.Paste) -> None:
        """Called when a file is dropped into the terminal, or when text is pasted with middle click."""

        # Detect file drop
        def _extract_filepaths(text: str) -> List[str]:
            """Extracts escaped filepaths from text.

            Taken from https://github.com/agmmnn/textual-filedrop/blob/55a288df65d1397b959d55ef429e5282a0bb21ff/textual_filedrop/_filedrop.py#L17-L36
            """
            split_filepaths = []
            if os.name == "nt":
                pattern = r'(?:[^\s"]|"(?:\\"|[^"])*")+'
                split_filepaths = re.findall(pattern, text)
            else:
                split_filepaths = shlex.split(text)

            split_filepaths = shlex.split(text)
            filepaths: List[str] = []
            for i in split_filepaths:
                item = i.replace("\x00", "").replace('"', "")
                if os.path.isfile(item):
                    filepaths.append(i)
                # elif os.path.isdir(item):
                #     for root, _, files in os.walk(item):
                #         for file in files:
                #             filepaths.append(os.path.join(root, file))
            return filepaths

        try:
            filepaths = _extract_filepaths(event.text)
            if filepaths:
                file_path = filepaths[0]
                self.open_from_file_path(file_path, lambda: None)
                return
        except ValueError as error:
            logger.debug("Pasted text is not a valid shell path list", exc_info=error)

        # Text pasting is only supported with Ctrl+V or Edit > Paste, handled separately.
        return

    def action_toggle_tools_box(self) -> None:
        """Toggles the visibility of the tools box."""
        self.show_tools_box = not self.show_tools_box

    def action_toggle_colors_box(self) -> None:
        """Toggles the visibility of the colors box."""
        self.show_colors_box = not self.show_colors_box

    def action_toggle_status_bar(self) -> None:
        """Toggles the visibility of the status bar."""
        self.show_status_bar = not self.show_status_bar

    def on_tools_box_tool_selected(self, event: ToolsBox.ToolSelected) -> None:
        """Called when a tool is selected in the tools box."""
        self.finalize_polygon_or_curve()  # must come before setting selected_tool
        self.meld_selection()
        self.tool_points = []

        self.selected_tool = event.tool
        if self.selected_tool not in [Tool.magnifier, Tool.pick_color]:
            self.return_to_tool = self.selected_tool

    def on_char_input_char_selected(self, event: CharInput.CharSelected) -> None:
        """Called when a character is entered in the character input."""
        self.selected_char = event.char

    def on_colors_box_color_selected(self, event: ColorsBox.ColorSelected) -> None:
        """Called when a color well is clicked in the palette."""
        if event.as_foreground:
            self.selected_fg_color = event.color
        else:
            self.selected_bg_color = event.color

    def on_colors_box_edit_color(self, event: ColorsBox.EditColor) -> None:
        """Called when a color is double-clicked in the palette."""
        self.action_edit_colors(
            color_palette_index=event.color_index, as_foreground=event.as_foreground
        )

    def on_menu_status_info(self, event: Menu.StatusInfo) -> None:
        """Called when a menu item is hovered."""
        text: str = event.description or ""
        if event.closed:
            text = _("For Help, click Help Topics on the Help Menu.")
        self.get_widget_by_id("status_text", Static).update(text)

    def within_menus(self, node: DOMNode) -> bool:
        """Returns True if the node is within the menus."""
        # root node will never be a menu, so it doesn't need to be `while node:`
        # and this makes the type checker happy, since parent can be None
        while node.parent:
            if isinstance(node, Menu):
                return True
            node = node.parent
        return False

    def on_mouse_down(self, event: events.MouseDown) -> None:
        """Called when the mouse button gets pressed."""

        if len(self.screen_stack) > 1:  # type: ignore
            # Avoid error if clicking to close the command palette
            return

        leaf_widget, _ = self.get_widget_at(*event.screen_offset)

        # Close menus if clicking outside the menus
        if (
            not self.within_menus(leaf_widget)
            and self.query_one(MenuBar).any_menus_open()
        ):
            self.query_one(MenuBar).close()
            return
        # Exit View Bitmap mode if clicking anywhere
        if self.has_class("view_bitmap"):
            # Call later to avoid drawing on the canvas when exiting
            self.call_later(self.action_view_bitmap)

        # Deselect if clicking outside the canvas
        if leaf_widget is self.editing_area:
            self.meld_selection()
        # Unfocus if clicking on or outside the canvas,
        # so that you can type in the Text tool.
        # Otherwise the CharInput gets in the way.
        if leaf_widget is self.editing_area or leaf_widget is self.canvas:
            self.app.set_focus(None)

        # Dev helper to inspect layout by highlighting elements under the mouse
        if not args.inspect_layout:
            return
        # I didn't like it resetting on every click.
        if event.button != 2:
            return
        if hasattr(self, "debug_highlight"):
            for (
                element,
                original_color,
                original_border,
                original_border_title,
            ) in self.debug_highlight:
                element.styles.background = original_color
                element.styles.border = original_border
                element.border_title = original_border_title
        self.debug_highlight: List[
            Tuple[Widget, Color, BorderDefinition, Optional[str]]
        ] = []
        # leaf_widget, _ = self.get_widget_at(*event.screen_offset)
        if leaf_widget and leaf_widget is not self.screen:
            for i, widget in enumerate(leaf_widget.ancestors_with_self):
                self.debug_highlight.append(
                    (
                        widget,
                        widget.styles.background,
                        widget.styles.border,
                        widget.border_title
                        if hasattr(widget, "border_title")
                        else None,
                    )
                )  # type: ignore
                widget.styles.background = Color.from_hsl(i / 10, 1, 0.3)
                if not event.ctrl:
                    widget.styles.border = ("round", Color.from_hsl(i / 10, 1, 0.5))
                    widget.border_title = widget.css_identifier_styled  # type: ignore


# `textual run --dev src.textual_paint.paint` will search for a
# global variable named `app`, and fallback to
# anything that is an instance of `App`, or
# a subclass of `App`.
Paint = AuraPaint
"""Compatibility alias for integrations that still import ``Paint``."""

app = AuraPaint()

# Passive arguments
# (with the exception of making directories)

app.dark = args.theme == "dark"

if args.backup_folder:
    backup_folder = os.path.abspath(args.backup_folder)
    if not os.path.exists(backup_folder):
        os.makedirs(backup_folder)
    app.backup_folder = backup_folder


if args.restart_on_changes:
    restart_on_changes(app)

if args.filename:
    # if args.filename == "-" and not sys.stdin.isatty():
    #     app.image = AnsiArtDocument.from_text(sys.stdin.read())
    #     app.filename = "<stdin>"
    # else:
    if os.path.exists(args.filename):
        # This calls recover_from_backup().
        # This requires the canvas to exist, hence call_later().
        def open_file_from_cli_arg() -> None:
            app.open_from_file_path(os.path.abspath(args.filename), lambda: None)

        app.call_later(open_file_from_cli_arg)
    else:
        # Sometimes you just want to name a new file from the command line.
        app.file_path = os.path.abspath(args.filename)
        app.call_later(app.recover_from_backup)
else:
    # This requires the canvas to exist, hence call_later().
    app.call_later(app.recover_from_backup)

if args.clear_screen:
    import subprocess

    subprocess.run(["cls" if os.name == "nt" else "clear"], shell=False, check=False)

app.call_later(app.start_backup_interval)


def main() -> None:
    """Entry point for the AuraPaint CLI."""
    app.run()


if __name__ == "__main__":
    main()
