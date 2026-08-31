"""Edit Colors Dialog - Aura CLI Paint Tool

Color picker dialog with HSL/RGB controls and custom palette.

Features:
    - Basic and custom color grids
    - HSL color field with luminosity ramp
    - RGB/HSL numeric inputs
    - Live color preview
    - Keyboard navigation in color grids
    - ASCII-only mode support for markers
"""

from typing import Any, Callable, Dict, List

from rich.segment import Segment
from rich.style import Style
from textual import events
from textual.color import Color as Color
from textual.containers import Container, Horizontal, Vertical
from textual.css.query import NoMatches
from textual.geometry import Offset
from textual.message import Message
from textual.reactive import reactive, var
from textual.strip import Strip
from textual.widget import Widget
from textual.widgets import Button, Input, Label

from aura_cli.application.paint.localization.i18n import get as _
from aura_cli.application.paint.palette_data import AURA_WHITE, DEFAULT_PALETTE

from .args import args
from .windows import DialogWindow

# https://github.com/kouzhudong/win2k/blob/ce6323f76d5cd7d136b74427dad8f94ee4c389d2/trunk/private/shell/win16/comdlg/color.c#L38-L43
# These are a fallback in case colors are not received from some driver.
# const default_basic_colors = [
#     "#8080FF", "#80FFFF", "#80FF80", "#80FF00", "#FFFF80", "#FF8000", "#C080FF", "#FF80FF",
#     "#0000FF", "#00FFFF", "#00FF80", "#40FF00", "#FFFF00", "#C08000", "#C08080", "#FF00FF",
#     "#404080", "#4080FF", "#00FF00", "#808000", "#804000", "#FF8080", "#400080", "#8000FF",
#     "#000080", "#0080FF", "#008000", "#408000", "#FF0000", "#A00000", "#800080", "#FF0080",
#     "#000040", "#004080", "#004000", "#404000", "#800000", "#400000", "#400040", "#800040",
#     "#000000", "#008080", "#408080", "#808080", "#808040", "#C0C0C0", "#400040", "#FFFFFF",
# ];
# Grabbed with Color Cop from the screen with Windows 98 SE running in VMWare
basic_colors = list(DEFAULT_PALETTE)
custom_colors = [
    AURA_WHITE,
    AURA_WHITE,
    AURA_WHITE,
    AURA_WHITE,
    AURA_WHITE,
    AURA_WHITE,
    AURA_WHITE,
    AURA_WHITE,
    AURA_WHITE,
    AURA_WHITE,
    AURA_WHITE,
    AURA_WHITE,
    AURA_WHITE,
    AURA_WHITE,
    AURA_WHITE,
    AURA_WHITE,
]

num_colors_per_row = 8


class ColorGrid(Container):
    """Grid of selectable color swatches.

    Displays colors in a grid layout with keyboard navigation
    and selection tracking.

    Attributes:
        color_list: List of color strings to display
        selected_color: Currently selected color
        can_focus: Whether grid can receive keyboard focus
    """

    class Changed(Message):
        """Message posted when selected color changes.

        Attributes:
            color: Selected color string
            color_grid: ColorGrid instance that posted message
            index: Index of selected color in color_list
        """

        def __init__(self, color: str, color_grid: "ColorGrid", index: int) -> None:
            """Initialize Changed message.

            Args:
                color: Selected color string
                color_grid: ColorGrid instance
                index: Color index in list
            """
            super().__init__()
            self.color = color
            self.color_grid = color_grid
            self.index = index

    color_list: var[List[str]] = var(List[str], init=False)

    def __init__(
        self, color_list: List[str], selected_color: str, **kwargs: Any
    ) -> None:
        """Initialize ColorGrid.

        Args:
            color_list: List of color strings to display
            selected_color: Initially selected color
            **kwargs: Additional widget arguments
        """
        super().__init__(**kwargs)
        self.selected_color: str = selected_color
        self._color_by_button: Dict[Button, str] = {}
        self.color_list = color_list
        self.can_focus = True

    def on_mount(self) -> None:
        """Initialize selection state on mount."""
        found_match = False
        for button, color in self._color_by_button.items():
            matches = Color.parse(color) == Color.parse(self.selected_color)
            if matches and not found_match:
                button.add_class("focused")
                found_match = True
        self._select_focused_color()

    def watch_color_list(self, color_list: List[str]) -> None:
        """Rebuild grid when color list changes.

        Args:
            color_list: New list of colors to display
        """
        self._color_by_button = {}
        for button in self.query(Button):
            button.remove()
        for color in self.color_list:
            button = Button("", classes="color_button color_well")
            button.styles.background = color
            button.can_focus = False  # using fake focus for now
            self._color_by_button[button] = color
            self.mount(button)

    def on_key(self, event: events.Key) -> None:
        """Handle keyboard navigation.

        Args:
            event: Key event with arrow keys, home/end, space/enter
        """
        if event.key == "up":
            self._navigate_relative(-num_colors_per_row)
        elif event.key == "down":
            self._navigate_relative(+num_colors_per_row)
        elif event.key == "left":
            self._navigate_relative(-1)
        elif event.key == "right":
            self._navigate_relative(+1)
        elif event.key == "home":
            self._navigate_absolute(0)
        elif event.key == "end":
            self._navigate_absolute(len(self.color_list) - 1)
        elif event.key in ("space", "enter"):
            self._select_focused_color()

    def _select_focused_color(self) -> None:
        """Select currently focused color and post Changed message."""
        try:
            focused = self.query_one(".focused", Button)
        except NoMatches:
            return
        for selected in self.query(".selected"):
            selected.remove_class("selected")
        focused.add_class("selected")
        self.selected_color = self._color_by_button[focused]
        index = list(self._color_by_button.keys()).index(focused)
        self.post_message(self.Changed(self.selected_color, self, index))

    def _navigate_relative(self, delta: int) -> None:
        """Navigate relative to focused color.

        Args:
            delta: Offset from current position (±1 for left/right, ±8 for up/down)
        """
        try:
            focused = self.query_one(".focused", Button)
        except NoMatches:
            return
        index = list(self._color_by_button.keys()).index(focused)
        if delta == -1 and (index % num_colors_per_row) == 0:
            return
        if delta == +1 and (index % num_colors_per_row) == num_colors_per_row - 1:
            return
        self._navigate_absolute(index + delta)

    def _navigate_absolute(self, index: int) -> None:
        """Navigate to color at given index.

        Args:
            index: Target color index in color_list
        """
        if index < 0 or index >= len(self.color_list):
            return
        target_button = list(self._color_by_button.keys())[index]
        target_button.add_class("focused")
        for button in self._color_by_button:
            button.remove_class("focused")
        target_button.add_class("focused")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle color button click.

        Args:
            event: Button pressed event
        """
        self.selected_color = self._color_by_button[event.button]
        for button in self._color_by_button:
            button.remove_class("focused")
        event.button.add_class("focused")
        self._select_focused_color()
        self.focus()

    # I want MouseDown rather than Pressed in order to implement double-clicking.
    # However, event.control is None for mouse events, so this doesn't work:
    # def on_mouse_down(self, event: events.MouseDown) -> None:
    #     """Called when the mouse is pressed down."""
    #     if event.button == 1:
    #         self.selected_color = self._color_by_button[event.control]
    #         self.refresh()
    # @on(events.MouseDown, ".color_button")
    # def handle_color_button(self, event: events.MouseDown) -> None:
    #     """Called when a color button is clicked."""
    #     self.selected_color = self._color_by_button[event.control]


class LuminosityRamp(Widget):
    """Vertical luminosity slider with gradient preview.

    Displays a vertical gradient from black to white at the current
    hue/saturation, with a draggable marker for luminosity selection.

    Attributes:
        hue: Hue value (0.0-1.0)
        saturation: Saturation value (0.0-1.0)
        luminosity: Luminosity value (0.0-1.0)
    """

    class Changed(Message):
        """Message posted when luminosity changes.

        Attributes:
            luminosity: New luminosity value (0.0-1.0)
        """

        def __init__(self, luminosity: float) -> None:
            """Initialize Changed message.

            Args:
                luminosity: New luminosity value
            """
            super().__init__()
            self.luminosity = luminosity

    hue = reactive(0.0)
    saturation = reactive(0.0)
    luminosity = reactive(0.0)

    def __init__(
        self, hue: float, saturation: float, luminosity: float, **kwargs: Any
    ) -> None:
        """Initialize LuminosityRamp.

        Args:
            hue: Initial hue (0.0-1.0)
            saturation: Initial saturation (0.0-1.0)
            luminosity: Initial luminosity (0.0-1.0)
            **kwargs: Additional widget arguments
        """
        super().__init__(**kwargs)
        self.luminosity = luminosity
        self.hue = hue
        self.saturation = saturation
        self._mouse_down = False

    def render_line(self, y: int) -> Strip:
        """Render gradient line with luminosity marker.

        Args:
            y: Line number to render

        Returns:
            Strip with gradient background and optional marker
        """
        marker = (
            "<" if args.ascii_only else "◀"
        )  # ◀ (bigger/clearer) or 🢐 (closer shape but smaller)
        # lum = y / self.size.height # bottom isn't quite white
        lum = 1 - y / (self.size.height - 1)
        color = Color.from_hsl(self.hue, self.saturation, lum)
        style = Style(bgcolor=color.rich_color)
        segments = [Segment(" " * (self.size.width - 1), style, None)]
        if y == round((self.size.height - 1) * (1 - self.luminosity)):
            segments.append(Segment(marker, Style(color="black"), None))
        return Strip(segments)

    def on_mouse_down(self, event: events.MouseDown) -> None:
        """Start luminosity drag.

        Args:
            event: Mouse down event
        """
        self._update_color(event.y)
        self._mouse_down = True
        self.capture_mouse()

    def on_mouse_up(self, event: events.MouseUp) -> None:
        """End luminosity drag.

        Args:
            event: Mouse up event
        """
        self.release_mouse()
        self._mouse_down = False

    def on_mouse_move(self, event: events.MouseMove) -> None:
        """Update luminosity during drag.

        Args:
            event: Mouse move event
        """
        if self._mouse_down:
            self._update_color(event.y)

    def _update_color(self, y: int) -> None:
        """Update luminosity from y coordinate.

        Args:
            y: Vertical position in widget
        """
        self.luminosity = max(0, min(1, 1 - y / (self.size.height - 1)))
        self.post_message(self.Changed(luminosity=self.luminosity))
        # self.refresh()


class ColorField(Widget):
    """2D hue/saturation picker with crosshair.

    Displays a 2D gradient of hue (horizontal) and saturation (vertical)
    with a draggable crosshair for color selection.

    Attributes:
        hue: Hue value (0.0-1.0)
        saturation: Saturation value (0.0-1.0)
    """

    class Changed(Message):
        """Message posted when hue/saturation changes.

        Attributes:
            hue: New hue value (0.0-1.0)
            saturation: New saturation value (0.0-1.0)
        """

        def __init__(self, hue: float, saturation: float) -> None:
            """Initialize Changed message.

            Args:
                hue: New hue value
                saturation: New saturation value
            """
            super().__init__()
            self.hue = hue
            self.saturation = saturation

    hue = reactive(0.0)
    saturation = reactive(0.0)

    def __init__(self, hue: float, saturation: float, **kwargs: Any) -> None:
        """Initialize ColorField.

        Args:
            hue: Initial hue (0.0-1.0)
            saturation: Initial saturation (0.0-1.0)
            **kwargs: Additional widget arguments
        """
        super().__init__(**kwargs)
        self.hue = hue
        self.saturation = saturation
        self._mouse_down = False

    def render_line(self, y: int) -> Strip:
        """Render hue/saturation gradient line with crosshair.

        Args:
            y: Line number to render

        Returns:
            Strip with color gradient and optional crosshair marker
        """
        segments: List[Segment] = []
        crosshair = "+" if args.ascii_only else "✜"  # Options: ┼+✜✛⊹✚╋╬⁘⁛⌖⯐ or
        #  ╻
        # ╺ ╸
        #  ╹
        for x in range(self.size.width):
            crosshair_here = x == round(
                self.hue * (self.size.width - 1)
            ) and y == round((self.size.height - 1) * (1 - self.saturation))
            color = Color.from_hsl(
                x / (self.size.width - 1), 1 - y / (self.size.height - 1), 0.5
            )
            char = crosshair if crosshair_here else " "
            segments.append(
                Segment(char, Style(color="black", bgcolor=color.rich_color), None)
            )
        return Strip(segments)

    def on_mouse_down(self, event: events.MouseDown) -> None:
        """Start color drag.

        Args:
            event: Mouse down event
        """
        self._update_color(event.offset)
        self._mouse_down = True
        self.capture_mouse()

    def on_mouse_up(self, event: events.MouseUp) -> None:
        """End color drag.

        Args:
            event: Mouse up event
        """
        self.release_mouse()
        self._mouse_down = False

    def on_mouse_move(self, event: events.MouseMove) -> None:
        """Update color during drag.

        Args:
            event: Mouse move event
        """
        if self._mouse_down:
            self._update_color(event.offset)

    def _update_color(self, offset: Offset) -> None:
        """Update hue/saturation from offset.

        Args:
            offset: Mouse position in widget
        """
        x, y = offset
        self.hue = max(0, min(1, x / (self.size.width - 1)))
        self.saturation = max(0, min(1, 1 - y / (self.size.height - 1)))
        self.post_message(self.Changed(hue=self.hue, saturation=self.saturation))
        # self.refresh()


class ColorPreview(Widget):
    """Solid color preview widget.

    Displays a solid block of the currently selected color.

    Attributes:
        color: Color string to display
    """

    color: reactive[str] = reactive("black")

    def __init__(self, color: str, **kwargs: Any) -> None:
        """Initialize ColorPreview.

        Args:
            color: Initial color string
            **kwargs: Additional widget arguments
        """
        super().__init__(**kwargs)
        self.color = color

    def render_line(self, y: int) -> Strip:
        """Render solid color line.

        Args:
            y: Line number to render

        Returns:
            Strip filled with current color
        """
        return Strip([Segment(" " * self.size.width, Style(bgcolor=self.color), None)])


class IntegerInput(Input):
    """Input field constrained to integer range.

    Validates input to ensure it's an integer within min/max bounds.
    Restores last valid value on blur if empty.

    Attributes:
        min: Minimum allowed value
        max: Maximum allowed value
        last_valid_int: Last successfully validated integer
    """

    def __init__(self, min_val: int, max_val: int, **kwargs: Any) -> None:
        """Initialize IntegerInput.

        Args:
            min_val: Minimum allowed value
            max_val: Maximum allowed value
            **kwargs: Additional input arguments
        """
        super().__init__(**kwargs)
        self.min = min_val
        self.max = max_val
        self.last_valid_int = 0

    def _track_valid_int(self, value: str) -> int:
        """Parse and clamp integer value.

        Args:
            value: String to parse as integer

        Returns:
            Clamped integer or last valid value if parse fails
        """
        try:
            value_as_int = int(value)
        except ValueError:
            return self.last_valid_int
        value_as_int = max(self.min, min(self.max, value_as_int))
        self.last_valid_int = value_as_int
        return value_as_int

    def validate_value(self, value: str) -> str:
        """Validate input value.

        Args:
            value: Input string to validate

        Returns:
            Validated string (empty or valid integer)
        """
        if not value:
            return value
        return str(self._track_valid_int(value))

    def on_blur(self, event: events.Blur) -> None:
        """Restore last valid value if empty on blur.

        Args:
            event: Blur event
        """
        if not self.value:
            self.value = str(self.last_valid_int)


class EditColorsDialogWindow(DialogWindow):
    """Color picker dialog window.

    Full-featured color picker with basic/custom color grids,
    HSL color field, luminosity ramp, and RGB/HSL numeric inputs.

    Attributes:
        hue_degrees: Hue in degrees (0-360)
        sat_percent: Saturation percentage (0-100)
        lum_percent: Luminosity percentage (0-100)
        handle_selected_color: Callback for color selection
    """

    def __init__(
        self,
        *children: Widget,
        title: str = _("Edit Colors"),
        selected_color: str | None,
        handle_selected_color: Callable[[str], None],
        **kwargs: Any,
    ) -> None:
        """Initialize Edit Colors dialog.

        Args:
            *children: Child widgets
            title: Dialog window title
            selected_color: Initially selected color
            handle_selected_color: Callback receiving selected color hex
            **kwargs: Additional dialog arguments
        """
        super().__init__(
            *children, handle_button=self.handle_button, title=title, **kwargs
        )
        self.hue_degrees = 0.0
        self.sat_percent = 0.0
        self.lum_percent = 0.0
        # self._initial_color = selected_color
        if selected_color:
            self._current_color = selected_color
        self._color_by_button: Dict[Button, str] = {}
        self._inputs_by_letter: Dict[str, IntegerInput] = {}
        self._custom_colors_index = 0
        self.handle_selected_color = handle_selected_color

    def handle_button(self, button: Button) -> None:
        """Handle dialog button clicks.

        Args:
            button: Clicked button (ok/cancel/add_to_custom_colors)
        """
        if button.has_class("cancel"):
            self.request_close()
        elif button.has_class("ok"):
            self.handle_selected_color(self._current_color.hex)
        elif button.has_class("add_to_custom_colors"):
            global custom_colors
            custom_colors = custom_colors[:]
            custom_colors[self._custom_colors_index] = self._current_color.hex
            self.custom_colors_grid.color_list = custom_colors
            self._custom_colors_index = (self._custom_colors_index + 1) % len(
                custom_colors
            )

    def on_mount(self) -> None:
        """Build dialog layout on mount."""
        self.basic_colors_grid = ColorGrid(
            basic_colors, self._current_color.hex, classes="autofocus"
        )
        self.custom_colors_grid = ColorGrid(custom_colors, self._current_color.hex)
        verticals_for_inputs: List[Vertical] = []
        for color_model in ["hsl", "rgb"]:
            input_containers: List[Container] = []
            for component_letter in color_model:
                text_with_hotkey: str = {
                    "h": _("Hu&e:"),
                    "s": _("&Sat:"),
                    "l": _("&Lum:"),
                    "r": _("&Red:"),
                    "g": _("&Green:"),
                    "b": _("Bl&ue:"),
                }[component_letter]
                text_without_hotkey = text_with_hotkey.replace("&", "")
                max_value: int = {
                    "h": 360,
                    "s": 100,
                    "l": 100,
                    "r": 255,
                    "g": 255,
                    "b": 255,
                }[component_letter]
                min_value: int = 0
                color_input = IntegerInput(min_value, max_value, name=component_letter)
                label = Label(text_without_hotkey)
                container = Container(label, color_input, classes="input_container")
                input_containers.append(container)
                self._inputs_by_letter[component_letter] = color_input
            verticals_for_inputs.append(Vertical(*input_containers))

        self.content.mount(
            Horizontal(
                Vertical(
                    Label(_("Basic Colors")),
                    self.basic_colors_grid,
                    Label(_("Custom Colors")),
                    self.custom_colors_grid,
                ),
                Vertical(
                    Horizontal(
                        ColorField(self.hue_degrees / 360, self.sat_percent / 100),
                        LuminosityRamp(
                            self.hue_degrees / 360,
                            self.sat_percent / 100,
                            self.lum_percent / 100,
                        ),
                    ),
                    Horizontal(
                        Vertical(
                            ColorPreview("black"),
                            Label(_("Color")),
                            classes="color_preview_area",
                        ),
                        *verticals_for_inputs,
                    ),
                    Button(_("Add to Custom Colors"), classes="add_to_custom_colors"),
                ),
            ),
            Container(
                Button(_("OK"), classes="ok submit", variant="primary"),
                Button(_("Cancel"), classes="cancel"),
                classes="buttons",
            ),
        )

        self._update_inputs("hslrgb")

    def on_color_grid_changed(self, event: ColorGrid.Changed) -> None:
        """Handle color grid selection.

        Args:
            event: ColorGrid.Changed event with selected color
        """
        self._current_color = event.color
        self._update_inputs("hslrgb")
        self._update_color_preview()
        if event.color_grid is self.custom_colors_grid:
            self._custom_colors_index = event.index
        for color_grid in self.query(ColorGrid):
            if event.color_grid is not color_grid:
                for button in color_grid.query(Button):
                    button.remove_class("selected")

    def on_luminosity_ramp_changed(self, event: LuminosityRamp.Changed) -> None:
        """Handle luminosity slider change.

        Args:
            event: LuminosityRamp.Changed event with new luminosity
        """
        self.lum_percent = event.luminosity * 100
        self._update_inputs("lrgb")
        self._update_color_preview()

    def on_color_field_changed(self, event: ColorField.Changed) -> None:
        """Handle color field change.

        Args:
            event: ColorField.Changed event with new hue/saturation
        """
        self.hue_degrees = event.hue * 360
        self.sat_percent = event.saturation * 100
        self._update_inputs("hsrgb")
        self._update_color_preview()

    def on_input_changed(self, event: Input.Changed) -> None:
        """Handle numeric input change.

        Args:
            event: Input.Changed event from HSL/RGB input
        """
        component_letter = event.input.name
        if component_letter is None:
            return
        assert isinstance(event.input, IntegerInput)
        value = event.input.last_valid_int
        if component_letter in "hsl":
            if component_letter == "h":
                self.hue_degrees = value
            elif component_letter == "s":
                self.sat_percent = value
            else:
                self.lum_percent = value
            self._update_inputs("rgb")
        else:
            rgb = list(self._current_color.rgb)
            rgb["rgb".index(component_letter)] = value
            self._current_color = Color(*rgb)
            self._update_inputs("hsl")
        self._update_color_preview()

    @property
    def _current_color(self) -> Color:
        """Get current color from HSL values.

        Returns:
            Color object from current hue/saturation/luminosity
        """
        return Color.from_hsl(
            self.hue_degrees / 360, self.sat_percent / 100, self.lum_percent / 100
        )

    @_current_color.setter
    def _current_color(self, color: Color | str) -> None:
        """Set HSL values from color.

        Args:
            color: Color object or string to convert to HSL
        """
        if isinstance(color, str):
            color = Color.parse(color)
        hue, sat, lum = color.hsl
        self.hue_degrees = hue * 360
        self.sat_percent = sat * 100
        self.lum_percent = lum * 100

    def _update_inputs(self, component_letters: str) -> None:
        """Update numeric inputs for specified components.

        Args:
            component_letters: String of component letters to update (h/s/l/r/g/b)
        """
        with self.prevent(Input.Changed):
            for component_letter in component_letters:
                color_input = self._inputs_by_letter[component_letter]
                color_input.value = str(
                    int(
                        {
                            "h": self.hue_degrees,
                            "s": self.sat_percent,
                            "l": self.lum_percent,
                            "r": self._current_color.rgb[0],
                            "g": self._current_color.rgb[1],
                            "b": self._current_color.rgb[2],
                        }[component_letter]
                    )
                )

    def _update_color_preview(self) -> None:
        """Update color preview and picker widgets with current color."""
        self.query_one(ColorPreview).color = self._current_color.hex
        luminosity_ramp = self.query_one(LuminosityRamp)
        color_field = self.query_one(ColorField)
        luminosity_ramp.luminosity = self.lum_percent / 100
        luminosity_ramp.hue = self.hue_degrees / 360
        luminosity_ramp.saturation = self.sat_percent / 100
        color_field.hue = self.hue_degrees / 360
        color_field.saturation = self.sat_percent / 100
