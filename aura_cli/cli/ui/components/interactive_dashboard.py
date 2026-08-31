"""Interactive dashboard for Aura CLI — keyboard-navigable data views.

InteractiveDashboard supports real-time filtering (contains/equals per column),
multi-column sorting (ASC/DESC/NONE), item selection callbacks and configurable
refresh rate. DashboardColumn and DashboardFilter are the configuration contracts.
"""

import csv
from dataclasses import dataclass
from io import StringIO
import json
from typing import Any, Callable, Dict, List, Optional

from rich.console import Console, Group, RenderableType
from rich.live import Live
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table
from rich.text import Text

from aura_cli.application.presentation.dashboard_query import (
    DashboardFilter,
    SortOrder,
    query_dashboard_rows,
)
from aura_cli.cli.ui.constants import UIIcons, UIStyles
from aura_cli.core.logger import get_logger

logger = get_logger(__name__)


@dataclass
class DashboardColumn:
    """A single column in the interactive dashboard."""

    key: str
    title: str
    width: Optional[int] = None
    sortable: bool = True
    filterable: bool = True
    formatter: Optional[Callable[[Any], str]] = None
    style: str = ""


class InteractiveDashboard:
    """Interactive keyboard-navigable Rich dashboard."""

    def __init__(
        self,
        title: str = "Dashboard",
        console: Optional[Console] = None,
        refresh_rate: float = 0.5,
    ):
        """Initialise the interactive dashboard."""
        self.title = title
        self.console = console or Console()
        self.refresh_rate = refresh_rate

        self.columns: List[DashboardColumn] = []
        self.data: List[Dict[str, Any]] = []
        self.filtered_data: List[Dict[str, Any]] = []

        self.selected_index: int = 0
        self.scroll_offset: int = 0
        self.visible_rows: int = 20

        self.sort_column: Optional[str] = None
        self.sort_order: SortOrder = SortOrder.NONE

        self.filters: List[DashboardFilter] = []
        self.search_text: str = ""

        self.show_help: bool = False
        self.show_filters: bool = False
        self.show_preview: bool = False
        self.mode: str = "normal"  # normal, filter, search

        self.on_select: Optional[Callable[[Dict], None]] = None
        self.on_action: Optional[Callable[[str, Dict], None]] = None

        self._running: bool = False

    def add_column(
        self,
        key: str,
        title: str,
        width: Optional[int] = None,
        sortable: bool = True,
        filterable: bool = True,
        formatter: Optional[Callable] = None,
        style: str = "",
    ) -> "InteractiveDashboard":
        """Add a column to the dashboard."""
        self.columns.append(
            DashboardColumn(
                key=key,
                title=title,
                width=width,
                sortable=sortable,
                filterable=filterable,
                formatter=formatter,
                style=style,
            )
        )
        return self

    def set_data(self, data: List[Dict[str, Any]]):
        """Set the dashboard data."""
        self.data = data
        self._apply_filters_and_sort()

    def add_data(self, item: Dict[str, Any]):
        """Adiciona item aos dados."""
        self.data.append(item)
        self._apply_filters_and_sort()

    def update_data(self, index: int, item: Dict[str, Any]):
        """Atualiza item nos dados."""
        if 0 <= index < len(self.data):
            self.data[index] = item
            self._apply_filters_and_sort()

    def remove_data(self, index: int):
        """Remove an item from the dashboard data."""
        if 0 <= index < len(self.data):
            self.data.pop(index)
            self._apply_filters_and_sort()

    def set_sort(self, column: str, order: SortOrder = SortOrder.ASC):
        """Set the sort column and direction."""
        self.sort_column = column
        self.sort_order = order
        self._apply_filters_and_sort()

    def toggle_sort(self, column: str):
        """Toggle column sort order."""
        if self.sort_column == column:
            if self.sort_order == SortOrder.NONE:
                self.sort_order = SortOrder.ASC
            elif self.sort_order == SortOrder.ASC:
                self.sort_order = SortOrder.DESC
            else:
                self.sort_order = SortOrder.NONE
        else:
            self.sort_column = column
            self.sort_order = SortOrder.ASC

        self._apply_filters_and_sort()

    def add_filter(self, column: str, value: str, operator: str = "contains"):
        """Adiciona filtro."""
        self.filters.append(
            DashboardFilter(column=column, value=value, operator=operator)
        )
        self._apply_filters_and_sort()

    def remove_filter(self, index: int):
        """Remove a filter by index."""
        if 0 <= index < len(self.filters):
            self.filters.pop(index)
            self._apply_filters_and_sort()

    def clear_filters(self):
        """Remove all active filters."""
        self.filters.clear()
        self.search_text = ""
        self._apply_filters_and_sort()

    def set_search(self, text: str):
        """Set the search query string."""
        self.search_text = text
        self._apply_filters_and_sort()

    def _apply_filters_and_sort(self):
        """Apply active filters and sort order to the data."""
        self.filtered_data = query_dashboard_rows(
            self.data,
            search=self.search_text,
            filters=self.filters,
            sort_column=self.sort_column,
            sort_order=self.sort_order,
        )

        if self.selected_index >= len(self.filtered_data):
            self.selected_index = max(0, len(self.filtered_data) - 1)

    def move_up(self):
        """Move selection up one row."""
        if self.selected_index > 0:
            self.selected_index -= 1
            self._ensure_visible()

    def move_down(self):
        """Move selection down one row."""
        if self.selected_index < len(self.filtered_data) - 1:
            self.selected_index += 1
            self._ensure_visible()

    def page_up(self):
        """Move selection up one page."""
        self.selected_index = max(0, self.selected_index - self.visible_rows)
        self._ensure_visible()

    def page_down(self):
        """Move selection down one page."""
        self.selected_index = min(
            len(self.filtered_data) - 1, self.selected_index + self.visible_rows
        )
        self._ensure_visible()

    def _ensure_visible(self):
        """Ensure the selected item is visible."""
        if self.selected_index < self.scroll_offset:
            self.scroll_offset = self.selected_index
        elif self.selected_index >= self.scroll_offset + self.visible_rows:
            self.scroll_offset = self.selected_index - self.visible_rows + 1

    def get_selected(self) -> Optional[Dict]:
        """Return the currently selected item."""
        if 0 <= self.selected_index < len(self.filtered_data):
            return self.filtered_data[self.selected_index]
        return None

    def _handle_sort_key(self) -> None:
        """Cycle sort column on 's' key."""
        sortable = [c for c in self.columns if c.sortable]
        if not sortable:
            return
        if self.sort_column:
            current_idx = next(
                (i for i, c in enumerate(sortable) if c.key == self.sort_column), -1
            )
            self.toggle_sort(sortable[(current_idx + 1) % len(sortable)].key)
        else:
            self.toggle_sort(sortable[0].key)

    def handle_key(self, key: str) -> Optional[str]:
        """Handle a keypress and return True if consumed."""
        if self.mode != "normal":
            return None

        # Actions that return a value
        if key == "enter":
            selected = self.get_selected()
            if selected and self.on_select:
                self.on_select(selected)
            return "select"
        if key == "/":
            self.mode = "search"
            return "search_start"
        if key in ("e", "q", "escape", "r"):
            return {"e": "export", "q": "quit", "escape": "quit", "r": "refresh"}[key]

        # Actions that mutate state
        _ACTIONS = {
            ("up", "k"): self.move_up,
            ("down", "j"): self.move_down,
            ("page_up",): self.page_up,
            ("page_down",): self.page_down,
            ("c",): self.clear_filters,
            ("s",): self._handle_sort_key,
        }
        for keys, action in _ACTIONS.items():
            if key in keys:
                action()
                return None

        if key == "home":
            self.selected_index = 0
            self._ensure_visible()
        elif key == "end":
            self.selected_index = len(self.filtered_data) - 1
            self._ensure_visible()
        elif key == "f":
            self.show_filters = not self.show_filters
        elif key in ("h", "?"):
            self.show_help = not self.show_help
        elif key == "p":
            self.show_preview = not self.show_preview

        return None

    def render(self) -> RenderableType:
        """Renderiza o dashboard."""
        table = Table(
            show_header=True,
            header_style=UIStyles.TITLE,
            box=None,
            expand=True,
            highlight=True,
        )

        for col in self.columns:
            title = col.title
            if col.sortable and self.sort_column == col.key:
                if self.sort_order == SortOrder.ASC:
                    title += f" {UIIcons.ARROW_UP}"
                elif self.sort_order == SortOrder.DESC:
                    title += f" {UIIcons.ARROW_DOWN}"

            table.add_column(
                title,
                width=col.width,
                style=col.style or UIStyles.BODY,
            )

        visible_data = self.filtered_data[
            self.scroll_offset : self.scroll_offset + self.visible_rows
        ]

        for i, item in enumerate(visible_data):
            actual_index = self.scroll_offset + i
            is_selected = actual_index == self.selected_index

            row = []
            for col in self.columns:
                value = item.get(col.key, "")
                value = col.formatter(value) if col.formatter else str(value)

                if is_selected:
                    value = f"[reverse]{value}[/reverse]"

                row.append(value)

            table.add_row(*row)

        footer_parts = []

        footer_parts.append(f"{len(self.filtered_data)}/{len(self.data)} itens")

        if self.filters:
            footer_parts.append(f"{len(self.filters)} filtros")

        if self.search_text:
            footer_parts.append(f"Busca: {self.search_text}")

        footer_parts.append("p Prévia | e Exportar | ? Ajuda | q Sair")

        footer = Text(" · ".join(footer_parts), style=UIStyles.MUTED)
        title_line = Text(f"{UIIcons.STATS} {self.title}", style=UIStyles.TITLE)

        content_parts: List[Any] = [title_line, table, footer]

        if self.show_preview and self.selected_index < len(self.filtered_data):
            preview = self._render_preview(self.filtered_data[self.selected_index])
            content_parts.append(preview)

        if self.show_help:
            help_text = self._render_help()
            content_parts.append(help_text)

        return Group(*content_parts)

    def _render_preview(self, item: Dict[str, Any]) -> RenderableType:
        """Render an expandable preview of the selected item."""

        preview_parts: list[Any] = []

        info_text = Text()
        info_text.append(
            f"{UIIcons.INFO} Detalhes do item selecionado\n\n", style=UIStyles.TITLE
        )

        for col in self.columns:
            value = item.get(col.key, "")
            value = col.formatter(value) if col.formatter else str(value)

            info_text.append(f"{col.title}: ", style=UIStyles.LABEL)
            info_text.append(f"{value}\n", style=UIStyles.BODY)

        preview_parts.append(info_text)

        if any(isinstance(v, (dict, list)) for v in item.values()):
            json_str = json.dumps(item, indent=2, default=str)
            json_syntax = Syntax(json_str, "json", theme="monokai", line_numbers=False)
            preview_parts.append(Panel(json_syntax, border_style=UIStyles.BORDER_MUTED))

        preview_parts.insert(0, Text("Prévia", style=UIStyles.TITLE))
        return Group(*preview_parts)

    def export_data(self, fmt: str = "json") -> str:
        """Export dashboard data as JSON or CSV."""
        if fmt == "json":
            return json.dumps(self.filtered_data, indent=2, default=str)

        elif fmt == "csv":
            if not self.filtered_data:
                return ""

            output = StringIO()
            writer = csv.writer(output)

            headers = [col.title for col in self.columns]
            writer.writerow(headers)

            for item in self.filtered_data:
                row = []
                for col in self.columns:
                    value = item.get(col.key, "")
                    if col.formatter:
                        value = col.formatter(value)
                    row.append(str(value))
                writer.writerow(row)

            return output.getvalue()

        return ""

    def _render_help(self) -> RenderableType:
        """Render the keyboard help line."""
        help_items = [
            ("↑/↓ ou j/k", "Navegar"),
            ("PgUp/PgDn", "Página"),
            ("Enter", "Selecionar"),
            ("/", "Buscar"),
            ("s", "Ordenar"),
            ("f", "Filtros"),
            ("c", "Limpar filtros"),
            ("r", "Atualizar"),
            ("q/Esc", "Sair"),
        ]

        text = Text()
        for key, desc in help_items:
            text.append(f"  {key}", style=UIStyles.ACCENT)
            text.append(f"  {desc}\n", style=UIStyles.BODY)

        return Group(Text("Atalhos", style=UIStyles.TITLE), text)

    def run_interactive(self):
        """Run the dashboard in interactive mode."""
        self._running = True

        try:
            with Live(
                self.render(),
                console=self.console,
                refresh_per_second=1 / self.refresh_rate,
                screen=True,
            ) as live:
                while self._running:
                    live.update(self.render())

                    import time

                    time.sleep(self.refresh_rate)
        except KeyboardInterrupt:
            self._running = False

    def stop(self):
        """Stop the interactive dashboard."""
        self._running = False

    def get_stats(self) -> Dict[str, Any]:
        """Return dashboard statistics as a dict."""
        return {
            "title": self.title,
            "columns": len(self.columns),
            "total_items": len(self.data),
            "filtered_items": len(self.filtered_data),
            "active_filters": len(self.filters),
            "sort_column": self.sort_column,
            "sort_order": self.sort_order.value if self.sort_order else None,
            "selected_index": self.selected_index,
        }
