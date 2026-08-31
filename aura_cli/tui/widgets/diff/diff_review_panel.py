"""Diff review UI (decomposed from DiffConfirmationScreen)."""

from __future__ import annotations

from typing import List

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.widgets import Button, Label, Static


class DiffReviewPanel(Vertical):
    """Header, stats, scrollable diff, and action buttons."""

    def __init__(
        self,
        file_path: str,
        diff_lines: List[str],
        **kwargs,
    ) -> None:
        super().__init__(id="diff-dialog", **kwargs)
        self.file_path = file_path
        self.diff_lines = diff_lines
        self.additions = sum(
            1
            for line in diff_lines
            if line and line.startswith("+") and not line.startswith("+++")
        )
        self.deletions = sum(
            1
            for line in diff_lines
            if line and line.startswith("-") and not line.startswith("---")
        )

    def compose(self) -> ComposeResult:
        with Horizontal(id="diff-header"):
            yield Label(f"✎ Alterações em: {self.file_path}")
        with Horizontal(id="diff-stats"):
            yield Static(f"+{self.additions} adições", classes="stat-added")
            yield Static("  ")
            yield Static(f"-{self.deletions} remoções", classes="stat-removed")
        yield VerticalScroll(id="diff-display")
        with Horizontal(id="button-bar"):
            yield Button(
                "✔ Aceitar (A)", variant="success", id="accept", classes="accept"
            )
            yield Button(
                "✖ Rejeitar (R)", variant="error", id="reject", classes="reject"
            )
            yield Button("✎ Editar (E)", variant="primary", id="edit", classes="edit")
            yield Button(
                "⟳ Aceitar Todos (Shift+A)",
                variant="warning",
                id="accept_all",
                classes="accept-all",
            )

    def on_mount(self) -> None:
        diff_display = self.query_one("#diff-display", VerticalScroll)
        for line in self.diff_lines:
            if line is None:
                continue
            if line.startswith("+") and not line.startswith("+++"):
                diff_display.mount(Static(line, classes="diff-line line-added"))
            elif line.startswith("-") and not line.startswith("---"):
                diff_display.mount(Static(line, classes="diff-line line-removed"))
            elif line.startswith(("@@", "+++", "---")):
                diff_display.mount(Static(line, classes="diff-line line-header"))
            else:
                diff_display.mount(Static(line, classes="diff-line line-context"))
        self.query_one("#accept", Button).focus()
