"""Navigation contracts for the history auxiliary screen."""

from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from textual.app import App, ComposeResult
from textual.widgets import Static

from aura_cli.application.sessions.history import SessionEntry
from aura_cli.tui.screens import history_screen


class HistoryScreenHarness(App[None]):
    def compose(self) -> ComposeResult:
        yield Static("")


@pytest.mark.asyncio
async def test_open_session_pops_restores_focus_and_notifies(tmp_path: Path) -> None:
    app = HistoryScreenHarness()
    entry = SessionEntry(
        session_id="session-1",
        path=tmp_path / "session-1.jsonl",
        timestamp=datetime.now(),
        cwd=str(tmp_path),
        first_message="Olá",
        last_message="Até logo",
        message_count=2,
        search_blob="session-1 olá até logo",
    )
    session = object()

    async with app.run_test() as pilot:
        screen = history_screen.HistoryScreen(sessions_dir=tmp_path)
        app.push_screen(screen)
        await pilot.pause()
        screen._panel = MagicMock(
            return_value=MagicMock(open_selected_session=lambda: entry)
        )

        with (
            patch(
                "aura_cli.tui.services.tui_session_service.load_session_from_path",
                return_value=session,
            ),
            patch(
                "aura_cli.tui.services.tui_session_service.restore_session_to_chat"
            ) as restore,
            patch.object(
                history_screen, "pop_screen_and_restore_focus"
            ) as pop_and_restore,
            patch.object(app, "notify") as notify,
        ):
            screen.action_open_session()

        restore.assert_called_once_with(app, session)
        pop_and_restore.assert_called_once_with(app)
        notify.assert_called_once_with("Sessão restaurada: session-1", title="◇ Sessão")
