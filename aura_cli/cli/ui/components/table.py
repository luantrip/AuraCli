"""
Componente AuraTable - Uma tabela padronizada para a UI.
"""

from typing import Any, Dict, List

import rich.box as box
from rich.table import Table

from aura_cli.cli.ui.components.base import ComponentBase
from aura_cli.cli.ui.theme_manager import get_theme_manager


class AuraTable(ComponentBase):
    """
    Um componente de tabela padronizado que usa o sistema de temas.
    """

    def render(
        self,
        title: str,
        columns: List[Dict[str, Any]],
        rows: List[List[Any]],
        *,
        variant: str = "default",
    ) -> Table:
        """
        Render data in a styled table.

        Args:
            title: Table title.
            columns: A list of dicts, where each dict representa
                     uma coluna (ex: {"header": "Nome", "style": "cyan"}).
            rows: Uma lista de listas, onde cada lista interna representa uma linha.
            variant: A variante de estilo a ser usada.

        Returns:
            Um objeto Table estilizado.
        """
        theme = get_theme_manager()

        border_style_map = {
            "default": "border_primary",
            "success": "border_success",
        }
        border_style_name = border_style_map.get(variant, "border_primary")
        style = theme.get_style(border_style_name)

        border_type_name = theme.get_appearance_property(
            "panel_border_type", "round"
        ).upper()
        border_box = getattr(box, border_type_name, box.ROUNDED)

        table = Table(
            title=title,
            box=border_box,
            border_style=style,
            show_header=True,
            header_style=theme.get_style("bold " + style),
        )

        for col in columns:
            table.add_column(col.get("header", ""), style=col.get("style"))

        for row in rows:
            str_row = [str(item) for item in row]
            table.add_row(*str_row)

        return table
