"""Layer System for Paint Tool.

Provides a multi-layer system for complex ANSI art compositions with support
for blend modes, opacity, visibility, and layer groups.

Features:
    - Multiple independent layers with z-ordering
    - 7 blend modes (Normal, Multiply, Screen, Overlay, Add, Difference, Transparent)
    - Layer opacity and visibility controls
    - Layer locking for protection
    - Layer groups for organization
    - Efficient composition with caching
"""

from __future__ import annotations

import contextlib
from copy import deepcopy
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional
import uuid

from rich.style import Style
from textual.geometry import Region

if TYPE_CHECKING:
    from .ansi_art_document import AnsiArtDocument


def blend_colors(
    bottom: LayerCell, top: LayerCell, mode: BlendMode, opacity: float
) -> LayerCell:
    """Blend two layer cells using specified blend mode and opacity.

    Implements 7 blend modes with proper color math and opacity interpolation.

    Args:
        bottom: Bottom layer cell (base)
        top: Top layer cell (blend)
        mode: Blend mode to apply
        opacity: Opacity of top layer (0.0-1.0)

    Returns:
        Blended LayerCell with combined colors and properties
    """
    if top.is_transparent:
        return bottom

    blend_functions = {
        BlendMode.NORMAL: lambda: (
            _lerp_cells(bottom, top, opacity) if opacity < 1.0 else top
        ),
        BlendMode.TRANSPARENT: lambda: top if top.char != " " else bottom,
        BlendMode.MULTIPLY: lambda: _multiply_blend(top, bottom, opacity),
        BlendMode.SCREEN: lambda: _screen_blend(top, bottom, opacity),
        BlendMode.ADD: lambda: _add_blend(top, bottom, opacity),
        BlendMode.DIFFERENCE: lambda: _difference_blend(top, bottom, opacity),
        BlendMode.OVERLAY: lambda: _overlay_blend(top, bottom, opacity),
    }

    return blend_functions.get(mode, lambda: top)()


def _hex_to_rgb(hex_color: str) -> tuple:
    """Convert hex color string to RGB tuple.

    Args:
        hex_color: Hex color string (e.g., "#FF00FF")

    Returns:
        RGB tuple (r, g, b) with values 0-255
    """
    hex_color = hex_color.lstrip("#")
    return (
        tuple(int(hex_color[i : i + 2], 16) for i in (0, 2, 4))
        if len(hex_color) == 6
        else (255, 255, 255)
    )


def _lerp_cells(a: LayerCell, b: LayerCell, t: float) -> LayerCell:
    """Linear interpolation between two layer cells.

    Blends colors and selects character based on interpolation factor.

    Args:
        a: First cell
        b: Second cell
        t: Interpolation factor (0.0-1.0)

    Returns:
        Interpolated LayerCell
    """
    ar, ag, ab = _hex_to_rgb(a.bg_color)
    br, bg, bb = _hex_to_rgb(b.bg_color)

    r = int(ar + (br - ar) * t)
    g = int(ag + (bg - ag) * t)
    b_val = int(ab + (bb - ab) * t)

    return LayerCell(
        char=b.char if t >= 0.5 else a.char,
        fg_color=b.fg_color if t >= 0.5 else a.fg_color,
        bg_color=f"#{r:02x}{g:02x}{b_val:02x}",
        is_transparent=False,
    )


def _multiply_blend(top: LayerCell, bottom: LayerCell, opacity: float) -> LayerCell:
    """Multiply blend mode - darkens colors.

    Multiplies color channels and interpolates with opacity.

    Args:
        top: Top layer cell
        bottom: Bottom layer cell
        opacity: Blend opacity (0.0-1.0)

    Returns:
        Blended LayerCell
    """
    tr, tg, tb = _hex_to_rgb(top.bg_color)
    br, bg, bb = _hex_to_rgb(bottom.bg_color)

    r = int(((tr * br) // 255) * opacity + br * (1 - opacity))
    g = int(((tg * bg) // 255) * opacity + bg * (1 - opacity))
    b = int(((tb * bb) // 255) * opacity + bb * (1 - opacity))

    return LayerCell(
        char=top.char,
        fg_color=top.fg_color,
        bg_color=f"#{r:02x}{g:02x}{b:02x}",
        is_transparent=False,
    )


def _screen_blend(top: LayerCell, bottom: LayerCell, opacity: float) -> LayerCell:
    """Screen blend mode."""
    tr, tg, tb = _hex_to_rgb(top.bg_color)
    br, bg, bb = _hex_to_rgb(bottom.bg_color)

    r = int((255 - ((255 - tr) * (255 - br)) // 255) * opacity + br * (1 - opacity))
    g = int((255 - ((255 - tg) * (255 - bg)) // 255) * opacity + bg * (1 - opacity))
    b = int((255 - ((255 - tb) * (255 - bb)) // 255) * opacity + bb * (1 - opacity))

    return LayerCell(
        char=top.char,
        fg_color=top.fg_color,
        bg_color=f"#{r:02x}{g:02x}{b:02x}",
        is_transparent=False,
    )


def _add_blend(top: LayerCell, bottom: LayerCell, opacity: float) -> LayerCell:
    """Additive blend mode."""
    tr, tg, tb = _hex_to_rgb(top.bg_color)
    br, bg, bb = _hex_to_rgb(bottom.bg_color)

    r = min(255, int((tr + br) * opacity + br * (1 - opacity)))
    g = min(255, int((tg + bg) * opacity + bg * (1 - opacity)))
    b = min(255, int((tb + bb) * opacity + bb * (1 - opacity)))

    return LayerCell(
        char=top.char,
        fg_color=top.fg_color,
        bg_color=f"#{r:02x}{g:02x}{b:02x}",
        is_transparent=False,
    )


def _difference_blend(top: LayerCell, bottom: LayerCell, opacity: float) -> LayerCell:
    """Difference blend mode."""
    tr, tg, tb = _hex_to_rgb(top.bg_color)
    br, bg, bb = _hex_to_rgb(bottom.bg_color)

    r = int(abs(tr - br) * opacity + br * (1 - opacity))
    g = int(abs(tg - bg) * opacity + bg * (1 - opacity))
    b = int(abs(tb - bb) * opacity + bb * (1 - opacity))

    return LayerCell(
        char=top.char,
        fg_color=top.fg_color,
        bg_color=f"#{r:02x}{g:02x}{b:02x}",
        is_transparent=False,
    )


def _overlay_blend(top: LayerCell, bottom: LayerCell, opacity: float) -> LayerCell:
    """Overlay blend mode."""
    tr, tg, tb = _hex_to_rgb(top.bg_color)
    br, bg, bb = _hex_to_rgb(bottom.bg_color)

    r = int(
        ((br * tr) // 128 if br < 128 else 255 - ((255 - br) * (255 - tr)) // 128)
        * opacity
        + br * (1 - opacity)
    )
    g = int(
        ((bg * tg) // 128 if bg < 128 else 255 - ((255 - bg) * (255 - tg)) // 128)
        * opacity
        + bg * (1 - opacity)
    )
    b = int(
        ((bb * tb) // 128 if bb < 128 else 255 - ((255 - bb) * (255 - tb)) // 128)
        * opacity
        + bb * (1 - opacity)
    )

    return LayerCell(
        char=top.char,
        fg_color=top.fg_color,
        bg_color=f"#{r:02x}{g:02x}{b:02x}",
        is_transparent=False,
    )


class BlendMode(Enum):
    """Layer blending modes."""

    NORMAL = "normal"  # Top layer replaces bottom
    MULTIPLY = "multiply"  # Darken
    SCREEN = "screen"  # Lighten
    OVERLAY = "overlay"  # Contrast
    DIFFERENCE = "difference"  # Subtract
    ADD = "add"  # Additive blending
    TRANSPARENT = "transparent"  # Spaces are transparent


@dataclass
class LayerCell:
    """A single cell in a layer."""

    char: str = " "
    fg_color: str = "#ffffff"
    bg_color: str = "#000000"
    is_transparent: bool = True  # Space characters are transparent by default

    def to_style(self) -> Style:
        """Convert to Rich Style."""
        return Style(color=self.fg_color, bgcolor=self.bg_color)

    @classmethod
    def from_style(cls, char: str, style: Style) -> LayerCell:
        """Create from character and Rich Style."""
        fg = style.color.name if style.color else "#ffffff"
        bg = style.bgcolor.name if style.bgcolor else "#000000"
        return cls(char=char, fg_color=fg, bg_color=bg, is_transparent=(char == " "))


@dataclass
class Layer:
    """A single layer in the layer stack."""

    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = "Layer"
    width: int = 80
    height: int = 24
    visible: bool = True
    locked: bool = False
    opacity: float = 1.0  # 0.0 to 1.0
    blend_mode: BlendMode = BlendMode.NORMAL
    offset_x: int = 0
    offset_y: int = 0

    # Cell data
    cells: List[List[LayerCell]] = field(default_factory=list)

    def __post_init__(self):
        """Initialize cell grid if empty."""
        if not self.cells:
            self.cells = [
                [LayerCell() for _ in range(self.width)] for _ in range(self.height)
            ]

    def resize(self, new_width: int, new_height: int) -> None:
        """Resize the layer."""
        new_cells = [[LayerCell() for _ in range(new_width)] for _ in range(new_height)]

        # Copy existing data
        for y in range(min(self.height, new_height)):
            for x in range(min(self.width, new_width)):
                new_cells[y][x] = self.cells[y][x]

        self.width = new_width
        self.height = new_height
        self.cells = new_cells

    def get_cell(self, x: int, y: int) -> Optional[LayerCell]:
        """Get a cell at the given position."""
        adjusted_x = x - self.offset_x
        adjusted_y = y - self.offset_y

        if 0 <= adjusted_x < self.width and 0 <= adjusted_y < self.height:
            return self.cells[adjusted_y][adjusted_x]
        return None

    def set_cell(self, x: int, y: int, cell: LayerCell) -> bool:
        """Set a cell at the given position."""
        if self.locked:
            return False

        adjusted_x = x - self.offset_x
        adjusted_y = y - self.offset_y

        if 0 <= adjusted_x < self.width and 0 <= adjusted_y < self.height:
            self.cells[adjusted_y][adjusted_x] = cell
            return True
        return False

    def clear(self) -> None:
        """Clear all cells in the layer."""
        if self.locked:
            return

        for y in range(self.height):
            for x in range(self.width):
                self.cells[y][x] = LayerCell()

    def fill(self, cell: LayerCell, region: Optional[Region] = None) -> None:
        """Fill a region with a cell value."""
        if self.locked:
            return

        if region is None:
            region = Region(0, 0, self.width, self.height)

        for y in range(region.y, min(region.y + region.height, self.height)):
            for x in range(region.x, min(region.x + region.width, self.width)):
                self.cells[y][x] = deepcopy(cell)

    def copy(self) -> Layer:
        """Create a deep copy of this layer."""
        new_layer = Layer(
            name=f"{self.name} (copy)",
            width=self.width,
            height=self.height,
            visible=self.visible,
            locked=False,
            opacity=self.opacity,
            blend_mode=self.blend_mode,
            offset_x=self.offset_x,
            offset_y=self.offset_y,
        )
        new_layer.cells = deepcopy(self.cells)
        return new_layer

    def merge_down(self, bottom_layer: Layer) -> Layer:
        """Merge this layer onto a bottom layer, returning a new merged layer."""
        result = bottom_layer.copy()
        result.name = f"{self.name} + {bottom_layer.name}"

        for y in range(self.height):
            for x in range(self.width):
                top_cell = self.get_cell(x + self.offset_x, y + self.offset_y)
                if top_cell and not top_cell.is_transparent and self.visible:
                    result.set_cell(
                        x,
                        y,
                        self._blend_cells(
                            top_cell,
                            result.get_cell(x, y),
                            self.blend_mode,
                            self.opacity,
                        ),
                    )

        return result

    def _blend_cells(
        self,
        top: LayerCell,
        bottom: Optional[LayerCell],
        mode: BlendMode,
        opacity: float,
    ) -> LayerCell:
        """Blend two cells together using module-level blend functions."""
        if bottom is None:
            bottom = LayerCell()
        return blend_colors(bottom, top, mode, opacity)


@dataclass
class LayerGroup:
    """A group of layers that can be manipulated together."""

    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = "Group"
    layers: List[str] = field(default_factory=list)  # Layer IDs
    visible: bool = True
    locked: bool = False
    collapsed: bool = False


class LayerStack:
    """Manages a stack of layers for a document."""

    def __init__(self, width: int = 80, height: int = 24):
        self.width = width
        self.height = height
        self._layers: Dict[str, Layer] = {}
        self._order: List[str] = []  # Layer IDs from bottom to top
        self._groups: Dict[str, LayerGroup] = {}
        self._active_layer_id: Optional[str] = None

        # Event callbacks
        self._on_change_callbacks: List[Callable[[], None]] = []

        # Create default background layer
        self.add_layer("Background", locked=False)

    @property
    def active_layer(self) -> Optional[Layer]:
        """Get the currently active layer."""
        if self._active_layer_id and self._active_layer_id in self._layers:
            return self._layers[self._active_layer_id]
        return None

    @property
    def layer_count(self) -> int:
        """Get the number of layers."""
        return len(self._layers)

    def add_layer(
        self, name: str = "New Layer", above: Optional[str] = None, locked: bool = False
    ) -> Layer:
        """Add a new layer to the stack."""
        layer = Layer(name=name, width=self.width, height=self.height, locked=locked)

        self._layers[layer.id] = layer

        if above and above in self._order:
            idx = self._order.index(above) + 1
            self._order.insert(idx, layer.id)
        else:
            self._order.append(layer.id)

        self._active_layer_id = layer.id
        self._notify_change()

        return layer

    def remove_layer(self, layer_id: str) -> bool:
        """Remove a layer from the stack."""
        if layer_id not in self._layers:
            return False

        if len(self._layers) <= 1:
            return False  # Can't remove the last layer

        del self._layers[layer_id]
        self._order.remove(layer_id)

        # Update active layer
        if self._active_layer_id == layer_id:
            self._active_layer_id = self._order[-1] if self._order else None

        self._notify_change()
        return True

    def get_layer(self, layer_id: str) -> Optional[Layer]:
        """Get a layer by ID."""
        return self._layers.get(layer_id)

    def get_layer_by_name(self, name: str) -> Optional[Layer]:
        """Get a layer by name."""
        for layer in self._layers.values():
            if layer.name == name:
                return layer
        return None

    def get_layers_in_order(self) -> List[Layer]:
        """Get all layers in render order (bottom to top)."""
        return [self._layers[lid] for lid in self._order if lid in self._layers]

    def set_active_layer(self, layer_id: str) -> bool:
        """Set the active layer."""
        if layer_id in self._layers:
            self._active_layer_id = layer_id
            return True
        return False

    def store_document(self, layer_id: str, document: AnsiArtDocument) -> bool:
        """Copy the overlapping document cells into a layer."""
        layer = self.get_layer(layer_id)
        if layer is None:
            return False
        for y in range(min(document.height, layer.height)):
            for x in range(min(document.width, layer.width)):
                layer.cells[y][x] = LayerCell.from_style(
                    document.ch[y][x], document.st[y][x]
                )
        return True

    def load_document(self, layer_id: str, document: AnsiArtDocument) -> bool:
        """Copy the overlapping layer cells into an existing document."""
        layer = self.get_layer(layer_id)
        if layer is None:
            return False
        for y in range(min(document.height, layer.height)):
            for x in range(min(document.width, layer.width)):
                cell = layer.cells[y][x]
                document.ch[y][x] = cell.char
                document.st[y][x] = cell.to_style()
        return True

    def move_layer(self, layer_id: str, new_index: int) -> bool:
        """Move a layer to a new position in the stack."""
        if layer_id not in self._order:
            return False

        self._order.remove(layer_id)
        new_index = max(0, min(new_index, len(self._order)))
        self._order.insert(new_index, layer_id)

        self._notify_change()
        return True

    def move_layer_up(self, layer_id: str) -> bool:
        """Move a layer up one position."""
        if layer_id not in self._order:
            return False

        idx = self._order.index(layer_id)
        if idx < len(self._order) - 1:
            self._order[idx], self._order[idx + 1] = (
                self._order[idx + 1],
                self._order[idx],
            )
            self._notify_change()
            return True
        return False

    def move_layer_down(self, layer_id: str) -> bool:
        """Move a layer down one position."""
        if layer_id not in self._order:
            return False

        idx = self._order.index(layer_id)
        if idx > 0:
            self._order[idx], self._order[idx - 1] = (
                self._order[idx - 1],
                self._order[idx],
            )
            self._notify_change()
            return True
        return False

    def duplicate_layer(self, layer_id: str) -> Optional[Layer]:
        """Duplicate a layer."""
        if layer_id not in self._layers:
            return None

        original = self._layers[layer_id]
        copy = original.copy()

        self._layers[copy.id] = copy
        idx = self._order.index(layer_id) + 1
        self._order.insert(idx, copy.id)

        self._active_layer_id = copy.id
        self._notify_change()

        return copy

    def merge_layers(self, top_id: str, bottom_id: str) -> Optional[Layer]:
        """Merge two layers together."""
        if top_id not in self._layers or bottom_id not in self._layers:
            return None

        top = self._layers[top_id]
        bottom = self._layers[bottom_id]

        merged = top.merge_down(bottom)

        # Replace bottom layer with merged
        self._layers[bottom.id] = merged
        merged.id = bottom.id
        merged.name = f"Merged ({top.name})"

        # Remove top layer
        del self._layers[top_id]
        self._order.remove(top_id)

        self._active_layer_id = merged.id
        self._notify_change()

        return merged

    def merge_visible(self) -> Layer:
        """Merge all visible layers into one."""
        visible_layers = [
            layer for layer in self.get_layers_in_order() if layer.visible
        ]

        if not visible_layers:
            return self.add_layer("Empty Merge")

        result = visible_layers[0].copy()
        for layer in visible_layers[1:]:
            result = layer.merge_down(result)

        result.name = "Merged"
        return result

    def flatten(self) -> Layer:
        """Flatten all layers into one."""
        return self.merge_visible()

    def render(self) -> List[List[LayerCell]]:
        """Render all layers into a single grid."""
        result = [[LayerCell() for _ in range(self.width)] for _ in range(self.height)]

        for layer in self.get_layers_in_order():
            if not layer.visible:
                continue

            for y in range(self.height):
                for x in range(self.width):
                    cell = layer.get_cell(x, y)
                    if cell and not cell.is_transparent:
                        # Apply opacity and blend mode
                        blended = layer._blend_cells(
                            cell, result[y][x], layer.blend_mode, layer.opacity
                        )
                        result[y][x] = blended

        return result

    def compose(self) -> List[List[LayerCell]]:
        """Alias for render() - compose all layers into single grid."""
        return self.render()

    def to_document(self) -> AnsiArtDocument:
        """Convert the layer stack to a flat AnsiArtDocument."""
        from .ansi_art_document import AnsiArtDocument

        doc = AnsiArtDocument(self.width, self.height)
        rendered = self.render()

        for y in range(self.height):
            for x in range(self.width):
                cell = rendered[y][x]
                doc.ch[y][x] = cell.char
                doc.st[y][x] = cell.to_style()

        return doc

    @classmethod
    def from_document(cls, doc: AnsiArtDocument) -> LayerStack:
        """Create a LayerStack from an AnsiArtDocument."""
        stack = cls(doc.width, doc.height)

        # Clear default layer and populate
        base_layer = stack.active_layer
        if base_layer:
            for y in range(doc.height):
                for x in range(doc.width):
                    cell = LayerCell.from_style(doc.ch[y][x], doc.st[y][x])
                    base_layer.set_cell(x, y, cell)

        return stack

    def resize(self, new_width: int, new_height: int) -> None:
        """Resize all layers."""
        self.width = new_width
        self.height = new_height

        for layer in self._layers.values():
            layer.resize(new_width, new_height)

        self._notify_change()

    def on_change(self, callback: Callable[[], None]) -> None:
        """Register a callback for when the layer stack changes."""
        self._on_change_callbacks.append(callback)

    def _notify_change(self) -> None:
        """Notify all registered callbacks of a change."""
        for callback in self._on_change_callbacks:
            with contextlib.suppress(Exception):
                callback()

    def to_dict(self) -> Dict[str, Any]:
        """Serialize the layer stack to a dictionary."""
        return {
            "width": self.width,
            "height": self.height,
            "order": self._order,
            "active": self._active_layer_id,
            "layers": {
                lid: {
                    "id": layer.id,
                    "name": layer.name,
                    "visible": layer.visible,
                    "locked": layer.locked,
                    "opacity": layer.opacity,
                    "blend_mode": layer.blend_mode.value,
                    "offset_x": layer.offset_x,
                    "offset_y": layer.offset_y,
                    "cells": [
                        [
                            {
                                "char": cell.char,
                                "fg": cell.fg_color,
                                "bg": cell.bg_color,
                            }
                            for cell in row
                        ]
                        for row in layer.cells
                    ],
                }
                for lid, layer in self._layers.items()
            },
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> LayerStack:
        """Deserialize a layer stack from a dictionary."""
        stack = cls.__new__(cls)
        stack.width = data["width"]
        stack.height = data["height"]
        stack._order = data["order"]
        stack._active_layer_id = data["active"]
        stack._groups = {}
        stack._on_change_callbacks = []
        stack._layers = {}

        for lid, layer_data in data["layers"].items():
            layer = Layer(
                id=layer_data["id"],
                name=layer_data["name"],
                width=stack.width,
                height=stack.height,
                visible=layer_data["visible"],
                locked=layer_data["locked"],
                opacity=layer_data["opacity"],
                blend_mode=BlendMode(layer_data["blend_mode"]),
                offset_x=layer_data["offset_x"],
                offset_y=layer_data["offset_y"],
            )

            layer.cells = [
                [
                    LayerCell(
                        char=cell["char"],
                        fg_color=cell["fg"],
                        bg_color=cell["bg"],
                        is_transparent=(cell["char"] == " "),
                    )
                    for cell in row
                ]
                for row in layer_data["cells"]
            ]

            stack._layers[lid] = layer

        return stack
