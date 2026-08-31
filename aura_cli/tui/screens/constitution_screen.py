"""Constitution Screen — composes wizard panel on modal shell."""

from __future__ import annotations

from typing import Optional

from textual.app import ComposeResult
from textual.message import Message

from aura_cli.tui.shell.base_modal import BaseAuraResultModalScreen
from aura_cli.tui.widgets.constitution.wizard_panel import ConstitutionWizardPanel


class ConstitutionScreen(BaseAuraResultModalScreen[Optional[str]]):
    """Multi-step constitution wizard; dismisses with markdown or None."""

    TITLE = "◆  Criar Constituição do Projeto"
    INITIAL_FOCUS_SELECTOR = "#stage-select"
    MODAL_ROOT_ID = "dialog"  # keep existing theme.tcss selectors

    class ConstitutionCreated(Message):
        """Emitted when the constitution is confirmed."""

        def __init__(self, constitution: str) -> None:
            super().__init__()
            self.constitution = constitution

    def compose_body(self) -> ComposeResult:
        yield ConstitutionWizardPanel(
            on_complete=self._finish,
            on_cancel=lambda: self._dismiss_and_restore_focus(None),
        )

    def _finish(self, text: str) -> None:
        self._dismiss_and_restore_focus(text)
