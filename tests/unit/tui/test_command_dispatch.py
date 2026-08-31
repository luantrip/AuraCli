"""Tests for the TUI command dispatch adapter."""

from unittest.mock import Mock

from aura_cli.tui.commands.dispatch import command_ids, resolve_command_action


def test_resolves_aliases_to_bound_host_actions() -> None:
    host = Mock()

    assert resolve_command_action(host, "clear") is host.action_clear_chat
    assert resolve_command_action(host, "clear_chat") is host.action_clear_chat
    assert resolve_command_action(host, "unknown") is None


def test_catalog_exposes_session_and_navigation_commands() -> None:
    assert {"settings", "sessions", "paint", "token_usage"} <= command_ids()
