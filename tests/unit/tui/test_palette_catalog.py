"""Tests for the declarative built-in palette catalog."""

from unittest.mock import Mock

from aura_cli.tui.commands.palette_catalog import (
    default_palette_commands,
    register_default_palette_commands,
)


def test_default_palette_ids_are_unique() -> None:
    commands = default_palette_commands()
    assert len({command.id for command in commands}) == len(commands)
    assert sum(command.id == "list_sessions" for command in commands) == 1


def test_registers_each_default_once() -> None:
    registry = Mock()
    register_default_palette_commands(registry)
    assert registry.register.call_count == len(default_palette_commands())
