"""Rich rendering for the authoritative workspace diff snapshot."""

from __future__ import annotations

from rich.console import Group, RenderableType
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from aura_cli.application.diffs import WorkspaceDiff


class WorkspaceDiffDisplay:
    """Render a bounded workspace diff for CLI and Rich surfaces."""

    def render(self, snapshot: WorkspaceDiff, *, max_lines: int = 40) -> RenderableType:
        """Return a compact summary plus color-coded patch preview."""
        summary = Table.grid(padding=(0, 1))
        summary.add_column(style="dim")
        summary.add_column()
        summary.add_row("Workspace", snapshot.project_root)
        summary.add_row("Files", str(len(snapshot.changed_files)))
        summary.add_row("Status", "changed" if snapshot.has_changes else "clean")
        if snapshot.truncated:
            summary.add_row("Notice", "diff truncated; use git_diff_context for full state")

        lines: list[Text] = []
        for line in snapshot.patch.splitlines()[:max_lines]:
            style = "green" if line.startswith("+") and not line.startswith("+++") else "red" if line.startswith("-") and not line.startswith("---") else "cyan" if line.startswith("@@") else "dim"
            lines.append(Text(line, style=style))
        patch = Group(*lines) if lines else Text("No changes", style="dim")
        return Panel(Group(summary, Text(), patch), title="Aura Diff", border_style="cyan")


__all__ = ["WorkspaceDiffDisplay"]
