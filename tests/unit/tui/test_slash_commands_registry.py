"""Slash command registry consistency."""

from aura_cli.application.commands import (
    SLASH_COMMANDS,
    command_names,
    slash_command_pairs,
    tui_handled_commands,
)
from aura_cli.tui.widgets.input import SLASH_COMMANDS as INPUT_PAIRS


def test_input_pairs_match_slash_registry():
    registry_pairs = slash_command_pairs("pt")
    assert set(INPUT_PAIRS) == set(registry_pairs)


def test_tui_settings_and_sessions_in_registry():
    names = set(command_names(tui=True, cli=False))
    assert "/settings" in names
    assert "/sessions" in names or "/session-history" in names


def test_tui_handled_includes_settings():
    handled = set(tui_handled_commands())
    assert "/settings" in handled
    assert "/sessions" in handled


def test_every_primary_command_has_description():
    for cmd in SLASH_COMMANDS:
        assert cmd.description_pt
        assert cmd.name.startswith("/")
