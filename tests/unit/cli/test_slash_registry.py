"""CLI slash registry tests."""

from aura_cli.application.commands import slash_command_pairs
from aura_cli.cli.commands.slash_registry import get_cli_command_descriptions


def test_cli_registry_includes_tui_pairs():
    tui = dict(slash_command_pairs("pt"))
    cli = get_cli_command_descriptions()
    for name in tui:
        assert name in cli


def test_cli_registry_has_session_and_settings():
    cli = get_cli_command_descriptions()
    assert "/settings" in cli
    assert "/session" in cli or "/sessions" in cli


def test_cli_extra_commands():
    cli = get_cli_command_descriptions()
    assert "/cost" in cli
    assert "/dashboard" in cli
