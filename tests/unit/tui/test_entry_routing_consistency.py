"""Simulate TUI entry routing: registry, palette, and keybind action names."""

from __future__ import annotations

import pytest

from aura_cli.tui.commands.dispatch import command_ids
from aura_cli.tui.commands.navigation_catalog import NAVIGATION_SPECS
from aura_cli.tui.keybinds.keybind_config import DEFAULT_KEYBINDS
from aura_cli.tui.shell import screen_registry
from aura_cli.tui.shell.screen_registry import (
    ScreenId,
    _build_screen,
    navigate_route,
    resolve_route,
)

# Palette command IDs registered in AuraTUI._register_palette_commands
PALETTE_COMMAND_IDS = {
    "quit",
    "clear",
    "help",
    "toggle_panel",
    "code_analysis",
    "focus_mode",
    "show_events",
    "show_memory",
    "save_session",
    "new_session",
    "list_sessions",
    "toggle_dark",
    "cycle_theme",
    "copy",
    "paste",
    "constitution",
    "settings",
    "paint",
    "monitor",
    "launch_monitor",
    "token_usage",
}


def test_screen_registry_has_one_lazy_spec_per_screen_id():
    assert set(screen_registry._SCREEN_SPECS) == set(ScreenId)
    assert all(
        module_name.startswith("aura_cli.tui.screens.")
        and class_name.endswith("Screen")
        for module_name, class_name in screen_registry._SCREEN_SPECS.values()
    )


@pytest.mark.parametrize("screen_id", list(ScreenId))
def test_screen_registry_builds_all_screens(screen_id: ScreenId):
    screen = _build_screen(screen_id)
    assert screen is not None


def test_palette_and_keybind_actions_are_handled():
    """Every palette id and default keybind action must resolve in _execute_command."""
    handled = command_ids()
    missing_palette = sorted(PALETTE_COMMAND_IDS - handled)
    assert not missing_palette, (
        f"Palette commands missing from command_map: {missing_palette}"
    )

    keybind_actions = {kb["action"] for kb in DEFAULT_KEYBINDS}
    missing_keybinds = [action for action in keybind_actions if action not in handled]
    assert not missing_keybinds, (
        f"Keybind actions missing from command_map: {missing_keybinds}"
    )


def test_open_screen_uses_window_stack_when_present(monkeypatch):
    from aura_cli.tui.shell import screen_registry

    pushed = []

    class FakeStack:
        def push_screen(self, screen, callback=None):
            pushed.append((screen, callback))

    class FakeApp:
        windows = FakeStack()

        def push_screen(self, screen, callback=None):
            raise AssertionError("should use WindowStack")

    app = FakeApp()
    screen_registry.open_screen(app, ScreenId.SETTINGS)
    assert len(pushed) == 1


def test_navigation_routes_aliases_and_home_back_behavior():
    assert resolve_route("file-manager") is ScreenId.FILES
    assert resolve_route("tokens") is ScreenId.TOKEN_USAGE

    app = type("App", (), {"screen_stack": [object(), object()]})()
    app.pop_screen = lambda: app.screen_stack.pop()
    assert navigate_route(app, "home") is True
    assert len(app.screen_stack) == 1


def test_unknown_navigation_route_is_rejected():
    with pytest.raises(ValueError, match="Unknown TUI route"):
        resolve_route("nowhere")


def test_navigation_catalog_is_connected_to_dispatch_and_routes():
    handled = command_ids()
    for spec in NAVIGATION_SPECS:
        assert spec.command_id in handled
        assert resolve_route(spec.route) is not None
        for alias in spec.aliases:
            assert alias in handled
