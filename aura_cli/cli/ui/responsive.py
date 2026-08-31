"""Responsive layout system — adaptive layouts for different terminal sizes.

Detects and categorises terminal width (SMALL <80, MEDIUM 80-120,
LARGE 120-160, XLARGE >160 columns). ResponsiveLayout provides
adaptive panel widths, column counts and size-based style adjustments.
"""

from enum import Enum
import time
from typing import Optional, Tuple

from rich.console import Console
from rich.panel import Panel
from rich.table import Table


class TerminalSize(Enum):
    """
    Terminal size categories for responsive layouts.

    Attributes:
        SMALL: Small terminal (< 80 columns)
        MEDIUM: Medium terminal (80-120 columns)
        LARGE: Large terminal (120-160 columns)
        XLARGE: Extra large terminal (> 160 columns)
    """

    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"
    XLARGE = "xlarge"


class ResponsiveLayout:
    """
    Responsive layout manager for automatic terminal size adaptation.

    Detects terminal size and provides methods to calculate widths,
    columns and appropriate layout configurations. Supports adaptive panels,
    responsive tables and intelligent text truncation.

    Attributes:
        console: Rich Console instance
        width: Current terminal width in columns
        height: Current terminal height in lines
        size_category: Size category (TerminalSize enum)

    Example:
        >>> layout = ResponsiveLayout()
        >>> width = layout.get_panel_width(0.9)
        >>> columns = layout.get_column_count(40)
        >>> config = layout.get_layout_config()
    """

    def __init__(self, console: Optional[Console] = None):
        """
        Initialize responsive layout manager with dynamic size tracking.

        Args:
            console: Custom Rich Console (creates new if None)
        """
        self.console = console or Console()
        self._update_size()
        self._last_size_check = time.time()
        self._size_check_interval = 1.0  # Verificar tamanho a cada 1s

    def _update_size(self):
        """Update terminal size information."""
        self.width = self.console.width
        self.height = self.console.height
        self.size_category = self._categorize_size()

    def check_size_change(self) -> bool:
        """Return True if the terminal size has changed."""
        import time

        current_time = time.time()
        if current_time - self._last_size_check < self._size_check_interval:
            return False

        old_width = self.width
        old_height = self.height

        self._update_size()

        self._last_size_check = current_time

        return old_width != self.width or old_height != self.height

    def _categorize_size(self) -> TerminalSize:
        """Categorize terminal size."""
        if self.width < 80:
            return TerminalSize.SMALL
        elif self.width < 120:
            return TerminalSize.MEDIUM
        elif self.width < 160:
            return TerminalSize.LARGE
        else:
            return TerminalSize.XLARGE

    def get_panel_width(self, percentage: float = 0.9) -> int:
        """Return ideal width for panels.

        Args:
            percentage: Width percentage (0.0-1.0)

        Returns:
            Panel width in columns
        """
        try:
            normalized_percentage = float(percentage)
        except (TypeError, ValueError):
            normalized_percentage = 0.9
        normalized_percentage = min(max(normalized_percentage, 0.0), 1.0)
        return max(1, int(self.width * normalized_percentage))

    def get_column_count(self, min_col_width: int = 40) -> int:
        """Return number of columns based on width.

        Args:
            min_col_width: Minimum column width

        Returns:
            Number of columns that fit
        """
        try:
            normalized_width = int(min_col_width)
        except (TypeError, ValueError):
            normalized_width = 40
        normalized_width = max(1, normalized_width)
        return max(1, self.width // normalized_width)

    def should_show_sidebar(self) -> bool:
        """Determina se deve mostrar sidebar."""
        return self.size_category in [TerminalSize.LARGE, TerminalSize.XLARGE]

    def should_show_footer(self) -> bool:
        """Determina se deve mostrar footer."""
        return self.height > 20

    def get_max_lines(self, reserve: int = 5) -> int:
        """Return the maximum lines to display for the current height."""
        return max(10, self.height - reserve)

    def create_adaptive_panel(self, content, title: str, **kwargs) -> Panel:
        """Cria painel adaptativo."""
        width = self.get_panel_width()

        padding = (0, 1) if self.size_category == TerminalSize.SMALL else (1, 2)

        return Panel(content, title=title, width=width, padding=padding, **kwargs)

    def create_adaptive_table(self, **kwargs) -> Table:
        """Cria tabela adaptativa."""
        if self.size_category == TerminalSize.SMALL:
            show_header = True
            show_lines = False
            padding = (0, 1)
        elif self.size_category == TerminalSize.MEDIUM:
            show_header = True
            show_lines = True
            padding = (0, 1)
        else:
            show_header = True
            show_lines = True
            padding = (0, 2)

        return Table(
            show_header=kwargs.get("show_header", show_header),
            show_lines=kwargs.get("show_lines", show_lines),
            padding=kwargs.get("padding", padding),
            **{
                k: v
                for k, v in kwargs.items()
                if k not in ["show_header", "show_lines", "padding"]
            },
        )

    def truncate_text(self, text: str, max_percentage: float = 0.8) -> str:
        """Trunca texto baseado na largura do terminal."""
        try:
            normalized_percentage = float(max_percentage)
        except (TypeError, ValueError):
            normalized_percentage = 0.8
        normalized_percentage = min(max(normalized_percentage, 0.0), 1.0)
        max_width = max(1, int(self.width * normalized_percentage))
        if len(text) <= max_width:
            return text
        if max_width <= 3:
            return text[:max_width]
        return text[: max_width - 3] + "..."

    def get_layout_config(self) -> dict:
        """Return a layout configuration dict for the current terminal."""
        configs = {
            TerminalSize.SMALL: {
                "columns": 1,
                "show_sidebar": False,
                "show_footer": False,
                "padding": (0, 1),
                "max_content_width": self.width - 4,
            },
            TerminalSize.MEDIUM: {
                "columns": 2,
                "show_sidebar": False,
                "show_footer": True,
                "padding": (1, 2),
                "max_content_width": self.width - 8,
            },
            TerminalSize.LARGE: {
                "columns": 3,
                "show_sidebar": True,
                "show_footer": True,
                "padding": (1, 2),
                "max_content_width": self.width - 12,
            },
            TerminalSize.XLARGE: {
                "columns": 4,
                "show_sidebar": True,
                "show_footer": True,
                "padding": (1, 3),
                "max_content_width": self.width - 16,
            },
        }
        return configs.get(self.size_category, configs[TerminalSize.MEDIUM])


class ResponsiveText:
    """Text that adapts its length to the terminal width."""

    @staticmethod
    def wrap_text(text: str, width: int, indent: int = 0) -> str:
        """Wrap text across multiple lines."""
        words = text.split()
        lines = []
        current_line = " " * indent

        for word in words:
            if len(current_line) + len(word) + 1 <= width:
                current_line += word + " "
            else:
                lines.append(current_line.rstrip())
                current_line = " " * indent + word + " "

        if current_line.strip():
            lines.append(current_line.rstrip())

        return "\n".join(lines)

    @staticmethod
    def ellipsize(text: str, max_length: int, position: str = "end") -> str:
        """Truncate text with ellipsis to fit a target width."""
        if len(text) <= max_length:
            return text

        if position == "end":
            return text[: max_length - 3] + "..."
        elif position == "middle":
            half = (max_length - 3) // 2
            return text[:half] + "..." + text[-half:]
        else:  # start
            return "..." + text[-(max_length - 3) :]


def get_responsive_layout(console: Optional[Console] = None) -> ResponsiveLayout:
    """Return a ResponsiveLayout for the current terminal."""
    return ResponsiveLayout(console)


def get_terminal_size(console: Optional[Console] = None) -> Tuple[int, int]:
    """Return (width, height) of the current terminal."""
    console = console or Console()
    return (console.width, console.height)


def is_small_terminal(console: Optional[Console] = None) -> bool:
    """Return True if the terminal is small."""
    width, _ = get_terminal_size(console)
    return width < 80


def is_large_terminal(console: Optional[Console] = None) -> bool:
    """Return True if the terminal is large."""
    width, _ = get_terminal_size(console)
    return width >= 120
