"""Actionable empty states for the history domain screen."""

from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import pytest
from textual.app import App, ComposeResult

from aura_cli.application.sessions.history import SessionEntry
from aura_cli.tui.widgets.history.browser_panel import HistoryBrowserPanel


class HistoryHarness(App[None]):
    """Minimal host for mounting the reusable history panel."""

    def __init__(self, sessions_dir: Path) -> None:
        super().__init__()
        self.sessions_dir = sessions_dir

    def compose(self) -> ComposeResult:
        yield HistoryBrowserPanel(sessions_dir=self.sessions_dir)


@pytest.mark.asyncio
async def test_empty_history_explains_next_actions(tmp_path: Path) -> None:
    app = HistoryHarness(tmp_path)

    async with app.run_test() as pilot:
        panel = app.query_one(HistoryBrowserPanel)
        empty = panel.query_one("#empty-history-state")
        table = panel.query_one("#session-table")

        assert empty.display is True
        assert table.display is False
        assert app.focused is panel.query_one("#history-start")
        assert str(panel.query_one("#empty-history-title").render()) == (
            "Nenhuma sessão neste workspace."
        )
        assert panel.query_one("#history-start")
        assert panel.query_one("#history-workspace")
        assert panel.query_one("#history-refresh")

        entry = SessionEntry(
            session_id="session-1",
            path=Path("session-1.jsonl"),
            timestamp=datetime.now(timezone.utc),
            cwd="/workspace",
            first_message="Olá",
            last_message="Olá",
            message_count=1,
            search_blob="olá /workspace",
        )
        panel.sessions = [entry]
        panel.query_text = "não-existe"
        panel._refresh_table()
        assert panel.query_one("#empty-history-state").display is True
        assert panel.query_one("#session-table").display is False
        assert str(panel.query_one("#empty-history-title").render()) == (
            "Nenhuma sessão corresponde ao filtro."
        )
        await pilot.pause()

        with patch(
            "aura_cli.tui.widgets.history.browser_panel.restore_composer_focus"
        ) as restore_focus:
            panel._return_to_conversation()
        restore_focus.assert_called_once_with(app)
