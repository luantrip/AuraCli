"""Data Visualization Charts for Aura TUI.

ASCII-based charts for terminal data visualization.
"""

from dataclasses import dataclass
from typing import Any, ClassVar, Dict, List, Optional, Tuple

from textual.widgets import Static


@dataclass
class ChartData:
    """Data for chart rendering."""

    values: List[float]
    labels: Optional[List[str]] = None
    title: str = ""
    color: str = "cyan"


class ASCIILineChart(Static):
    """ASCII line chart widget."""

    CHARS: ClassVar[dict] = {
        "empty": " ",
        "point": "●",
        "line_h": "─",
        "line_v": "│",
        "corner_tl": "┌",
        "corner_tr": "┐",
        "corner_bl": "└",
        "corner_br": "┘",
        "cross": "┼",
        "t_left": "├",
        "t_right": "┤",
        "t_up": "┴",
        "t_down": "┬",
    }

    def __init__(
        self,
        data: Optional[List[float]] = None,
        height: int = 8,
        title: str = "",
        color: str = "cyan",
        show_axis: bool = True,
        **kwargs,
    ):
        """Initialize the instance."""
        super().__init__(**kwargs)
        self.data = data or []
        self.chart_height = height
        self.title = title
        self.color = color
        self.show_axis = show_axis

    def render(self) -> str:
        """Render the widget content."""
        if not self.data:
            return "No data to display"

        result = []

        if self.title:
            result.append(self.title)

        chart = self._generate_chart()
        result.append(chart)

        return "\n".join(result)

    @staticmethod
    def _interpolate_line(grid: list, x: int, prev_y: int, y: int) -> None:
        """Draw vertical connector between prev_y and y at column x-1."""
        step = 1 if prev_y < y else -1
        for cy in range(prev_y + step, y, step):
            if 0 <= cy < len(grid) and grid[cy][x - 1] == " ":
                grid[cy][x - 1] = "│"

    def _generate_chart(self) -> str:
        """Generate the chart renderable from current data."""
        if not self.data:
            return ""

        data = self.data
        height = self.chart_height
        width = min(len(data), 60)

        if len(data) > width:
            step = len(data) / width
            data = [data[int(i * step)] for i in range(width)]

        min_val = min(data)
        max_val = max(data)
        val_range = max_val - min_val if max_val != min_val else 1

        grid = [[" " for _ in range(width + 6)] for _ in range(height + 2)]

        for i in range(height):
            val = max_val - (i * val_range / (height - 1))
            label = f"{val:5.1f}"
            for j, c in enumerate(label):
                grid[i][j] = c

        if self.show_axis:
            for i in range(height):
                grid[i][5] = "│"
            for j in range(5, width + 6):
                grid[height][j] = "─"
            grid[height][5] = "└"

        for i, val in enumerate(data):
            if val_range > 0:
                y = int((max_val - val) / val_range * (height - 1))
            else:
                y = height // 2

            y = max(0, min(height - 1, y))
            x = i + 6

            if x < len(grid[0]):
                grid[y][x] = "●"
            if x < len(grid[0]) and 0 < i < len(data):
                prev_y = max(
                    0,
                    min(
                        height - 1,
                        int((max_val - data[i - 1]) / val_range * (height - 1))
                        if val_range > 0
                        else height // 2,
                    ),
                )
                if prev_y != y:
                    self._interpolate_line(grid, x, prev_y, y)

        lines = ["".join(row) for row in grid]
        return "\n".join(lines)

    def update_data(self, data: List[float]) -> None:
        """Update the chart with new data."""
        self.data = data
        self.update(self.render())


class BarChart(Static):
    """Horizontal bar chart widget."""

    def __init__(
        self,
        data: Optional[Dict[str, float]] = None,
        title: str = "",
        max_width: int = 40,
        color: str = "cyan",
        show_values: bool = True,
        **kwargs,
    ):
        """Initialize the instance."""
        super().__init__(**kwargs)
        self.data = data or {}
        self.title = title
        self.max_width = max_width
        self.color = color
        self.show_values = show_values

    def render(self) -> str:
        """Render the widget content."""
        if not self.data:
            return "No data to display"

        result = []

        if self.title:
            result.append(self.title)
            result.append("")

        max_val = max(self.data.values()) if self.data.values() else 1
        max_label_len = max(len(str(k)) for k in self.data) if self.data else 0

        for label, value in self.data.items():
            padded_label = f"{label:>{max_label_len}}"
            bar_width = int((value / max_val) * self.max_width) if max_val > 0 else 0
            bar = "█" * bar_width

            line = f"{padded_label} {bar}"
            if self.show_values:
                line += f" {value:.1f}"
            result.append(line)

        return "\n".join(result)

    def update_data(self, data: Dict[str, float]) -> None:
        """Update the chart with new data."""
        self.data = data
        self.update(self.render())


class VerticalBarChart(Static):
    """Vertical bar chart widget."""

    BLOCKS = " ▁▂▃▄▅▆▇█"

    def __init__(
        self,
        data: Optional[List[Tuple[str, float]]] = None,
        title: str = "",
        height: int = 8,
        color: str = "cyan",
        **kwargs,
    ):
        """Initialize the instance."""
        super().__init__(**kwargs)
        self.data = data or []
        self.title = title
        self.bar_height = height
        self.color = color

    def render(self) -> str:
        """Render the widget content."""
        if not self.data:
            return "No data to display"

        result = []

        if self.title:
            result.append(self.title)
            result.append("")

        max_val = max(v for _, v in self.data) if self.data else 1

        for row in range(self.bar_height, 0, -1):
            threshold = (row / self.bar_height) * max_val
            line = ""

            for _, value in self.data:
                if value >= threshold:
                    line += " █ "
                elif value >= threshold - (max_val / self.bar_height / 2):
                    block_idx = int(
                        (value - threshold + (max_val / self.bar_height))
                        / (max_val / self.bar_height)
                        * 8
                    )
                    block_idx = max(0, min(8, block_idx))
                    line += f" {self.BLOCKS[block_idx]} "
                else:
                    line += "   "

            result.append(line)

        label_line = ""
        for label, _ in self.data:
            short_label = label[:3] if len(label) > 3 else label
            label_line += f" {short_label:^2}"
        result.append(label_line)

        return "\n".join(result)

    def update_data(self, data: List[Tuple[str, float]]) -> None:
        """Update the chart with new data."""
        self.data = data
        self.update(self.render())


class MetricGauge(Static):
    """Metric gauge widget."""

    def __init__(
        self,
        label: str = "",
        value: float = 0,
        max_value: float = 100,
        width: int = 20,
        color: str = "cyan",
        warning_threshold: float = 0.7,
        critical_threshold: float = 0.9,
        **kwargs,
    ):
        """Initialize the instance."""
        super().__init__(**kwargs)
        self.label = label
        self.value = value
        self.max_value = max_value
        self.gauge_width = width
        self.color = color
        self.warning_threshold = warning_threshold
        self.critical_threshold = critical_threshold

    def render(self) -> str:
        """Render the widget content."""
        pct = self.value / self.max_value if self.max_value > 0 else 0
        pct = max(0, min(1, pct))

        filled = int(pct * self.gauge_width)
        empty = self.gauge_width - filled

        bar = "▐" + "█" * filled + "░" * empty + "▌"
        value_text = f" {self.value:.1f}/{self.max_value:.0f} ({pct * 100:.0f}%)"

        return f"{self.label}: {bar}{value_text}"

    def update_value(self, value: float) -> None:
        """Update the displayed value."""
        self.value = value
        self.update(self.render())


class StatsDisplay(Static):
    """Statistics display widget."""

    def __init__(
        self,
        title: str = "Estatísticas",
        stats: Optional[Dict[str, Any]] = None,
        **kwargs,
    ):
        """Initialize the instance."""
        super().__init__(**kwargs)
        self.title = title
        self.stats = stats or {}

    def render(self) -> str:
        """Render the widget content."""
        result = []

        result.append(f"┌─ {self.title} " + "─" * (30 - len(self.title)) + "┐")

        for key, value in self.stats.items():
            if isinstance(value, float):
                value_str = f"{value:.2f}"
            elif isinstance(value, int):
                value_str = f"{value:,}"
            else:
                value_str = str(value)

            line_len = len(key) + len(value_str) + 4
            padding = " " * max(0, 32 - line_len)
            result.append(f"│ {key}: {value_str}{padding}│")

        result.append("└" + "─" * 32 + "┘")

        return "\n".join(result)

    def update_stats(self, stats: Dict[str, Any]) -> None:
        """Update the statistics display."""
        self.stats = stats
        self.update(self.render())


class MiniSparkline(Static):
    """Mini inline sparkline widget."""

    SPARK_CHARS = "▁▂▃▄▅▆▇█"

    def __init__(
        self,
        data: Optional[List[float]] = None,
        width: int = 10,
        color: str = "cyan",
        **kwargs,
    ):
        """Initialize the instance."""
        super().__init__(**kwargs)
        self.data = data or []
        self.spark_width = width
        self.color = color

    def render(self) -> str:
        """Render the widget content."""
        if not self.data:
            return "─" * self.spark_width

        min_val = min(self.data)
        max_val = max(self.data)
        val_range = max_val - min_val if max_val != min_val else 1

        data = self.data
        if len(data) > self.spark_width:
            step = len(data) / self.spark_width
            data = [data[int(i * step)] for i in range(self.spark_width)]

        spark = ""
        for val in data:
            normalized = (val - min_val) / val_range
            idx = int(normalized * 7)
            idx = max(0, min(7, idx))
            spark += self.SPARK_CHARS[idx]

        return spark

    def update_data(self, data: List[float]) -> None:
        """Update the chart with new data."""
        self.data = data
        self.update(self.render())
