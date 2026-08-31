"""Command-to-action dispatch catalog for the Textual application adapter."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, Protocol

from aura_cli.tui.commands.navigation_catalog import navigation_actions


class TUICommandHost(Protocol):
    """Action surface required by the command dispatcher."""


_COMMAND_ACTIONS = {
    "quit": "action_quit",
    "clear": "action_clear_chat",
    "clear_chat": "action_clear_chat",
    "help": "_action_show_help",
    "show_help": "_action_show_help",
    "toggle_panel": "action_toggle_analysis_event_panel",
    "code_analysis": "action_show_code_analysis",
    "show_code_analysis": "action_show_code_analysis",
    "focus_mode": "action_toggle_focus_mode",
    "toggle_focus_mode": "action_toggle_focus_mode",
    "command_palette": "action_toggle_command_palette",
    "quick_command": "action_toggle_command_palette",
    "show_events": "action_show_events",
    "show_memory": "action_show_memory",
    "show_workflows": "action_show_workflows",
    "launch_paint": "action_launch_paint",
    "launch_monitor": "action_launch_monitor",
    "history_browser": "action_push_history_screen",
    "save_session": "action_save_session",
    "new_session": "action_new_session",
    "show_token_usage": "action_show_token_usage",
    "toggle_dark": "action_toggle_theme_mode",
    "toggle_dark_mode": "action_toggle_theme_mode",
    "cycle_theme": "action_cycle_theme",
    "copy": "_action_clipboard_stub",
    "copy_selection": "_action_clipboard_stub",
    "paste": "_action_clipboard_stub",
    "paste_smart": "_action_clipboard_stub",
    "cancel": "_action_cancel",
}
_COMMAND_ACTIONS.update(navigation_actions())


def command_ids() -> frozenset[str]:
    """Return every command handled by the Textual host."""
    return frozenset(_COMMAND_ACTIONS)


def resolve_command_action(
    host: TUICommandHost, command: str
) -> Callable[..., Any] | None:
    """Resolve one command to its bound host action."""
    action_name = _COMMAND_ACTIONS.get(command)
    return getattr(host, action_name) if action_name else None
