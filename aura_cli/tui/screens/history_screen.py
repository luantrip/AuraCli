"""Session history screen embedded in the main Aura TUI."""

from __future__ import annotations

from pathlib import Path
from typing import Any, ClassVar, Optional, cast

from textual.app import ComposeResult
from textual.binding import Binding

from aura_cli.application.sessions.history import SessionEntry
from aura_cli.tui.shell.base_tool_screen import (
    BaseToolScreen,
    pop_screen_and_restore_focus,
)
from aura_cli.tui.widgets.history.browser_panel import HistoryBrowserPanel


class HistoryScreen(BaseToolScreen):
    """Browse past JSONL sessions under ~/.aura/sessions."""

    SCREEN_TITLE = "◇ Histórico de Sessões"
    SCREEN_SUBTITLE = "Buscar · filtrar por CWD · pré-visualizar"

    BINDINGS: ClassVar[list] = [
        *BaseToolScreen.BINDINGS,
        Binding("/", "focus_search", "Buscar", show=True),
        Binding("f", "toggle_cwd_filter", "Filtrar CWD"),
        Binding("enter", "open_session", "Abrir"),
        Binding("r", "refresh", "Atualizar"),
        Binding("c", "clear_search", "Limpar busca"),
    ]

    def __init__(self, sessions_dir: Optional[Path] = None, **kwargs):
        super().__init__(**kwargs)
        self._sessions_dir = sessions_dir

    def compose_tool_body(self) -> ComposeResult:
        yield HistoryBrowserPanel(
            sessions_dir=self._sessions_dir,
            include_external=True,
        )

    def _panel(self) -> HistoryBrowserPanel:
        return self.query_one(HistoryBrowserPanel)

    def action_toggle_cwd_filter(self) -> None:
        self._panel().toggle_cwd_filter()

    def action_focus_search(self) -> None:
        self._panel().focus_search()

    def action_clear_search(self) -> None:
        self._panel().clear_search()

    def action_refresh(self) -> None:
        self._panel().refresh_sessions()

    def action_open_session(self) -> None:
        entry = self._panel().open_selected_session()
        if not entry:
            return
        if entry.external:
            self._open_external_session(entry)
            return
        from aura_cli.tui.services.tui_session_service import (
            load_session_from_path,
            restore_session_to_chat,
        )

        session = load_session_from_path(entry.path)
        if session:
            restore_session_to_chat(cast(Any, self.app), session)
            pop_screen_and_restore_focus(self.app)
            self.app.notify(
                f"Sessão restaurada: {entry.session_id}",
                title="◇ Sessão",
            )
        else:
            self.notify(
                f"Não foi possível carregar: {entry.session_id}",
                severity="warning",
            )

    def _open_external_session(self, entry: SessionEntry) -> None:
        """Preview and confirm an external import before changing the chat."""
        from aura_cli.tui.services.tui_session_service import (
            import_external_tui_session,
            preview_external_tui_session,
        )

        try:
            preview = preview_external_tui_session(str(entry.path), self.app)
        except ValueError as exc:
            self.notify(str(exc), severity="error")
            return

        def restore(confirmed: bool | None = True) -> None:
            if not confirmed:
                return
            try:
                from aura_cli.tui.services.tui_session_service import (
                    restore_session_to_chat,
                )

                session = import_external_tui_session(str(entry.path), self.app)
                restore_session_to_chat(cast(Any, self.app), session)
                pop_screen_and_restore_focus(self.app)
                self.app.notify(
                    f"Sessão externa restaurada: {entry.session_id}",
                    title="◇ Sessão",
                )
            except ValueError as exc:
                self.notify(str(exc), severity="error")

        if preview.requires_confirmation:
            from aura_cli.tui.shell.prompts import push_confirm

            reasons = "; ".join(preview.divergence_reasons)
            push_confirm(
                self.app,
                title="Importar sessão externa",
                message=(
                    f"Esta sessão diverge ({reasons}) e será importada somente como "
                    "histórico. Nenhuma tool será executada. Continuar?"
                ),
                on_result=restore,
                confirm_label="Importar",
            )
            return
        restore()
