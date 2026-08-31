"""Canonical command catalog."""

from .catalog import (
    SLASH_COMMANDS,
    SlashCommand,
    command_dict_for_autocomplete,
    command_names,
    slash_command_pairs,
    tui_handled_commands,
)

__all__ = [
    "SLASH_COMMANDS",
    "SlashCommand",
    "command_dict_for_autocomplete",
    "command_names",
    "slash_command_pairs",
    "tui_handled_commands",
]
