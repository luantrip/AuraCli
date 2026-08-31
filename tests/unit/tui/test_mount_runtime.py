"""Tests for TUI mount-time composition."""

from unittest.mock import Mock, patch

from aura_cli.tui.mount_runtime import (
    connect_app_loop,
    initialize_tui_session,
    stop_autosave_timer,
)


def test_connect_app_loop_uses_only_public_bridge_lifecycle() -> None:
    app = Mock()
    app.app_loop.ui.ensure_initialized.return_value = True

    connect_app_loop(app)

    app.app_loop.set_shutdown_event.assert_called_once_with(app.shutdown_event)
    app.app_loop.ui.ensure_initialized.assert_called_once_with()
    assert not app.app_loop.ui._init_sync_manager.called


def test_session_metadata_and_autosave_interval_are_mounted() -> None:
    app = Mock()
    manager = Mock(auto_save_interval=12)
    with patch("aura_cli.core.sessions.get_session_manager", return_value=manager):
        initialize_tui_session(app)

    app.store.set.assert_any_call("session.id", app.store.set.call_args_list[0].args[1])
    app.store.set.assert_any_call(
        "session.started_at", app.store.set.call_args_list[1].args[1]
    )
    app.set_interval.assert_called_once_with(12.0, app._on_autosave_interval)
    assert app._autosave_timer is app.set_interval.return_value


def test_initialize_session_replaces_previous_autosave_timer() -> None:
    app = Mock()
    previous_timer = Mock()
    app._autosave_timer = previous_timer
    manager = Mock(auto_save_interval=12)
    with patch("aura_cli.core.sessions.get_session_manager", return_value=manager):
        initialize_tui_session(app)

    previous_timer.stop.assert_called_once_with()
    assert app._autosave_timer is app.set_interval.return_value


def test_initialize_session_stops_timer_when_config_load_fails() -> None:
    app = Mock()
    previous_timer = Mock()
    app._autosave_timer = previous_timer
    with patch(
        "aura_cli.core.sessions.get_session_manager",
        side_effect=RuntimeError("config unavailable"),
    ):
        initialize_tui_session(app)

    previous_timer.stop.assert_called_once_with()
    assert app._autosave_timer is None
    app.set_interval.assert_not_called()


def test_stop_autosave_timer_is_idempotent() -> None:
    app = Mock()
    timer = Mock()
    app._autosave_timer = timer

    stop_autosave_timer(app)
    stop_autosave_timer(app)

    timer.stop.assert_called_once_with()
    assert app._autosave_timer is None
