"""
AuraToolHeader - Clean, minimal tool call header display.

Provides a streamlined header for tool executions with
essential information and optional argument preview.
"""

import json
from typing import Any, Dict, Optional

from rich.console import Group, RenderableType
from rich.text import Text

from aura_cli.cli.ui.components.base import ComponentBase
from aura_cli.cli.ui.constants import UIIcons, UIStyles
from aura_cli.cli.ui.theme_manager import get_theme_manager


class AuraToolHeader(ComponentBase):
    """
    Minimal tool header component.

    Displays tool name with optional metrics and argument preview.
    """

    def render(
        self,
        tool_name: str,
        args: Dict[str, Any],
        *,
        execution_time: Optional[float] = None,
        tokens: Optional[int] = None,
        show_preview: bool = True,
    ) -> RenderableType:
        """
        Render minimal tool header.

        Args:
            tool_name: Tool name
            args: Tool arguments
            execution_time: Execution time in seconds
            tokens: Token count
            show_preview: Show argument preview

        Returns:
            Formatted tool header
        """
        theme = get_theme_manager()
        parts = []

        header = Text()
        header.append(f"{UIIcons.TOOL} ", style=f"{theme.get_style('primary')}")
        header.append(tool_name, style=f"bold {theme.get_style('primary')}")

        metrics = []
        if execution_time is not None:
            if execution_time < 1:
                metrics.append(f"{execution_time * 1000:.0f}ms")
            else:
                metrics.append(f"{execution_time:.2f}s")
        if tokens is not None:
            metrics.append(f"{tokens:,} tokens")

        if metrics:
            header.append(f"  {' · '.join(metrics)}", style=f"dim {UIStyles.MUTED}")

        parts.append(header)

        if args and show_preview:
            parts.append(Text())

            for key, value in args.items():
                arg_line = Text()
                arg_line.append("  ", style="dim")
                arg_line.append(f"{key}", style=f"dim {theme.get_color('muted')}")
                arg_line.append(": ", style="dim")

                # Format value
                if isinstance(value, (dict, list)):
                    value_str = json.dumps(value, ensure_ascii=False)
                    if len(value_str) > 60:
                        value_str = value_str[:60] + "…"
                    arg_line.append(value_str, style=theme.get_style("code"))
                else:
                    value_str = str(value)
                    if len(value_str) > 80:
                        value_str = value_str[:80] + "…"
                    arg_line.append(value_str, style=theme.get_style("body"))

                parts.append(arg_line)

        return Group(*parts)


class ToolHeaderCompact(ComponentBase):
    """Ultra-compact tool header for dense displays."""

    def render(
        self,
        tool_name: str,
        status: str = "running",
        execution_time: Optional[float] = None,
    ) -> Text:
        """
        Render compact single-line tool header.

        Args:
            tool_name: Tool name
            status: Status (running, success, error)
            execution_time: Execution time

        Returns:
            Single-line formatted text
        """
        theme = get_theme_manager()

        # Status styling
        status_config = {
            "running": (UIIcons.LOADING, theme.get_style("status_working")),
            "success": (UIIcons.SUCCESS, theme.get_style("status_success")),
            "error": (UIIcons.ERROR, theme.get_style("status_error")),
        }
        icon, style = status_config.get(
            status, (UIIcons.TOOL, theme.get_style("primary"))
        )

        header = Text()
        header.append(f"{icon} ", style=style)
        header.append(tool_name, style=f"bold {style}")

        if execution_time is not None:
            if execution_time < 1:
                time_str = f"{execution_time * 1000:.0f}ms"
            else:
                time_str = f"{execution_time:.2f}s"
            header.append(f"  {time_str}", style=f"dim {theme.get_color('muted')}")

        return header
