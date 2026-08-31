"""
AuraSyntax component — standardised syntax-highlighted code block.
"""

from typing import List, Optional

from rich.syntax import Syntax

from aura_cli.cli.ui.components.base import ComponentBase
from aura_cli.cli.ui.theme_manager import get_theme_manager


class AuraSyntax(ComponentBase):
    """
    Um componente de syntax highlighting que usa o sistema de temas.
    """

    def render(
        self,
        code: str,
        language: str,
        *,
        title: Optional[str] = None,
        line_numbers: bool = True,
        highlight_lines: Optional[List[int]] = None,
    ) -> Syntax:
        """
        Render a syntax-highlighted code block.

        Args:
            code: The code to render.
            language: The programming language of the code.
            title: An optional title to display.
            line_numbers: Whether to show line numbers.
            highlight_lines: A a lista de linhas a serem destacadas.

        Returns:
            Um objeto Syntax estilizado.
        """
        theme = get_theme_manager()
        syntax_theme = theme.get_appearance_property("syntax_theme", "monokai")

        return Syntax(
            code,
            language,
            theme=syntax_theme,
            line_numbers=line_numbers,
            highlight_lines=set(highlight_lines) if highlight_lines else None,
        )
