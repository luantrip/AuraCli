"""
AuraLCDDisplay - Clean, minimal code/output display component.

Provides a professional container for displaying logs, code, or command output
with optional line numbers and syntax highlighting.
"""

from typing import Optional, Union

from rich.console import Group
from rich.syntax import Syntax
from rich.table import Table
from rich.text import Text

from aura_cli.cli.ui.components.base import ComponentBase
from aura_cli.cli.ui.components.section_header import AuraSectionHeader
from aura_cli.cli.ui.constants import Indent
from aura_cli.cli.ui.theme_manager import get_theme_manager


class AuraLCDDisplay(ComponentBase):
    """
    Clean display component for code/output visualization.

    Features:
    - Optional line numbers
    - Syntax highlighting
    - Minimal, professional design
    - Truncation with indicator
    """

    def render(
        self,
        content: Union[str, Text, Syntax],
        title: str = "OUTPUT",
        format_type: str = "text",
        line_numbers: bool = True,
        max_height: Optional[int] = 20,
        variant: str = "primary",
        metadata: Optional[str] = None,
    ) -> Group:
        """
        Render the display with minimal styling.

        Args:
            content: The content (text or rich object).
            title: Display title.
            format_type: Format type for syntax highlighting.
            line_numbers: Whether to show line numbers.
            max_height: Maximum lines before truncating.
            variant: Color variant (primary, success, error).
            metadata: Extra metadata text.

        Returns:
            Group with formatted content.
        """
        theme = get_theme_manager()

        muted = theme.get_color("muted")

        # Build header line
        section_header = AuraSectionHeader()
        header = section_header.render(title.upper(), metadata=metadata)
        header.append(" ", style=f"dim {muted}")

        # Prepare content
        if isinstance(content, str):
            raw_lines = content.splitlines()

            if format_type != "text":
                syntax_theme = theme.get_appearance_property("syntax_theme", "monokai")
                renderable_content = Syntax(
                    content,
                    format_type,
                    theme=syntax_theme,
                    line_numbers=line_numbers,
                    word_wrap=True,
                )
                # Return early with syntax highlighting
                return Group(
                    header,
                    Text(),
                    renderable_content,
                    self._render_footer(raw_lines, max_height, theme),
                )
            else:
                raw_lines = content.splitlines()
        elif isinstance(content, Text):
            raw_lines = content.plain.splitlines()
        else:
            # Fallback for other renderables
            return Group(header, Text(), content)

        # Build content table with optional line numbers
        num_lines = len(raw_lines)
        display_limit = min(num_lines, max_height) if max_height else num_lines

        content_table = Table.grid(padding=0)

        if line_numbers:
            content_table.add_column(
                justify="right",
                style=f"dim {muted}",
                width=len(str(display_limit)) + 1,
            )
            content_table.add_column(style=f"dim {muted}", width=2)

        content_table.add_column(ratio=1)

        for i in range(display_limit):
            line_content = raw_lines[i] if i < len(raw_lines) else ""
            styled_line = Text(line_content, style=theme.get_style("body"))

            if line_numbers:
                line_num = Text(str(i + 1), style=f"dim {muted}")
                separator = Text("│ ", style=f"dim {muted}")
                content_table.add_row(line_num, separator, styled_line)
            else:
                content_table.add_row(styled_line)

        # Truncation indicator
        footer = self._render_footer(raw_lines, max_height, theme)

        return Group(header, Text(), content_table, footer)

    def _render_footer(self, raw_lines: list, max_height: Optional[int], theme) -> Text:
        """Render footer with truncation indicator if needed."""
        footer = Text()
        num_lines = len(raw_lines)

        if max_height and num_lines > max_height:
            remaining = num_lines - max_height
            footer.append(
                f"{Indent.NESTED}⋯ {remaining} more lines",
                style=f"dim {theme.get_color('muted')}",
            )

        return footer
