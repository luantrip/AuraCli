"""Session auto-save debouncing."""

from unittest.mock import MagicMock, patch

from aura_cli.tui.services.tui_session_service import maybe_autosave


def test_maybe_autosave_skips_when_unchanged():
    app = MagicMock()
    app.all_chat_messages = [{"sender": "User", "content": "hi"}]
    app._last_saved_message_count = 1
    manager = MagicMock()
    manager.auto_save = True
    with patch(
        "aura_cli.tui.services.tui_session_service.get_session_manager",
        return_value=manager,
    ):
        assert maybe_autosave(app) is False


def test_maybe_autosave_respects_interval_and_force(monkeypatch):
    app = MagicMock()
    app.all_chat_messages = [{"sender": "Aura", "content": "one"}]
    app._last_saved_message_count = 0
    manager = MagicMock()
    manager.auto_save = True
    manager.auto_save_interval = 60
    clock = iter((100.0, 101.0, 102.0))
    monkeypatch.setattr(
        "aura_cli.tui.services.tui_session_service.time.monotonic",
        lambda: next(clock),
    )
    with (
        patch(
            "aura_cli.tui.services.tui_session_service.get_session_manager",
            return_value=manager,
        ),
        patch(
            "aura_cli.tui.services.tui_session_service.save_tui_session",
            return_value=MagicMock(),
        ) as save,
    ):
        assert maybe_autosave(app) is True
        app.all_chat_messages.append({"sender": "Aura", "content": "two"})
        assert maybe_autosave(app) is False
        assert maybe_autosave(app, force=True) is True
        assert save.call_count == 2


def test_maybe_autosave_saves_when_count_changes():
    app = MagicMock()
    app.all_chat_messages = [{"sender": "User", "content": "hi"}]
    app._last_saved_message_count = 0
    manager = MagicMock()
    manager.auto_save = True
    with (
        patch(
            "aura_cli.tui.services.tui_session_service.get_session_manager",
            return_value=manager,
        ),
        patch(
            "aura_cli.tui.services.tui_session_service.save_tui_session",
            return_value=MagicMock(),
        ) as save,
    ):
        assert maybe_autosave(app) is True
        save.assert_called_once_with(app)
        assert app._last_saved_message_count == 1
