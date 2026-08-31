"""
AuraErrorDisplay Component - Standardized error message display.

Provides consistent error rendering with styled panels, icons and
optional exception details.

Features:
    - Styled Error Panels: Red-themed error panels
    - Icon Support: Error icon with message
    - Exception Details: Optional exception information
    - Consistent Formatting: Uniform error display

Usage:
    >>> from aura_cli.cli.ui.components.error_display import AuraErrorDisplay
    >>> error = AuraErrorDisplay()
    >>> rendered = error.render("File not found", exception=FileNotFoundError())
"""

import traceback
from typing import Any, Dict, List, Optional

import rich.box as box
from rich.console import Group, RenderableType
from rich.panel import Panel
from rich.syntax import Syntax
from rich.text import Text

from aura_cli.cli.ui.components.base import ComponentBase
from aura_cli.cli.ui.components.panel import AuraPanel
from aura_cli.cli.ui.constants import UIIcons, UIStyles
from aura_cli.cli.ui.layout_contract import layout_for_width
from aura_cli.cli.ui.theme_manager import get_theme_manager


class AuraErrorDisplay(ComponentBase):
    """
    Component for rendering standardized error message.

    Displays error in styled panel with icon and optional exception details.

    Example:
        >>> error = AuraErrorDisplay()
        >>> panel = error.render("Operation failed")
        >>> console.print(panel)
    """

    def render(
        self,
        error_message: str,
        *,
        exception: Optional[Exception] = None,
        context: Optional[Dict[str, Any]] = None,
        suggestions: Optional[List[str]] = None,
        show_traceback: bool = False,
        console_width: int = 80,
    ) -> RenderableType:
        """
        Render error message in styled panel; traceback only if show_traceback=True.

        Args:
            error_message: Main error message
            exception: Optional exception (details shown only if show_traceback=True)
            context: Optional context dictionary (variables, stack, etc.)
            suggestions: Optional list of suggested fixes (max 2–3 items)
            show_traceback: If True and exception given, show full traceback (default False)

        Returns:
            Styled Panel with error
        """

        theme = get_theme_manager()
        metrics = layout_for_width(console_width)
        content_parts: list[Any] = []

        # Mensagem principal
        main_text = Text()
        main_text.append(f"{UIIcons.ERROR} ", style=theme.get_style("error") + " bold")
        main_text.append(error_message, style=theme.get_style("error") + " bold")
        content_parts.append(main_text)
        if metrics.vertical_gap:
            content_parts.append(Text())

        # Default: single line only; full traceback only if show_traceback
        if exception:
            exc_msg = str(exception)
            if len(exc_msg) > 120:
                exc_msg = exc_msg[:117] + "..."
            detail = Text()
            detail.append(f"Detalhes: {exc_msg}", style=UIStyles.MUTED)
            content_parts.append(detail)
            if metrics.vertical_gap:
                content_parts.append(Text())

            if show_traceback:
                traceback_text = "".join(
                    traceback.format_exception(
                        type(exception), exception, exception.__traceback__
                    )
                )
                traceback_syntax = Syntax(
                    traceback_text, "python", theme="monokai", line_numbers=True
                )
                traceback_panel = Panel(
                    traceback_syntax,
                    title="Rastreamento",
                    border_style=UIStyles.BORDER_ERROR,
                    padding=metrics.focus_padding,
                    box=box.ROUNDED,
                )
                content_parts.append(traceback_panel)
                if metrics.vertical_gap:
                    content_parts.append(Text())

        # Contexto adicional
        if context:
            context_text = Text()
            context_text.append("Contexto:\n", style=UIStyles.SUBTITLE + " bold")
            for key, value in context.items():
                context_text.append(f"  {key}: ", style=UIStyles.LABEL)
                context_text.append(f"{value}\n", style=UIStyles.BODY)
            content_parts.append(context_text)
            if metrics.vertical_gap:
                content_parts.append(Text())

        # Suggestions (max 3 items)
        if suggestions:
            suggestions_text = Text()
            suggestions_text.append("Sugestões:\n", style=UIStyles.SUBTITLE + " bold")
            for i, suggestion in enumerate(suggestions[:3], 1):
                suggestions_text.append(f"  {i}. ", style=UIStyles.ACCENT)
                suggestions_text.append(f"{suggestion}\n", style=UIStyles.BODY)
            content_parts.append(suggestions_text)

        panel_component = AuraPanel()
        panel = panel_component.render(
            Group(*content_parts),
            title="Erro",
            status="error",
            console_width=console_width,
        )

        return panel
