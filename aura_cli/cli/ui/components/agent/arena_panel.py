"""Compact Rich status panel for an Arena run."""

from __future__ import annotations

from rich.panel import Panel
from rich.table import Table


def render_arena_panel(status: dict) -> Panel:
    """Render a serializable Arena status payload for the existing worker feed."""
    table = Table.grid(padding=(0, 1))
    table.add_column(style="cyan")
    table.add_column()
    table.add_row("Run", str(status.get("run_id", "—")))
    table.add_row("Phase", str(status.get("phase", "—")))
    table.add_row("Round", str(status.get("round", 0)))
    table.add_row("Alive", f"{len(status.get('alive', []))}/{status.get('agents', 0)}")
    table.add_row("Matches", str(status.get("matches", 0)))
    return Panel(table, title="Arena", border_style="magenta")
