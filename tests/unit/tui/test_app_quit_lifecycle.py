"""Tests for TUI shutdown resource ownership."""

import asyncio
from unittest.mock import AsyncMock, Mock, patch

from aura_cli.tui.app import AuraTUI


def test_quit_stops_bridge_and_releases_app_resources() -> None:
    app = object.__new__(AuraTUI)
    app.app_loop = Mock()
    app.shutdown_event = Mock()
    app._teardown_event_subscriptions = Mock()
    autosave_timer = Mock()
    app._autosave_timer = autosave_timer

    with (
        patch("aura_cli.tui.services.tui_session_service.maybe_autosave") as autosave,
        patch("textual.app.App.action_quit", new=AsyncMock()) as parent_quit,
    ):
        asyncio.run(app.action_quit())

    autosave.assert_called_once_with(app, force=True)
    app.shutdown_event.set.assert_called_once_with()
    autosave_timer.stop.assert_called_once_with()
    assert app._autosave_timer is None
    app._teardown_event_subscriptions.assert_called_once_with()
    app.app_loop.ui.stop.assert_called_once_with()
    parent_quit.assert_awaited_once()
