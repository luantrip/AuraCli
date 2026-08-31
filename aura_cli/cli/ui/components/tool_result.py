"""
ToolResult - Clean result display for tool executions.

Provides minimal, informative display of tool results
with appropriate formatting based on content type.
Expandable output when truncated (same pattern as shell_command).
"""

import json
from typing import Any, Optional

from rich.console import Group, RenderableType
from rich.syntax import Syntax
from rich.text import Text

from aura_cli.application.presentation.cli_visual import cli_label, decide_cli_visual
from aura_cli.cli.ui.components.base import ComponentBase
from aura_cli.cli.ui.constants import UIIcons
from aura_cli.cli.ui.terminal_display import ExpandableOutput
from aura_cli.cli.ui.theme_manager import get_theme_manager


class ToolResult(ComponentBase):
    """
    Clean tool result display component.

    Features:
    - Automatic format detection
    - Syntax highlighting for code/JSON
    - Truncation for long outputs
    - Status indicators
    """

    def render(
        self,
        tool_name: str,
        result: Any,
        execution_time: Optional[float] = None,
        status: str = "success",
        args: Optional[dict] = None,
        show_args: bool = False,
        console_width: int = 80,
        max_lines: Optional[int] = None,
        *rest,
        **kwargs,
    ) -> RenderableType:
        """
        Render tool result with minimal styling.

        Args:
            tool_name: Tool name
            result: Result data
            execution_time: Execution time
            status: Result status (success, error)
            max_lines: Maximum lines to display

        Returns:
            Formatted result display
        """
        theme = get_theme_manager()
        success = status.lower() in {"success", "done", "completed"}

        if success:
            status_icon = UIIcons.SUCCESS
            status_style = theme.get_style("success")
        else:
            status_icon = UIIcons.ERROR
            status_style = theme.get_style("error")

        parts: list[Any] = []

        header = Text()
        header.append(f"{status_icon} ", style=status_style)
        header.append(tool_name, style=f"bold {status_style}")

        metrics = []
        if execution_time is not None:
            if execution_time < 1:
                metrics.append(f"{execution_time * 1000:.0f}ms")
            else:
                metrics.append(f"{execution_time:.2f}s")

        if isinstance(result, (dict, list)):
            content = json.dumps(result, indent=2, ensure_ascii=False)
            fmt = "json"
            metrics.append("JSON")
        else:
            content = str(result)
            fmt = "text"

        if metrics:
            header.append(
                f"  {' · '.join(metrics)}", style=f"dim {theme.get_color('muted')}"
            )

        parts.append(header)
        parts.append(Text())

        # Show arguments if requested
        if show_args and args:
            args_text = Text()
            args_text.append("  Args: ", style=f"dim {theme.get_color('muted')}")
            args_str = ", ".join(f"{k}={repr(v)[:30]}" for k, v in args.items())
            args_text.append(args_str, style=f"dim {theme.get_color('muted')}")
            parts.append(args_text)
            parts.append(Text())

        # Capture any extra positional arguments for forward compatibility
        _ = rest  # Explicitly acknowledge unused args

        if max_lines is None:
            max_lines = decide_cli_visual(console_width).result_preview_lines
        lines = content.splitlines()
        truncated = len(lines) > max_lines

        if truncated:
            expandable = ExpandableOutput(content, max_preview_lines=max_lines)
            content_group = expandable.render(title=cli_label("result"))
            parts.append(content_group)
        elif fmt == "json":
            syntax_theme = theme.get_appearance_property("syntax_theme", "monokai")
            syntax = Syntax(
                content,
                "json",
                theme=syntax_theme,
                line_numbers=False,
                word_wrap=True,
            )
            parts.append(syntax)
        else:
            content_text = Text(content, style=theme.get_style("body"))
            parts.append(content_text)

        return Group(*parts)


class ToolResultCompact(ComponentBase):
    """Ultra-compact tool result for inline display."""

    def render(
        self,
        tool_name: str,
        success: bool = True,
        message: str = "",
        execution_time: Optional[float] = None,
    ) -> Text:
        """
        Render compact single-line result.

        Args:
            tool_name: Tool name
            success: Whether successful
            message: Short result message
            execution_time: Execution time

        Returns:
            Single-line formatted text
        """
        theme = get_theme_manager()

        if success:
            icon = UIIcons.SUCCESS
            style = theme.get_style("success")
        else:
            icon = UIIcons.ERROR
            style = theme.get_style("error")

        result = Text()
        result.append(f"{icon} ", style=style)
        result.append(tool_name, style=f"bold {style}")

        if message:
            result.append(f"  {message}", style=theme.get_style("body"))

        if execution_time is not None:
            if execution_time < 1:
                time_str = f"{execution_time * 1000:.0f}ms"
            else:
                time_str = f"{execution_time:.2f}s"
            result.append(f"  ({time_str})", style=f"dim {theme.get_color('muted')}")

        return result
