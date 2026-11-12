"""Composite rendering for /dashboard slash subcommands."""

from __future__ import annotations

import importlib
from typing import Dict, Optional, Tuple

from rich.console import Console, RenderableType
from rich.table import Table

from aura_cli.application.presentation.cli_visual import SurfaceChrome
from aura_cli.cli.ui.composition.visual_surface import surface_panel
from aura_cli.cli.ui.constants import UIIcons, UIStyles

DashboardEntry = Tuple[str, str, str]

DASHBOARD_REGISTRY: Dict[str, DashboardEntry] = {
    "tool_history": (
        "Tool History (optional)",
        "aura_cli.cli.ui.tools.tool_history",
        "ToolHistoryViewer",
    ),
    "memory": (
        "Memory Explorer (optional)",
        "aura_cli.cli.ui.memory.memory_explorer",
        "MemoryExplorer",
    ),
    "graph": (
        "Module Graph Explorer (optional)",
        "aura_cli.cli.ui.visualization.graph_renderer",
        "GraphRenderer",
    ),
    "infra": (
        "Infrastructure / Containers (optional)",
        "aura_cli.cli.ui.ops.infrastructure_dashboard",
        "InfrastructureDashboard",
    ),
    "extensions": (
        "Extensions / Plugins (optional)",
        "aura_cli.cli.ui.extensions.extension_manager",
        "ExtensionBrowser",
    ),
    "edit": (
        "Edit History (optional)",
        "aura_cli.cli.ui.edit.edit_coordinator",
        "EditHistoryViewer",
    ),
    "refactor": (
        "Duplication Analysis (optional)",
        "aura_cli.cli.ui.refactoring.refactoring_studio",
        "DuplicationAnalyzer",
    ),
    "autocomplete": (
        "Autocomplete Suggestions (optional)",
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
    message.add_row("Status", "unavailable")
    message.add_row("Module", module_path)
    message.add_row("Reason", str(error) or "optional implementation not installed")
    message.add_row("Next step", "install/activate the extension and try again")
    console.print(
        surface_panel(
            message,
            title=f"[{UIStyles.WARNING}]{UIIcons.WARNING} {title}[/]",
            chrome=SurfaceChrome.GROUP,
            border_style=UIStyles.BORDER_WARNING,
            console_width=console.width,
        )
    )


def render_dashboard_help(console: Console) -> None:
    """Print dashboard subcommand index."""
    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column("Command", style=f"{UIStyles.ACCENT} bold", width=20)
    table.add_column("Description", style=UIStyles.BODY)
    for key, (desc, _, _) in DASHBOARD_REGISTRY.items():
        table.add_row(f"/dashboard {key}", desc)
    console.print(
        surface_panel(
            table,
            title=f"[{UIStyles.TITLE}]{UIIcons.STATS} Dashboards Opcionais[/]",
            chrome=SurfaceChrome.GROUP,
            border_style=UIStyles.BORDER_PRIMARY,
            console_width=console.width,
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
