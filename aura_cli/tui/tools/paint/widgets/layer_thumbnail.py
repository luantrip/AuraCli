"""Layer Thumbnail Widget - Aura CLI Paint Tool.

Efficient miniature preview rendering for layers with downsampling and caching.
"""

from typing import TYPE_CHECKING

from rich.segment import Segment
from rich.style import Style
from textual.strip import Strip
from textual.widget import Widget

if TYPE_CHECKING:
    from aura_cli.application.paint.layers import Layer


class LayerThumbnail(Widget):
    """Miniature layer preview widget with intelligent downsampling.

    Features:
        - Configurable thumbnail dimensions (default 32x16)
        - Efficient downsampling algorithm
        - Render caching for performance
        - Rich Segment rendering for accurate colors
        - Automatic cache invalidation
    """

    DEFAULT_CSS = """
    LayerThumbnail {
        width: 34;
        height: 16;
        background: #1E1E1E;
        border: solid #333333;
    }
    """

    def __init__(self, layer: "Layer", width: int = 32, height: int = 16) -> None:
        """Initialize layer thumbnail.

        Args:
            layer: Source layer to render
            width: Thumbnail width in characters
            height: Thumbnail height in lines
        """
        super().__init__()
        self.layer = layer
        self.thumb_width = width
        self.thumb_height = height
        self._cache = None

    def render_line(self, y: int) -> Strip:
        """Render a single line of the thumbnail.

        Args:
            y: Line index to render

        Returns:
            Strip containing rendered segments
        """
        if self._cache is None:
            self._render_thumbnail()

        if y < len(self._cache):
            return Strip(self._cache[y])
        return Strip([])

    def _render_thumbnail(self) -> None:
        """Generate thumbnail with downsampling algorithm.

        Calculates scale factors and samples source layer cells
        to create a miniature representation.
        """
        scale_x = self.layer.width / self.thumb_width
        scale_y = self.layer.height / self.thumb_height

        self._cache = []
        for y in range(self.thumb_height):
            line = []
            for x in range(self.thumb_width):
                src_x = min(int(x * scale_x), self.layer.width - 1)
                src_y = min(int(y * scale_y), self.layer.height - 1)

                if src_y < len(self.layer.cells) and src_x < len(
                    self.layer.cells[src_y]
                ):
                    cell = self.layer.cells[src_y][src_x]
                    style = Style(color=cell.fg_color, bgcolor=cell.bg_color)
                    line.append(Segment(cell.char, style))
                else:
                    line.append(Segment(" ", Style(bgcolor="#1E1E1E")))

            self._cache.append(line)

    def invalidate(self) -> None:
        """Invalidate cache and trigger refresh.

        Call this method when the source layer changes to force
        thumbnail regeneration on next render.
        """
        self._cache = None
        self.refresh()
