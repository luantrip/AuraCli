"""Tests for TUI shell (screen registry, modal base)."""

from aura_cli.tui.screens.settings_screen import SettingsScreen
from aura_cli.tui.shell.screen_registry import ScreenId, _build_screen


def test_screen_registry_builds_settings():
    screen = _build_screen(ScreenId.SETTINGS)
    assert isinstance(screen, SettingsScreen)


def test_screen_registry_builds_history():
    from aura_cli.tui.screens.history_screen import HistoryScreen

    screen = _build_screen(ScreenId.HISTORY)
    assert isinstance(screen, HistoryScreen)
    assert screen.SCREEN_TITLE == "◇ Histórico de Sessões"


def test_screen_registry_builds_diff_confirm():
    from aura_cli.tui.screens.diff_confirmation_screen import DiffConfirmationScreen

    screen = _build_screen(
        ScreenId.DIFF_CONFIRM,
        file_path="x.py",
        diff_lines=["+a"],
        new_content="a",
    )
    assert isinstance(screen, DiffConfirmationScreen)


def test_settings_screen_uses_modal_base_title():
    assert SettingsScreen.TITLE == "⚙ Configurações"
