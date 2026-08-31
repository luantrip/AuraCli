"""Settings routing when Textual UI is active."""

from unittest.mock import MagicMock

from aura_cli.application.presentation_routing import (
    is_textual_ui,
    open_settings_for_ui,
)
from aura_cli.tui.screens.settings_screen import SettingsScreen


def test_is_textual_ui_detects_bridge():
    ui = MagicMock()
    type(ui).__name__ = "TextualUIManager"
    assert is_textual_ui(ui) is True


def test_open_settings_for_ui_calls_app():
    ui = MagicMock()
    type(ui).__name__ = "TextualUIManager"
    app = MagicMock()
    app._open_settings_screen = MagicMock()
    ui.app = app

    def safe(fn):
        fn()
        return True

    ui._safe_call_from_thread = safe
    assert open_settings_for_ui(ui) is True
    app._open_settings_screen.assert_called_once()


def test_settings_saved_event_closes_modal() -> None:
    screen = SettingsScreen()
    screen.action_close_modal = MagicMock()

    screen._on_settings_saved(MagicMock())

    screen.action_close_modal.assert_called_once_with()


def test_settings_reset_event_closes_modal() -> None:
    screen = SettingsScreen()
    screen.action_close_modal = MagicMock()

    screen._on_settings_reset(MagicMock())

    screen.action_close_modal.assert_called_once_with()
