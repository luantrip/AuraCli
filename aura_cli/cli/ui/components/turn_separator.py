"""
TurnSeparator - Subtle visual separator between conversation turns.

Provides a modern, minimal divider that uses gradient-like fading
from the theme's accent colors. Inspired by Warp/Cursor turn boundaries.
"""

from typing import Optional

from rich.console import RenderableType
from rich.text import Text

from aura_cli.cli.ui.components.base import ComponentBase
from aura_cli.cli.ui.theme_manager import get_theme_manager


class TurnSeparator(ComponentBase):
    """
    Minimal turn separator for between conversation messages.

    Variants:
    - subtle: Very dim line (between same-sender messages)
    - standard: Visible separator (between user/assistant turns)
    - accent: Colored separator (after tool execution blocks)
    """

    def render(
        self,
        variant: str = "standard",
        label: Optional[str] = None,
        width: int = 60,
    ) -> RenderableType:
        """Render turn separator.

        Args:
            variant: Visual style (subtle, standard, accent)
            label: Optional centered label
            width: Separator width in chars

        Returns:
            Formatted separator
        """
        theme = get_theme_manager()

        if variant == "subtle":
            line_char = "·"
            style = f"dim {theme.get_color('muted')}"
            sep_width = min(width, 30)
        elif variant == "accent":
            line_char = "─"
            style = theme.get_color("accent")
            sep_width = min(width, 40)
        else:
            line_char = "─"
            style = f"dim {theme.get_color('muted')}"
            sep_width = min(width, 40)

        if label:
            label_text = f" {label} "
            side_len = max(4, (sep_width - len(label_text)) // 2)
            separator = Text()
            separator.append(line_char * side_len, style=style)
            separator.append(label_text, style=f"dim {theme.get_style('caption')}")
            separator.append(line_char * side_len, style=style)
        else:
            separator = Text(line_char * sep_width, style=style)

        return separator


class ToolCallInline(ComponentBase):
    """
    Compact inline tool call display — single line per tool.

    Shows: ⚒ tool_name(key_arg) ✔ 0.3s
    Modern collapsed style like Cursor/Claude Code.
    """

    def render(
        self,
        tool_name: str,
        args: dict,
        status: str = "running",
        duration: Optional[float] = None,
    ) -> Text:
        """Render compact inline tool call.

        Args:
            tool_name: Tool function name
            args: Tool arguments (shows first key arg)
            status: running | success | error
            duration: Execution time

        Returns:
            Single-line Text
        """
        theme = get_theme_manager()
        text = Text()

        # Status icon
        if status == "success":
            icon_style = theme.get_style("status_success")
            status_icon = "✔"
        elif status == "error":
            icon_style = theme.get_style("status_error")
            status_icon = "✖"
        else:
            icon_style = theme.get_style("status_working")
            status_icon = "⟳"

        # Tool icon + name
        text.append("  ⚒ ", style=f"dim {theme.get_color('muted')}")
        text.append(tool_name, style=theme.get_style("primary"))

        # Key argument preview (first meaningful arg)
        preview = self._get_arg_preview(args)
        if preview:
            text.append(f"({preview})", style=f"dim {theme.get_color('muted')}")

        # Status + duration
        text.append(f" {status_icon}", style=icon_style)
        if duration is not None:
            if duration < 1:
                time_str = f"{duration * 1000:.0f}ms"
            else:
                time_str = f"{duration:.1f}s"
            text.append(f" {time_str}", style=f"dim {theme.get_color('muted')}")

        return text

    def _get_arg_preview(self, args: dict) -> str:
        """Extract key argument for preview."""
        if not args:
            return ""

        # Priority keys to show
        priority_keys = ["path", "file_path", "query", "command", "pattern", "content"]
        for key in priority_keys:
            if key in args:
                val = str(args[key])
                if len(val) > 40:
                    val = val[:37] + "…"
                return val

        # Fallback: first arg
        first_key = next(iter(args))
        val = str(args[first_key])
        if len(val) > 40:
            val = val[:37] + "…"
        return val
