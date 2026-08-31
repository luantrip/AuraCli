"""
FileDiff - Clean diff display component.

Provides minimal, readable diff display between two file versions
with statistics and color-coded changes.
"""

import difflib
from typing import List, NamedTuple

from rich.console import Group, RenderableType
from rich.text import Text

from aura_cli.cli.ui.components.base import ComponentBase
from aura_cli.cli.ui.components.section_header import AuraSectionHeader
from aura_cli.cli.ui.constants import Indent, UIIcons
from aura_cli.cli.ui.theme_manager import get_theme_manager


class DiffStats(NamedTuple):
    """Diff statistics."""

    added: int
    removed: int


class FileDiff(ComponentBase):
    """
    Clean file diff display component.

    Features:
    - Unified diff format
    - Color-coded additions/deletions
    - Statistics display
    - Configurable preview limit
    """

    def _calculate_stats(self, old_lines: List[str], new_lines: List[str]) -> DiffStats:
        """Calculate diff statistics."""
        diff = list(difflib.unified_diff(old_lines, new_lines, lineterm="", n=0))
        added = sum(
            1 for line in diff if line.startswith("+") and not line.startswith("+++")
        )
        removed = sum(
            1 for line in diff if line.startswith("-") and not line.startswith("---")
        )
        return DiffStats(added=added, removed=removed)

    def render(
        self,
        file_path: str,
        old_content: str,
        new_content: str,
        max_preview_lines: int = 50,
        show_stats: bool = True,
        *args,
        **kwargs,
    ) -> RenderableType:
        """
        Render minimal diff display.

        Args:
            file_path: Path to file
            old_content: Original content
            new_content: Modified content
            max_preview_lines: Max lines to show
            show_stats: Show statistics

        Returns:
            Formatted diff display
        """
        theme = get_theme_manager()
        muted = theme.get_color("muted")

        old_lines = old_content.splitlines()
        new_lines = new_content.splitlines()

        stats = self._calculate_stats(old_lines, new_lines)

        diff = list(
            difflib.unified_diff(
                old_lines,
                new_lines,
                fromfile=file_path,
                tofile=file_path,
                lineterm="",
                n=3,
            )
        )

        parts = []

        section_header = AuraSectionHeader()
        header_title = f"{UIIcons.EDIT} {file_path}"
        header = section_header.render(header_title)

        if show_stats and (stats.added > 0 or stats.removed > 0):
            header.append("  ", style="dim")
            if stats.added > 0:
                header.append(f"+{stats.added}", style=theme.get_color("success"))
            if stats.added > 0 and stats.removed > 0:
                header.append(" ", style="dim")
            if stats.removed > 0:
                header.append(f"-{stats.removed}", style=theme.get_color("error"))

        parts.append(header)
        parts.append(Text())

        if not diff or (stats.added == 0 and stats.removed == 0):
            parts.append(Text("  No changes", style=f"dim {muted}"))
            return Group(*parts)

        line_count = 0
        for i, line in enumerate(diff):
            if line_count >= max_preview_lines:
                remaining = len(diff) - i
                parts.append(Text())
                parts.append(
                    Text(f"{Indent.CORE}⋯ {remaining} more lines", style=f"dim {muted}")
                )
                break

            diff_line = Text()

            if line.startswith(("+++", "---")):
                continue
            elif line.startswith("+"):
                diff_line.append("  ", style="dim")
                diff_line.append("+ ", style=theme.get_color("success"))
                diff_line.append(line[1:], style=theme.get_color("success"))
            elif line.startswith("-"):
                diff_line.append("  ", style="dim")
                diff_line.append("- ", style=theme.get_color("error"))
                diff_line.append(line[1:], style=theme.get_color("error"))
            elif line.startswith("@@"):
                diff_line.append("  ", style="dim")
                diff_line.append(line, style=f"dim {theme.get_color('primary')}")
            else:
                diff_line.append("  ", style="dim")
                diff_line.append("  ", style="dim")
                diff_line.append(line, style=f"dim {muted}")

            parts.append(diff_line)
            line_count += 1

        return Group(*parts)


class FileDiffCompact(ComponentBase):
    """Compact diff summary for inline display."""

    def render(
        self,
        file_path: str,
        added: int,
        removed: int,
    ) -> Text:
        """
        Render compact diff summary.

        Args:
            file_path: File path
            added: Lines added
            removed: Lines removed

        Returns:
            Single-line summary
        """
        theme = get_theme_manager()

        summary = Text()
        summary.append(f"{UIIcons.EDIT} ", style=theme.get_style("primary"))
        summary.append(file_path, style=f"bold {theme.get_style('primary')}")
        summary.append("  ", style="dim")

        if added > 0:
            summary.append(f"+{added}", style=theme.get_color("success"))
        if added > 0 and removed > 0:
            summary.append(" ", style="dim")
        if removed > 0:
            summary.append(f"-{removed}", style=theme.get_color("error"))

        return summary
