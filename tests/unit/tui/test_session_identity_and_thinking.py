from types import SimpleNamespace

import pytest
from textual.app import App, ComposeResult

from aura_cli.core.sessions.session_manager import Session
from aura_cli.tui.services import tui_session_service
from aura_cli.tui.widgets.chat import AuraChatLog
from aura_cli.tui.widgets.message_bubble import ThinkingBubble


class ChatApp(App[None]):
    def compose(self) -> ComposeResult:
        yield AuraChatLog(id="chat")


@pytest.mark.asyncio
async def test_thinking_indicator_is_singleton_and_hides_cleanly() -> None:
    app = ChatApp()
    async with app.run_test(size=(80, 24)) as pilot:
        await pilot.pause()
        chat = app.query_one("#chat", AuraChatLog)

        chat.show_thinking("Aura")
        await pilot.pause()
        assert len(chat.query(ThinkingBubble)) == 1

        chat.show_thinking("Aura")
        await pilot.pause()
        assert len(chat.query(ThinkingBubble)) == 1

        chat.hide_thinking()
        await pilot.pause()
        assert len(chat.query(ThinkingBubble)) == 0


def test_new_tui_session_uses_canonical_session_id(monkeypatch) -> None:
    session = Session(
        id="session-real-1",
        name="TUI",
        created_at="2026-01-01T00:00:00",
        updated_at="2026-01-01T00:00:00",
    )

    class Store:
        def __init__(self) -> None:
            self.values: dict[str, object] = {}

        def set(self, key: str, value: object) -> None:
            self.values[key] = value

    class Manager:
        current_session = None

        def create_session(self, name: str, tags: list[str]) -> Session:
            return session

    app = SimpleNamespace(
        all_chat_messages=[],
        store=Store(),
        post_message=lambda message: None,
    )
    monkeypatch.setattr(tui_session_service, "get_session_manager", lambda: Manager())

    created = tui_session_service.start_new_tui_session(app, save_current=False)

    assert created.id == "session-real-1"
    assert app.store.values["session.id"] == created.id
    assert app.store.values["session.manager_id"] == created.id
