"""Textual panel for the current workspace diff."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import VerticalScroll
from textual.widgets import Label, Static

from aura_cli.application.diffs import WorkspaceDiff


class WorkspaceDiffPanel(VerticalScroll):
    """Read-only live view of files and patch state for the active workspace."""

    def __init__(self, snapshot: WorkspaceDiff, **kwargs) -> None:
        super().__init__(**kwargs)
        self.snapshot = snapshot

    def compose(self) -> ComposeResult:
        yield Label(self._summary(), id="workspace-diff-summary")
        for line in self.snapshot.patch.splitlines():
            yield Static(line, classes=self._line_class(line))

    def update_snapshot(self, snapshot: WorkspaceDiff) -> None:
        """Replace the view after a tool or worker publishes a new snapshot."""
        self.snapshot = snapshot
        if not self.is_mounted:
            return
        self.query_one("#workspace-diff-summary", Label).update(self._summary())
        self.query(".workspace-diff-line").remove()
        for line in snapshot.patch.splitlines():
            self.mount(Static(line, classes=self._line_class(line)))

    def _summary(self) -> str:
        status = "alterado" if self.snapshot.has_changes else "limpo"
        suffix = " · truncado" if self.snapshot.truncated else ""
        return f"Aura Diff · {status} · {len(self.snapshot.changed_files)} arquivo(s){suffix}"

    @staticmethod
    def _line_class(line: str) -> str:
        if line.startswith("+") and not line.startswith("+++"):
            return "workspace-diff-line line-added"
        if line.startswith("-") and not line.startswith("---"):
            return "workspace-diff-line line-removed"
        if line.startswith(("@@", "+++", "---")):
            return "workspace-diff-line line-header"
        return "workspace-diff-line line-context"


__all__ = ["WorkspaceDiffPanel"]
