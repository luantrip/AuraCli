"""Session history browser panel (search, filter, preview)."""

from __future__ import annotations

import contextlib
from pathlib import Path
from typing import List, Optional

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, VerticalScroll
from textual.css.query import NoMatches
from textual.widgets import Button, DataTable, Input, Label, Static

from aura_cli.application.sessions.history import query_session_history
from aura_cli.core.logger import get_logger
from aura_cli.tui.shell.base_tool_screen import (
    pop_screen_and_restore_focus,
    restore_composer_focus,
)
from aura_cli.tui.widgets.history.session_store import SessionEntry, load_sessions

logger = get_logger(__name__)


class HistoryBrowserPanel(Container):
    """Reusable history UI; embedded in HistoryScreen or standalone HistoryApp."""

    def __init__(
        self,
        sessions_dir: Optional[Path] = None,
        *,
        include_external: bool = False,
        id: str = "history-browser-panel",
        **kwargs,
    ):
        super().__init__(id=id, **kwargs)
        from aura_cli.core.paths import aura_path

        self.sessions_dir = sessions_dir or aura_path("sessions")
        self.include_external = include_external
        self.sessions: List[SessionEntry] = []
        self.filtered: List[SessionEntry] = []
        self.cwd_filter: Optional[str] = str(Path.cwd())
        self.cwd_filter_active = False
        self.query_text = ""
        self.selected_session: Optional[SessionEntry] = None

    def compose(self) -> ComposeResult:
        with Container(id="search-container"):
            yield Input(placeholder="⚲ Buscar no histórico...", id="search-input")
        yield Static("", id="filter-status")
        with Container(id="content-container"):
            yield DataTable(id="session-table")
            yield VerticalScroll(id="detail-panel")
        with Container(id="empty-history-state", classes="empty-state"):
            yield Label("Nenhuma sessão neste workspace.", id="empty-history-title")
            yield Static(
                "Comece uma conversa ou ajuste o workspace para carregar sessões.",
                id="empty-history-message",
            )
            with Horizontal(classes="empty-state-actions"):
                yield Button("Iniciar conversa", id="history-start")
                yield Button("Escolher workspace", id="history-workspace")
                yield Button("Atualizar", id="history-refresh")

    def on_mount(self) -> None:
        self._load_sessions()
        self._setup_table()
        self._refresh_table()
        self._update_filter_status()
        self._focus_initial_control()

    def _focus_initial_control(self) -> None:
        """Focus the most useful control for the current history state."""
        if not self.sessions:
            self.query_one("#history-start", Button).focus()
        else:
            self.query_one("#search-input", Input).focus()

    def _load_sessions(self) -> None:
        self.sessions = load_sessions(
            self.sessions_dir, include_external=self.include_external
        )
        logger.info(f"Carregadas {len(self.sessions)} sessões")

    def _setup_table(self) -> None:
        table = self.query_one(DataTable)
        table.add_columns("Tempo", "Msgs", "CWD", "Última Mensagem")
        table.cursor_type = "row"

    def _refresh_table(self) -> None:
        table = self.query_one(DataTable)
        table.clear()

        self.filtered = query_session_history(
            self.sessions,
            query=self.query_text,
            cwd=self.cwd_filter if self.cwd_filter_active else None,
        )

        for entry in self.filtered:
            last_msg = (entry.last_message or "")[:50]
            if len(entry.last_message or "") > 50:
                last_msg += "..."

            table.add_row(
                entry.relative_time(),
                str(entry.message_count),
                entry.short_cwd,
                last_msg,
            )

        if self.selected_session not in self.filtered:
            self.selected_session = None
            with contextlib.suppress(NoMatches):
                self.query_one("#detail-panel", VerticalScroll).remove_children()
        self._update_empty_state()
        self._update_filter_status()

    def _update_empty_state(self) -> None:
        """Show an actionable message instead of an unexplained blank table."""
        empty = self.query_one("#empty-history-state", Container)
        content = self.query_one("#content-container", Container)
        table = self.query_one("#session-table", DataTable)
        detail = self.query_one("#detail-panel", VerticalScroll)
        has_sessions = bool(self.sessions)
        has_results = bool(self.filtered)
        empty.display = not has_results
        content.display = has_results
        table.display = has_results
        detail.display = has_results and self.selected_session is not None

        title = self.query_one("#empty-history-title", Label)
        message = self.query_one("#empty-history-message", Static)
        if has_sessions:
            title.update("Nenhuma sessão corresponde ao filtro.")
            message.update(
                "Limpe a busca ou desative o filtro CWD para ver o histórico."
            )
        else:
            title.update("Nenhuma sessão neste workspace.")
            message.update(
                "Comece uma conversa ou ajuste o workspace para carregar sessões."
            )

    def _update_filter_status(self) -> None:
        status = self.query_one("#filter-status", Static)
        parts = [f"▥ {len(self.filtered)}/{len(self.sessions)} sessões"]
        parts.append(
            "▷ Filtro CWD: ON" if self.cwd_filter_active else "▷ Filtro CWD: OFF"
        )
        if self.query_text:
            parts.append(f'⚲ "{self.query_text}"')
        status.update(" | ".join(parts))

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle empty-state actions without coupling to session storage."""
        if event.button.id == "history-refresh":
            self.refresh_sessions()
            return
        if event.button.id == "history-start":
            self._return_to_conversation()
            return
        if event.button.id == "history-workspace":
            self._return_to_conversation()
            toggle_workspace = getattr(self.app, "action_toggle_workspace_panel", None)
            if callable(toggle_workspace):
                toggle_workspace()

    def _return_to_conversation(self) -> None:
        """Return to the primary composer when hosted in a screen stack."""
        app = self.app
        if len(getattr(app, "screen_stack", [])) > 1:
            pop_screen_and_restore_focus(app)
        else:
            restore_composer_focus(app)

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == "search-input":
            self.query_text = event.value
            self._refresh_table()

    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        if event.row_key is None or not self.filtered:
            return

        try:
            table = self.query_one(DataTable)
            row_index = table.cursor_row
            if 0 <= row_index < len(self.filtered):
                entry = self.filtered[row_index]
                self.selected_session = entry
                self._show_details(entry)
        except Exception as e:
            logger.error(f"Error showing details: {e}")

    def _show_details(self, entry: SessionEntry) -> None:
        detail = self.query_one("#detail-panel", VerticalScroll)
        detail.display = True
        detail.remove_children()

        detail.mount(Label(f"▷ {entry.path}", classes="detail-path"))
        if entry.external:
            detail.mount(
                Label(
                    f"◇ Externa: {entry.source_format or 'desconhecida'} · somente leitura",
                    classes="detail-external",
                )
            )
        detail.mount(
            Label(
                f"◇ {entry.timestamp.strftime('%Y-%m-%d %H:%M:%S')}",
                classes="detail-timestamp",
            )
        )
        detail.mount(Label(f"▷ CWD: {entry.cwd or 'N/A'}", classes="detail-cwd"))
        detail.mount(
            Label(f"▣ Mensagens: {entry.message_count}", classes="detail-count")
        )
        detail.mount(Static("", classes="detail-separator"))
        detail.mount(Label("✎ Primeira mensagem:", classes="detail-label"))
        detail.mount(Static(entry.first_message or "N/A", classes="detail-content"))
        detail.mount(Static("", classes="detail-separator"))
        detail.mount(Label("✎ Última mensagem:", classes="detail-label"))
        detail.mount(Static(entry.last_message or "N/A", classes="detail-content"))

    def toggle_cwd_filter(self) -> None:
        self.cwd_filter_active = not self.cwd_filter_active
        self._refresh_table()

    def focus_search(self) -> None:
        self.query_one("#search-input", Input).focus()

    def clear_search(self) -> None:
        search = self.query_one("#search-input", Input)
        search.value = ""
        self.query_text = ""
        self._refresh_table()

    def refresh_sessions(self) -> None:
        self._load_sessions()
        self._refresh_table()

    def open_selected_session(self) -> Optional[SessionEntry]:
        return self.selected_session
