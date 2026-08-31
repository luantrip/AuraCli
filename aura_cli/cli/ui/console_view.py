"""Console/history view for Aura CLI — LLM interaction history visualisation.

ConsoleHistory maintains a complete record of interactions (prompt, response,
tool calls, status, timing). display_interaction_list() renders the list;
individual interactions can be expanded for full detail. Singleton via
get_console_history().
"""

from datetime import timedelta
import time
from typing import Any, Dict, List, Optional, Union

from rich.columns import Columns
from rich.console import Console, Group, RenderableType
from rich.layout import Layout
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table
from rich.text import Text

from aura_cli.application.presentation import (
    ConsoleHistory,
    Interaction,
    InteractionStatus,
    export_interactions,
    filter_interactions,
    summarize_interactions,
)
from aura_cli.application.presentation.safe_payloads import safe_tool_args_json
from aura_cli.cli.ui.constants import UIIcons, UIStyles
from aura_cli.cli.ui.display_facade import get_console
from aura_cli.cli.ui.layout_contract import layout_for_width

_console_history = ConsoleHistory()
# Compatible and patchable alias; the source remains the unique facade.
console = get_console()
_STATUS_LABELS = {
    "running": "executando",
    "success": "concluída",
    "error": "com erro",
    "cancelled": "cancelada",
}


def _resolve_console(output_console: Optional[Console]) -> Console:
    """Resolve the console instance to use."""
    return output_console if output_console is not None else console


def get_console_history() -> ConsoleHistory:
    """Return the global ConsoleHistory singleton."""
    return _console_history


def format_timestamp(timestamp: float) -> str:
    """Format a timestamp for display."""
    import datetime

    dt = datetime.datetime.fromtimestamp(timestamp)
    return dt.strftime("%H:%M:%S.%")[:-3]  # Milliseconds with 3 digits


def get_status_icon(status: InteractionStatus) -> str:
    """Return the icon for an interaction status."""
    icons = {
        InteractionStatus.RUNNING: UIIcons.LOADING,
        InteractionStatus.SUCCESS: UIIcons.SUCCESS,
        InteractionStatus.ERROR: UIIcons.ERROR,
        InteractionStatus.CANCELLED: UIIcons.CANCEL,
    }
    return icons.get(status, UIIcons.INFO)


def get_status_color(status: InteractionStatus) -> str:
    """Return the Rich colour string for an interaction status."""
    colors = {
        InteractionStatus.RUNNING: UIStyles.WARNING,
        InteractionStatus.SUCCESS: UIStyles.SUCCESS,
        InteractionStatus.ERROR: UIStyles.ERROR,
        InteractionStatus.CANCELLED: UIStyles.WARNING,
    }
    return colors.get(status, UIStyles.MUTED)


def display_interaction_list(
    selected_id: Optional[str] = None,
    output_console: Optional[Console] = None,
) -> None:
    """Display the interaction list with optional selection."""
    target_console = _resolve_console(output_console)
    history = get_console_history()

    if not history.interactions:
        target_console.print(
            f"[{UIStyles.MUTED}]Nenhuma interação ainda[/{UIStyles.MUTED}]"
        )
        return

    header = Text(
        f"{UIIcons.STATS} Histórico de interação",
        style=UIStyles.TITLE,
    )
    target_console.print(header)
    table = Table(
        show_header=True,
        header_style=UIStyles.SUBTITLE,
        box=None,
        width=target_console.width,
    )

    table.add_column("Estado", width=3)
    table.add_column("Hora", width=12)
    table.add_column("Tipo", width=15)
    table.add_column("Entrada", style=UIStyles.BODY)

    for interaction in history.interactions:
        is_selected = interaction.id == selected_id
        status_icon = get_status_icon(interaction.status)
        status_color = get_status_color(interaction.status)

        interaction_type = "Chat"
        if interaction.tool_calls:
            interaction_type = f"Ferramentas ({len(interaction.tool_calls)})"

        prompt_preview = (
            interaction.prompt[:50] + "..."
            if len(interaction.prompt) > 50
            else interaction.prompt
        )

        style = UIStyles.BODY
        if is_selected:
            style = UIStyles.PRIMARY + " bold"

        table.add_row(
            f"[{status_color}]{status_icon}[/{status_color}]",
            format_timestamp(interaction.timestamp),
            interaction_type,
            prompt_preview,
            style=style,
        )

    target_console.print(table)


def display_interaction_details(
    interaction_id: str,
    output_console: Optional[Console] = None,
) -> None:
    """Display expanded details for a specific interaction."""
    target_console = _resolve_console(output_console)
    history = get_console_history()
    interaction = history.get_interaction(interaction_id)

    if not interaction:
        target_console.print(
            f"[{UIStyles.ERROR}]{UIIcons.ERROR} Interação não encontrada[/{UIStyles.ERROR}]"
        )
        return

    status_icon = get_status_icon(interaction.status)
    status_color = get_status_color(interaction.status)

    header = f"{status_icon} Interação {interaction.id[:8]}"

    content = Text()

    content.append(
        f"Hora: {format_timestamp(interaction.timestamp)}\n", style=UIStyles.MUTED
    )
    content.append("Estado: ", style=UIStyles.MUTED)
    content.append(f"{interaction.status.value}\n", style=status_color)
    content.append("\n")

    content.append(
        "Entrada:\n",
        style=UIStyles.SUBTITLE,
    )
    content.append(f"{interaction.prompt}\n", style=UIStyles.BODY)
    content.append("\n")

    if interaction.response:
        content.append(
            "Resposta:\n",
            style=UIStyles.SUBTITLE,
        )
        content.append(
            (
                f"{interaction.response[:500]}...\n"
                if len(interaction.response) > 500
                else f"{interaction.response}\n"
            ),
            style=UIStyles.BODY,
        )
        content.append("\n")

    if interaction.prompt_tokens > 0 or interaction.generated_tokens > 0:
        content.append(
            "Estatísticas:\n",
            style=UIStyles.SUBTITLE,
        )
        content.append(
            f"Tokens de entrada: {interaction.prompt_tokens}\n", style=UIStyles.BODY
        )
        content.append(
            f"Tokens gerados: {interaction.generated_tokens}\n", style=UIStyles.BODY
        )
        if interaction.execution_time > 0:
            content.append(
                f"Tempo de execução: {interaction.execution_time:.2f}s\n",
                style=UIStyles.BODY,
            )
        content.append("\n")

    if interaction.tool_calls:
        content.append(
            f"Chamadas de tools ({len(interaction.tool_calls)}):\n",
            style=UIStyles.SUBTITLE,
        )
        for i, tool_call in enumerate(interaction.tool_calls, 1):
            tool_name = tool_call.get("name", "unknown")
            content.append(f"  {i}. {UIIcons.TOOL} {tool_name}\n", style=UIStyles.BODY)
        content.append("\n")

    if interaction.error:
        content.append("Erro:\n", style=UIStyles.ERROR)
        content.append(f"{interaction.error}\n", style=UIStyles.ERROR)

    header_text = Text(header, style=f"bold {status_color}")
    target_console.print(header_text)
    target_console.print(content)


def display_console_view(
    selected_id: Optional[str] = None,
    output_console: Optional[Console] = None,
) -> None:
    """Display the full interactive console view."""
    display_interaction_list(selected_id, output_console=output_console)

    if selected_id:
        display_interaction_details(selected_id, output_console=output_console)
    elif get_console_history().interactions:
        last_interaction = get_console_history().interactions[-1]
        display_interaction_details(last_interaction.id, output_console=output_console)


class InteractiveConsoleDashboard:
    """Interactive dashboard for viewing interaction history."""

    def __init__(self, history: Optional[ConsoleHistory] = None):
        """Initialize the instance."""
        self.history = history or get_console_history()
        self.search_query: str = ""
        self.status_filter: Optional[InteractionStatus] = None
        self.type_filter: Optional[str] = None  # "Chat" or "Tools"
        self.date_filter: Optional[timedelta] = None  # Last N hours/days
        self.selected_id: Optional[str] = None

    def set_search(self, query: str):
        """Set the search query filter."""
        self.search_query = query.lower()

    def set_status_filter(self, status: Optional[InteractionStatus]):
        """Set the status filter."""
        self.status_filter = status

    def set_type_filter(self, interaction_type: Optional[str]):
        """Set the type filter."""
        self.type_filter = interaction_type

    def set_date_filter(self, hours: Optional[int]):
        """Set the date filter (last N hours)."""
        if hours:
            self.date_filter = timedelta(hours=hours)
        else:
            self.date_filter = None

    def _filter_interactions(self) -> List[Interaction]:
        """Filter interactions based on active filters."""
        cutoff = (
            time.time() - self.date_filter.total_seconds() if self.date_filter else None
        )
        return filter_interactions(
            self.history.interactions,
            query=self.search_query,
            status=self.status_filter,
            interaction_type=self.type_filter,
            cutoff_timestamp=cutoff,
        )

    def _get_statistics(self, interactions: List[Interaction]) -> Dict[str, Any]:
        """Calculate aggregate statistics."""
        return summarize_interactions(interactions)

    def render_statistics_panel(
        self, stats: Dict[str, Any], console_width: int = 80
    ) -> RenderableType:
        """Render the statistics panel with responsive padding."""
        stats_text = Text()
        stats_text.append(f"{UIIcons.STATS} Estatísticas\n\n", style=UIStyles.TITLE)

        stats_text.append("Total: ", style=UIStyles.LABEL)
        stats_text.append(f"{stats['total']}\n", style=UIStyles.PRIMARY + " bold")

        if stats["by_status"]:
            stats_text.append("\nPor estado:\n", style=UIStyles.SUBTITLE)
            for status, count in sorted(stats["by_status"].items()):
                status_icon = get_status_icon(InteractionStatus[status.upper()])
                status_color = get_status_color(InteractionStatus[status.upper()])
                stats_text.append(f"  {status_icon} ", style=status_color)
                stats_text.append(
                    f"{_STATUS_LABELS.get(status, status)}: ",
                    style=UIStyles.LABEL,
                )
                stats_text.append(f"{count}\n", style=UIStyles.PRIMARY)

        stats_text.append("\nPor tipo:\n", style=UIStyles.SUBTITLE)
        stats_text.append("  Chat: ", style=UIStyles.LABEL)
        stats_text.append(f"{stats['by_type']['Chat']}\n", style=UIStyles.INFO)
        stats_text.append("  Ferramentas: ", style=UIStyles.LABEL)
        stats_text.append(f"{stats['by_type']['Tools']}\n", style=UIStyles.ACCENT)

        if stats["total_tokens"] > 0:
            stats_text.append("Tokens totais: ", style=UIStyles.LABEL)
            stats_text.append(f"{stats['total_tokens']:,}\n", style=UIStyles.PRIMARY)

        if stats["avg_execution_time"] > 0:
            stats_text.append("Tempo médio: ", style=UIStyles.LABEL)
            stats_text.append(
                f"{stats['avg_execution_time']:.2f}s\n", style=UIStyles.INFO
            )

        return stats_text

    def render_interaction_list_table(
        self,
        interactions: List[Interaction],
        max_rows: int = 20,
        console_width: int = 80,
    ) -> Union[Table, Group]:
        """Render the interaction list table with search and filters."""
        header = Text(
            f"{UIIcons.STATS} Histórico de interação",
            style=UIStyles.TITLE,
        )
        table = Table(
            show_header=True,
            header_style=UIStyles.SUBTITLE,
            box=None,
            width=console_width,
        )

        table.add_column("Estado", width=3)
        table.add_column("Hora", width=12)
        table.add_column("Tipo", width=15)
        table.add_column("Entrada", style=UIStyles.BODY)

        display_interactions = (
            interactions[-max_rows:] if len(interactions) > max_rows else interactions
        )

        for interaction in display_interactions:
            is_selected = interaction.id == self.selected_id
            status_icon = get_status_icon(interaction.status)
            status_color = get_status_color(interaction.status)

            interaction_type = "Chat"
            if interaction.tool_calls:
                interaction_type = f"Ferramentas ({len(interaction.tool_calls)})"

            prompt_preview = (
                interaction.prompt[:50] + "..."
                if len(interaction.prompt) > 50
                else interaction.prompt
            )

            if self.search_query and self.search_query in prompt_preview.lower():
                prompt_preview = prompt_preview.replace(
                    self.search_query,
                    f"[{UIStyles.ACCENT}]{self.search_query}[/{UIStyles.ACCENT}]",
                )

            style = UIStyles.BODY
            if is_selected:
                style = UIStyles.PRIMARY + " bold"

            table.add_row(
                f"[{status_color}]{status_icon}[/{status_color}]",
                format_timestamp(interaction.timestamp),
                interaction_type,
                prompt_preview,
                style=style,
            )

        if len(interactions) > max_rows:
            footer = Text()
            footer.append(
                f"\n[{UIStyles.MUTED}]Mostrando {max_rows} de {len(interactions)} interações",
                style=UIStyles.MUTED,
            )
            if (
                self.search_query
                or self.status_filter
                or self.type_filter
                or self.date_filter
            ):
                footer.append(" (filtrado)", style=UIStyles.WARNING)
            return Group(header, table, footer)

        return Group(header, table)

    def render_interaction_details_rich(
        self, interaction: Interaction, console_width: int = 80
    ) -> RenderableType:
        """Render interaction details with rich preview."""
        from rich.syntax import Syntax

        status_icon = get_status_icon(interaction.status)
        status_color = get_status_color(interaction.status)

        header_parts = []
        header_parts.append(f"{status_icon} Interação {interaction.id[:8]}")

        if interaction.execution_time > 0:
            header_parts.append(f"({interaction.execution_time:.2f}s)")

        header = " ".join(header_parts)

        content_parts: List[Any] = []
        metadata_cols: List[Any] = []
        time_text = Text()
        time_text.append("Hora: ", style=UIStyles.MUTED)
        time_text.append(format_timestamp(interaction.timestamp), style=UIStyles.BODY)
        metadata_cols.append(time_text)

        status_text = Text()
        status_text.append("Estado: ", style=UIStyles.MUTED)
        status_text.append(
            _STATUS_LABELS.get(interaction.status.value, interaction.status.value),
            style=status_color + " bold",
        )
        metadata_cols.append(status_text)

        if interaction.prompt_tokens > 0 or interaction.generated_tokens > 0:
            tokens_text = Text()
            tokens_text.append("Tokens: ", style=UIStyles.MUTED)
            tokens_text.append(
                f"{interaction.prompt_tokens + interaction.generated_tokens:,}",
                style=UIStyles.INFO,
            )
            metadata_cols.append(tokens_text)

        if metadata_cols:
            content_parts.append(Columns(metadata_cols, equal=True, expand=True))
            content_parts.append(Text())

        prompt_panel = self._render_code_or_text(
            interaction.prompt, "Prompt", language="python"
        )
        content_parts.append(prompt_panel)
        content_parts.append(Text())

        if interaction.response:
            response_panel = self._render_code_or_text(
                interaction.response, "Response", language="markdown"
            )
            content_parts.append(response_panel)
            content_parts.append(Text())

        if interaction.tool_calls:
            tool_calls_panel = self._render_tool_calls(interaction.tool_calls)
            content_parts.append(tool_calls_panel)
            content_parts.append(Text())

        if interaction.error:
            error_text = Text()
            error_text.append(
                f"{UIIcons.ERROR} Erro\n\n", style=UIStyles.ERROR + " bold"
            )
            error_syntax = Syntax(
                interaction.error, "python", theme="monokai", line_numbers=False
            )
            error_text.append(str(error_syntax))
            error_panel = Panel(
                error_text,
                border_style=UIStyles.BORDER_ERROR,
                padding=(1, 2),
            )
            content_parts.append(error_panel)

        header_text = Text(header, style=f"bold {status_color}")
        return Group(header_text, *content_parts)

    def _render_code_or_text(
        self, content: str, title: str, language: str = "text"
    ) -> Panel:
        """Render content as code or plain text."""
        looks_like_code = (
            "def " in content
            or "import " in content
            or "class " in content
            or "{" in content
            or "}" in content
        )

        if looks_like_code and len(content) < 1000:
            syntax = Syntax(content, language, theme="monokai", line_numbers=True)
            return Panel(
                syntax,
                title=f"[{UIStyles.SUBTITLE}]{title}[/{UIStyles.SUBTITLE}]",
                border_style=UIStyles.BORDER_PRIMARY,
                padding=(1, 2),
            )
        else:
            text = Text(content[:500], style=UIStyles.BODY)
            if len(content) > 500:
                text.append(
                    f"\n\n… ({len(content) - 500} caracteres)",
                    style=UIStyles.MUTED,
                )
            return Panel(
                text,
                title=f"[{UIStyles.SUBTITLE}]{title}[/{UIStyles.SUBTITLE}]",
                border_style=UIStyles.BORDER_MUTED,
                padding=(1, 2),
            )

    def _render_tool_calls(self, tool_calls: List[Dict]) -> RenderableType:
        """Renderiza tool calls com detalhes."""
        from rich.tree import Tree

        tree = Tree(
            f"{UIIcons.TOOL} Chamadas de tools ({len(tool_calls)})",
            style=UIStyles.SUBTITLE,
            guide_style=UIStyles.BORDER_PRIMARY,
        )

        for i, tool_call in enumerate(tool_calls, 1):
            tool_name = tool_call.get("name", "unknown")
            tool_args = tool_call.get("args", {})
            tool_result = tool_call.get("result")

            tool_node = tree.add(f"{i}. {UIIcons.TOOL} {tool_name}")

            if tool_args:
                args_text = safe_tool_args_json(tool_args)
                args_syntax = Syntax(
                    args_text, "json", theme="monokai", line_numbers=False
                )
                tool_node.add(Panel(args_syntax, border_style=UIStyles.BORDER_MUTED))

            if tool_result:
                result_preview = str(tool_result)[:200]
                tool_node.add(
                    Text(f"Resultado: {result_preview}...", style=UIStyles.MUTED)
                )

        return tree

    def render_dashboard(self, console_width: int = 80) -> Layout:
        """Renderiza dashboard completo usando a largura do terminal."""
        filtered = self._filter_interactions()
        stats = self._get_statistics(filtered)

        metrics = layout_for_width(console_width)
        layout = Layout()
        layout.split_column(
            Layout(name="header", size=3),
            Layout(name="main"),
            Layout(name="footer", size=3),
        )

        if metrics.narrow:
            layout["main"].split_column(
                Layout(name="left", ratio=2), Layout(name="right", ratio=1)
            )
        else:
            layout["main"].split_row(
                Layout(name="left", ratio=2), Layout(name="right", ratio=1)
            )

        header_text = Text()
        header_text.append(
            f"{UIIcons.STATS} Dashboard do histórico", style=UIStyles.TITLE
        )
        if self.search_query:
            header_text.append(f" | Busca: {self.search_query}", style=UIStyles.ACCENT)
        if self.status_filter:
            header_text.append(
                f" | Estado: {self.status_filter.value}",
                style=UIStyles.WARNING,
            )
        layout["header"].update(header_text)

        table = self.render_interaction_list_table(
            filtered, console_width=metrics.width
        )
        layout["left"].update(table)

        stats_panel = self.render_statistics_panel(stats, console_width=metrics.width)
        layout["right"].update(stats_panel)

        if self.selected_id:
            selected = self.history.get_interaction(self.selected_id)
            if selected:
                preview = self.render_interaction_details_rich(
                    selected, console_width=metrics.width
                )
                layout["footer"].update(preview)
            else:
                layout["footer"].update(
                    Text("Nenhuma interação selecionada", style=UIStyles.MUTED)
                )
        else:
            layout["footer"].update(
                Text(
                    "Selecione uma interação para ver os detalhes", style=UIStyles.MUTED
                )
            )

        return layout

    def export_history(self, fmt: str = "json") -> str:
        """Export the currently filtered history as JSON or CSV."""
        return export_interactions(self._filter_interactions(), fmt)


def display_interactive_console_dashboard() -> None:
    """Display the full interactive console dashboard."""
    dashboard = InteractiveConsoleDashboard()
    target_console = get_console()
    layout = dashboard.render_dashboard(console_width=target_console.width)
    target_console.print(layout)
