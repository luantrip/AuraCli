"""
Terminal display - Clean command rendering.

Provides minimal, informative display of terminal commands
with ANSI support and status indicators.
"""

from typing import Any, List, Optional

from rich.console import Console, Group
from rich.syntax import Syntax
from rich.text import Text

from aura_cli.application.presentation import (
    detect_output_language,
    query_output_lines,
)
from aura_cli.cli.ui.constants import UIIcons, UIStyles
from aura_cli.cli.ui.display_facade import get_console
from aura_cli.cli.ui.layout_contract import layout_for_width
from aura_cli.cli.ui.theme_manager import get_theme_manager


class ExpandableOutput:
    """Expandable output with search and syntax highlighting."""

    def __init__(self, output: str, max_preview_lines: int = 30):
        """Initialize the instance."""
        self.output = output
        self.max_preview_lines = max_preview_lines
        self.is_expanded = False
        self.search_query: str = ""
        self.filter_type: Optional[str] = None

    def set_search(self, query: str):
        """Set search query."""
        self.search_query = query

    def set_filter(self, filter_type: Optional[str]):
        """Set filter type."""
        self.filter_type = filter_type

    def _detect_language(self) -> str:
        """Detect output language for syntax highlighting."""
        return detect_output_language(self.output)

    def _filter_lines(self, lines: List[str]) -> List[str]:
        """Filter lines by type."""
        return query_output_lines(lines, filter_type=self.filter_type)

    def _highlight_search(self, text: str) -> Text:
        """Highlight search terms in text."""
        if not self.search_query:
            return Text(text)

        result = Text()
        query_lower = self.search_query.lower()
        text_lower = text.lower()

        last_pos = 0
        while True:
            pos = text_lower.find(query_lower, last_pos)
            if pos == -1:
                result.append(text[last_pos:])
                break

            accent_style = UIStyles.safe_style("ACCENT", "magenta")
            result.append(text[last_pos:pos])
            result.append(
                text[pos : pos + len(self.search_query)],
                style=f"bold reverse {accent_style}",
            )
            last_pos = pos + len(self.search_query)

        return result

    def render(self, title: str = "Saída") -> Group:
        """Render expandable output with minimal styling."""
        theme = get_theme_manager()
        muted = theme.get_color("muted")

        lines = self.output.splitlines()

        lines = query_output_lines(
            lines, filter_type=self.filter_type, query=self.search_query
        )

        truncated = False
        if not self.is_expanded and len(lines) > self.max_preview_lines:
            display_lines = lines[: self.max_preview_lines]
            truncated = True
        else:
            display_lines = lines

        parts: list[Any] = []

        header = Text()
        header.append(title, style=f"dim {theme.get_style('primary')}")

        if self.search_query or self.filter_type:
            header.append("  ", style="dim")
            if self.search_query:
                header.append(f"search: {self.search_query}", style=f"dim {muted}")
            if self.filter_type:
                header.append(f"  filter: {self.filter_type}", style=f"dim {muted}")

        parts.append(header)
        parts.append(Text())

        language = self._detect_language()

        if language != "text":
            display_text = "\n".join(display_lines)
            syntax_theme = theme.get_appearance_property("syntax_theme", "monokai")
            syntax = Syntax(
                display_text,
                language,
                theme=syntax_theme,
                line_numbers=False,
                word_wrap=True,
            )
            parts.append(syntax)
        else:
            for line in display_lines:
                highlighted = self._highlight_search(line)
                parts.append(highlighted)

        if truncated:
            remaining = len(lines) - self.max_preview_lines
            parts.append(Text())
            parts.append(
                Text(f"  ⋯ {remaining} linhas  [e] expandir", style=f"dim {muted}")
            )

        return Group(*parts)


def display_terminal_command(
    command: str,
    output: Optional[str] = None,
    status: str = "completed",
    execution_time: Optional[float] = None,
    exit_code: Optional[int] = None,
    output_console: Optional[Console] = None,
) -> None:
    """
    Display terminal command with minimal styling.

    Args:
        command: Executed command
        output: Command output
        status: Status (running, completed, failed, background)
        execution_time: Execution time in seconds
        exit_code: Exit code
    """
    target_console = output_console if output_console is not None else get_console()
    theme = get_theme_manager()
    muted = theme.get_color("muted")
    primary = theme.get_color("primary")
    border_muted = UIStyles.safe_style("BORDER_MUTED", "dim white")

    if status == "running":
        status_icon = UIIcons.LOADING
        status_style = theme.get_style("status_working")
    elif status == "failed" or (exit_code is not None and exit_code != 0):
        status_icon = UIIcons.ERROR
        status_style = theme.get_style("status_error")
    elif status == "background":
        status_icon = UIIcons.RUN
        status_style = theme.get_style("info")
    else:
        status_icon = UIIcons.SUCCESS
        status_style = theme.get_style("status_success")

    command_text = Text()
    command_text.append("  ", style="dim")
    command_text.append(f"{status_icon} ", style=status_style)
    command_text.append("$ ", style=f"bold {primary}")
    command_text.append(command, style=theme.get_style("body"))

    if execution_time is not None:
        if execution_time < 1:
            time_str = f"{execution_time * 1000:.0f}ms"
        elif execution_time < 60:
            time_str = f"{execution_time:.1f}s"
        else:
            mins = int(execution_time // 60)
            secs = execution_time % 60
            time_str = f"{mins}m {secs:.1f}s"
        command_text.append("  ", style="dim")
        command_text.append(f"({time_str})", style=f"dim {muted}")

    if exit_code is not None and exit_code != 0:
        command_text.append("  ", style="dim")
        command_text.append(f"exit {exit_code}", style=theme.get_style("error"))

    target_console.print(command_text)

    if output:
        expandable = ExpandableOutput(output, max_preview_lines=30)
        output_display = expandable.render()
        from rich.panel import Panel as RichPanel

        output_group = RichPanel(
            output_display,
            border_style=border_muted,
            padding=layout_for_width(target_console.width).group_padding,
        )
        target_console.print(output_group)


def create_status_badge(status: str, message: str = "") -> Text:
    """
    Create minimal status badge.

    Args:
        status: Status type
        message: Optional message

    Returns:
        Formatted status text
    """
    theme = get_theme_manager()

    badges = {
        "error": (UIIcons.ERROR, theme.get_style("error")),
        "canceled": (UIIcons.CANCEL, theme.get_style("warning")),
        "success": (UIIcons.SUCCESS, theme.get_style("success")),
        "warning": (UIIcons.WARNING, theme.get_style("warning")),
        "info": (UIIcons.INFO, theme.get_style("info")),
    }

    icon, style = badges.get(status, (UIIcons.INFO, theme.get_style("info")))

    badge = Text()
    badge.append(f"{icon} ", style=style)

    if message:
        badge.append(message, style=style)

    return badge
