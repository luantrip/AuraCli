"""Onion Skin Renderer - Aura CLI Paint Tool.

Provides onion skinning visualization for animation preview with configurable
tinting and opacity for previous/next frames.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING, List

if TYPE_CHECKING:
    from .animation import Frame
    from .layers import LayerCell


@dataclass
class OnionSkinSettings:
    """Configuration for onion skinning visualisation."""

    enabled: bool = False
    show_previous: int = 1
    show_next: int = 1
    previous_opacity: float = 0.3
    next_opacity: float = 0.3
    previous_tint: str = "#FF0000"
    next_tint: str = "#0000FF"


class OnionSkinRenderer:
    """Renders animation frames with onion skinning overlay.

    Applies color tinting and opacity fading to previous and next frames
    to provide visual context during animation editing.
    """

    def __init__(self, settings: OnionSkinSettings) -> None:
        """Initialize onion skin renderer.

        Args:
            settings: Onion skinning configuration
        """
        self.settings = settings

    def render_with_onion_skin(
        self,
        current_frame: "Frame",
        previous_frames: List["Frame"],
        next_frames: List["Frame"],
    ) -> List[List["LayerCell"]]:
        """Render frame with onion skin overlay.

        Composites previous and next frames with tinting and opacity
        onto the current frame for animation preview.

        Args:
            current_frame: Active frame to render
            previous_frames: List of previous frames (ordered newest to oldest)
            next_frames: List of next frames (ordered nearest to farthest)

        Returns:
            2D grid of LayerCell objects with onion skin applied
        """
        if not self.settings.enabled:
            return self._render_frame(current_frame)

        result = self._render_frame(current_frame)

        for i, frame in enumerate(previous_frames[: self.settings.show_previous]):
            opacity = self.settings.previous_opacity * (1.0 - i * 0.2)
            result = self._blend_onion_skin(
                result, self._render_frame(frame), opacity, self.settings.previous_tint
            )

        for i, frame in enumerate(next_frames[: self.settings.show_next]):
            opacity = self.settings.next_opacity * (1.0 - i * 0.2)
            result = self._blend_onion_skin(
                result, self._render_frame(frame), opacity, self.settings.next_tint
            )

        return result

    def _render_frame(self, frame: "Frame") -> List[List["LayerCell"]]:
        """Render single frame to cell grid.

        Args:
            frame: Frame to render

        Returns:
            2D grid of LayerCell objects
        """
        from .layers import LayerCell

        if hasattr(frame, "layer_stack") and frame.layer_stack:
            return frame.layer_stack.compose()

        return [[LayerCell() for _ in range(80)] for _ in range(24)]

    def _blend_onion_skin(
        self,
        base: List[List["LayerCell"]],
        onion: List[List["LayerCell"]],
        opacity: float,
        tint: str,
    ) -> List[List["LayerCell"]]:
        """Blend onion skin layer onto base with tinting.

        Args:
            base: Base layer cell grid
            onion: Onion skin layer cell grid
            opacity: Blend opacity (0.0-1.0)
            tint: Hex color for tinting

        Returns:
            Blended cell grid
        """
        from .layers import LayerCell

        result = []
        for y in range(len(base)):
            row = []
            for x in range(len(base[0])):
                base_cell = base[y][x]
                onion_cell = (
                    onion[y][x] if y < len(onion) and x < len(onion[y]) else LayerCell()
                )

                if onion_cell.is_transparent:
                    row.append(base_cell)
                else:
                    tinted = self._apply_tint(onion_cell, tint, opacity)
                    row.append(tinted)
            result.append(row)
        return result

    def _apply_tint(self, cell: "LayerCell", tint: str, opacity: float) -> "LayerCell":
        """Apply color tint to cell with opacity blending.

        Args:
            cell: Source cell to tint
            tint: Hex color for tinting
            opacity: Tint opacity (0.0-1.0)

        Returns:
            New LayerCell with tint applied
        """
        from .layers import LayerCell

        r_tint = int(tint[1:3], 16)
        g_tint = int(tint[3:5], 16)
        b_tint = int(tint[5:7], 16)

        r = int(cell.bg_color[1:3], 16)
        g = int(cell.bg_color[3:5], 16)
        b = int(cell.bg_color[5:7], 16)

        r = int(r * (1 - opacity) + r_tint * opacity)
        g = int(g * (1 - opacity) + g_tint * opacity)
        b = int(b * (1 - opacity) + b_tint * opacity)

        return LayerCell(
            char=cell.char,
            fg_color=cell.fg_color,
            bg_color=f"#{r:02x}{g:02x}{b:02x}",
            is_transparent=False,
        )
