"""Diff Confirmation Screen — composes diff review panel."""

from __future__ import annotations

from typing import ClassVar, List, Optional, Tuple

from textual import on
from textual.app import ComposeResult
from textual.binding import Binding
from textual.widgets import Button

from aura_cli.application.diffs import generate_new_file_diff, generate_unified_diff
from aura_cli.core.logger import get_logger
from aura_cli.tui.shell.base_modal import BaseAuraResultModalScreen
from aura_cli.tui.widgets.diff.diff_review_panel import DiffReviewPanel

logger = get_logger(__name__)

__all__ = [
    "DiffConfirmationScreen",
    "generate_new_file_diff",
    "generate_unified_diff",
]


class DiffConfirmationScreen(BaseAuraResultModalScreen[Tuple[str, Optional[str]]]):
    """Modal for reviewing unified diff before apply."""

    BINDINGS: ClassVar[list] = [
        Binding("a", "accept", "Aceitar", show=True),
        Binding("r", "reject", "Rejeitar", show=True),
        Binding("e", "edit", "Editar", show=True),
        Binding("shift+a", "accept_all", "Aceitar Todos", show=True),
        Binding("escape", "reject", "Cancelar"),
    ]
    MODAL_ROOT_ID = "diff-dialog-root"

    def __init__(
        self,
        file_path: str = "",
        diff_lines: Optional[List[str]] = None,
        new_content: Optional[str] = None,
        *,
        diff_text: Optional[str] = None,
        name: Optional[str] = None,
        id: Optional[str] = None,
        classes: Optional[str] = None,
    ):
        super().__init__(name=name, id=id, classes=classes)
        if diff_text is not None:
            diff_lines = diff_text.splitlines()
            if not file_path:
                file_path = "file"
        self.file_path = file_path or "file"
        self.diff_lines = diff_lines or []
        self.new_content = new_content

    def compose_body(self) -> ComposeResult:
        yield DiffReviewPanel(self.file_path, self.diff_lines)

    @on(Button.Pressed, "#accept")
    def handle_accept(self, event: Button.Pressed) -> None:
        logger.info(f"Alterações aceitas para {self.file_path}")
        self.dismiss(("accept", self.new_content))

    @on(Button.Pressed, "#reject")
    def handle_reject(self, event: Button.Pressed) -> None:
        logger.info(f"Alterações rejeitadas para {self.file_path}")
        self.dismiss(("reject", None))

    @on(Button.Pressed, "#edit")
    def handle_edit(self, event: Button.Pressed) -> None:
        logger.info(f"Edição solicitada para {self.file_path}")
        self.dismiss(("edit", self.new_content))

    @on(Button.Pressed, "#accept_all")
    def handle_accept_all(self, event: Button.Pressed) -> None:
        logger.info("Aceitar todas as alterações ativado")
        self.dismiss(("accept_all", self.new_content))

    def action_accept(self) -> None:
        self.dismiss(("accept", self.new_content))

    def action_reject(self) -> None:
        self.dismiss(("reject", None))

    def action_edit(self) -> None:
        self.dismiss(("edit", self.new_content))

    def action_accept_all(self) -> None:
        self.dismiss(("accept_all", self.new_content))
