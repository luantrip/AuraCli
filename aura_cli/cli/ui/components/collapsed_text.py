"""
CollapsedTextDisplay - Component for displaying collapsed large text inputs.

Provides a clean, minimal visual representation for large pasted content,
similar to modern chat interfaces like Cursor/Claude. Styled to integrate
with Aura chat (theme colors, padding aligned with user messages).

Features:
    - Clean collapsed indicator without noise
    - Theme-aware styling (border, label, muted) for chat consistency
    - Shows essential info: line count and size
    - Optional left padding to align with chat message content
    - No preview by default (keeps chat clean)

Usage:
    >>> from aura_cli.cli.ui.components.collapsed_text import CollapsedTextDisplay
    >>> collapsed = CollapsedTextDisplay()
    >>> rendered = collapsed.render(long_text, label="Entrada")
"""

from typing import Any

import rich.box
from rich.console import Group, RenderableType
from rich.padding import Padding
from rich.panel import Panel
from rich.text import Text

from aura_cli.cli.ui.components.base import ComponentBase
from aura_cli.cli.ui.constants import Indent
from aura_cli.cli.ui.theme_manager import get_theme_manager

CHAR_THRESHOLD = 500  # Collapse if more than 500 chars
LINE_THRESHOLD = 10  # Collapse if more than 10 lines


def should_collapse(text: str) -> bool:
    """
    Determine if text should be collapsed.

    Args:
        text: Text to check

    Returns:
        True if text should be collapsed
    """
    if not text:
        return False
    return len(text) > CHAR_THRESHOLD or text.count("\n") > LINE_THRESHOLD


class CollapsedTextDisplay(ComponentBase):
    """
    Component for rendering collapsed large text inputs.

    Displays large text in a clean, minimal format showing:
    - A subtle indicator that content was pasted
    - Line count and size

    Example:
        >>> display = CollapsedTextDisplay()
        >>> collapsed = display.render(long_code)
        >>> console.print(collapsed)
    """

    def render(
        self,
        content: str,
        label: str = "Entrada",
        show_preview: bool = False,
        preview_lines: int = 2,
        show_panel: bool = True,
    ) -> RenderableType:
        """
        Render collapsed text display.

        Args:
            content: The full text content
            label: Label to show (e.g., "Entrada", "Entrada #1")
            show_preview: Whether to show preview lines (default False for cleaner look)
            preview_lines: Number of preview lines to show
            show_panel: Whether to wrap in a styled container

        Returns:
            Rich-renderable collapsed text indicator
        """
        theme = get_theme_manager()
        muted = theme.get_style("label") or "dim"
        border_style = theme.get_color("muted") or "dim"

        lines = content.splitlines()
        line_count = len(lines)
        size_bytes = len(content.encode("utf-8"))

        if size_bytes >= 1024 * 1024:
            size_str = f"{size_bytes / (1024 * 1024):.1f} MB"
        elif size_bytes >= 1024:
            size_str = f"{size_bytes / 1024:.1f} KB"
        else:
            size_str = f"{size_bytes} B"

        indicator = Text()
        indicator.append("◇ ", style=muted)
        indicator.append(f"{label}", style=f"bold {muted}")
        indicator.append("  ·  ", style=muted)
        indicator.append(f"{line_count} linhas", style=muted)
        indicator.append("  ·  ", style=muted)
        indicator.append(size_str, style=muted)

        if show_preview and line_count > 0:
            elements = [indicator]

            preview_text = Text()
            preview_text.append("\n\n", style=muted)

            for i, line in enumerate(lines[:preview_lines]):
                if i > 0:
                    preview_text.append("\n")
                display_line = line[:70] + "…" if len(line) > 70 else line
                preview_text.append(f"  {display_line}", style=f"dim italic {muted}")

            if line_count > preview_lines:
                remaining = line_count - preview_lines
                preview_text.append("\n")
                preview_text.append(f"{Indent.CORE}⋯ +{remaining} linhas", style=muted)

            elements.append(preview_text)
            content_group: Any = Group(*elements)
        else:
            content_group = indicator

        if show_panel:
            return Panel(
                content_group,
                border_style=border_style,
                box=rich.box.ROUNDED,
                padding=(0, 1),
                expand=False,
            )

        return content_group

    def render_minimal(
        self,
        content: str,
        label: str = "Entrada",
        for_chat: bool = True,
    ) -> RenderableType:
        """
        Render an ultra-minimal collapsed indicator for chat.

        Single line: ◇ Entrada #N · X linhas · Y KB
        When for_chat=True, adds left padding to align with chat message content.

        Args:
            content: The full text content
            label: Label to show (e.g. "Entrada #1")
            for_chat: If True, wrap with padding to align with the canonical chat bubble content

        Returns:
            Minimal collapsed indicator
        """
        theme = get_theme_manager()
        muted = theme.get_style("label") or "dim"
        border_style = theme.get_color("muted") or "dim"

        lines = content.splitlines()
        line_count = len(lines)
        size_bytes = len(content.encode("utf-8"))

        if size_bytes >= 1024 * 1024:
            size_str = f"{size_bytes / (1024 * 1024):.1f} MB"
        elif size_bytes >= 1024:
            size_str = f"{size_bytes / 1024:.1f} KB"
        else:
            size_str = f"{size_bytes} B"

        indicator = Text()
        indicator.append("◇ ", style=muted)
        indicator.append(f"{label}", style=theme.get_style("primary") or "bold dim")
        indicator.append("  ·  ", style=muted)
        indicator.append(f"{line_count} linhas", style=muted)
        indicator.append("  ·  ", style=muted)
        indicator.append(size_str, style=muted)

        panel = Panel(
            indicator,
            border_style=border_style,
            box=rich.box.ROUNDED,
            padding=(0, 1),
            expand=False,
        )
        if for_chat:
            return Padding(panel, (0, 2, 0, 0))
        return panel


def render_collapsed_input(
    content: str,
    label: str = "Entrada",
    minimal: bool = True,
    for_chat: bool = True,
) -> RenderableType:
    """
    Convenience function to render collapsed text.

    Args:
        content: Text content
        label: Display label (e.g. "Entrada #1")
        minimal: Use minimal single-line style (default True)
        for_chat: When True, add padding to align with chat (default True)

    Returns:
        Rendered collapsed text
    """
    display = CollapsedTextDisplay()
    if minimal:
        return display.render_minimal(content, label=label, for_chat=for_chat)
    return display.render(content, label=label, show_preview=False)


def format_user_input_display(content: str, input_number: int = 1) -> RenderableType:
    """
    Format user input for display, collapsing if needed.

    This is the main function to use when displaying user input.
    Small inputs are shown as-is, large inputs are collapsed with
    chat-aligned styling.

    Args:
        content: User input content
        input_number: Sequential input number for label

    Returns:
        Formatted display (either plain text or collapsed)
    """
    if should_collapse(content):
        display = CollapsedTextDisplay()
        return display.render_minimal(
            content,
            label=f"Entrada #{input_number}",
            for_chat=True,
        )
    theme = get_theme_manager()
    return Text(content, style=theme.get_style("body"))
