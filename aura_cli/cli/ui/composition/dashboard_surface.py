"""Composite rendering for /dashboard slash subcommands."""

from __future__ import annotations

import importlib
from typing import Dict, Optional, Tuple

from rich.console import Console, RenderableType
from rich.panel import Panel
from rich.table import Table

from aura_cli.cli.ui.constants import UIIcons, UIStyles

DashboardEntry = Tuple[str, str, str]

DASHBOARD_REGISTRY: Dict[str, DashboardEntry] = {
    "tool_history": (
        "Histórico de Ferramentas (opcional)",
        "aura_cli.cli.ui.tools.tool_history",
        "ToolHistoryViewer",
    ),
    "memory": (
        "Explorador de Memória (opcional)",
        "aura_cli.cli.ui.memory.memory_explorer",
        "MemoryExplorer",
    ),
    "graph": (
        "Explorador de Grafo de Módulos (opcional)",
        "aura_cli.cli.ui.visualization.graph_renderer",
        "GraphRenderer",
    ),
    "infra": (
        "Infraestrutura / Containers (opcional)",
        "aura_cli.cli.ui.ops.infrastructure_dashboard",
        "InfrastructureDashboard",
    ),
    "extensions": (
        "Extensões / Plugins (opcional)",
        "aura_cli.cli.ui.extensions.extension_manager",
        "ExtensionBrowser",
    ),
    "edit": (
        "Histórico de Edições (opcional)",
        "aura_cli.cli.ui.edit.edit_coordinator",
        "EditHistoryViewer",
    ),
    "refactor": (
        "Análise de Duplicações (opcional)",
        "aura_cli.cli.ui.refactoring.refactoring_studio",
        "DuplicationAnalyzer",
    ),
    "autocomplete": (
        "Sugestões de Autocomplete (opcional)",
        "aura_cli.cli.ui.autocomplete.autocomplete_widget",
        "AutocompleteWidget",
    ),
}


def _render_dashboard_unavailable(
    console: Console, key: str, entry: DashboardEntry, error: Exception
) -> None:
    """Explain an unavailable optional dashboard without breaking the CLI flow."""
    title, module_path, _class_name = entry
    message = Table.grid(padding=(0, 1))
    message.add_row("Dashboard", key)
    message.add_row("Estado", "indisponível")
    message.add_row("Módulo", module_path)
    message.add_row("Motivo", str(error) or "implementação opcional não instalada")
    message.add_row("Próximo passo", "instale/ative a extensão e tente novamente")
    console.print(
        Panel(
            message,
            title=f"[{UIStyles.WARNING}]{UIIcons.WARNING} {title}[/]",
            border_style=UIStyles.BORDER_WARNING,
        )
    )


def render_dashboard_help(console: Console) -> None:
    """Print dashboard subcommand index."""
    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column("Comando", style=f"{UIStyles.ACCENT} bold", width=20)
    table.add_column("Descrição", style=UIStyles.BODY)
    for key, (desc, _, _) in DASHBOARD_REGISTRY.items():
        table.add_row(f"/dashboard {key}", desc)
    console.print(
        Panel(
            table,
            title=f"[{UIStyles.TITLE}]{UIIcons.STATS} Dashboards Opcionais[/]",
            border_style=UIStyles.BORDER_PRIMARY,
        )
    )


def render_dashboard_subcommand(
    console: Console, subcmd: str
) -> Optional[RenderableType]:
    """
    Load and render a dashboard subcommand.

    Returns None when help was shown or subcmd is invalid.
    """
    key = subcmd.strip().lower()
    if not key or key == "help" or key not in DASHBOARD_REGISTRY:
        render_dashboard_help(console)
        return None

    entry = DASHBOARD_REGISTRY[key]
    _title, module_path, class_name = entry
    try:
        mod = importlib.import_module(module_path)
        cls = getattr(mod, class_name)
        instance = cls()
        return instance.render(console)
    except (ImportError, AttributeError) as error:
        _render_dashboard_unavailable(console, key, entry, error)
        return None
