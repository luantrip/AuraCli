"""Declarative built-in command palette catalog."""

from __future__ import annotations

from typing import Any

from aura_cli.tui.widgets.command_palette import Command

_SPECS = (
    ("quit", "Exit application", "Exit Aura CLI", "Ctrl+C", "⎋", "navigation"),
    ("clear", "Clear chat", "Clear chat history", "Ctrl+L", "⟳", "navigation"),
    ("help", "Show help", "Display help information", "", "ℹ", "general"),
    (
        "toggle_panel",
        "Toggle panel",
        "Toggle analysis/events panel",
        "Ctrl+E",
        "▣",
        "panels",
    ),
    (
        "code_analysis",
        "Show code analysis",
        "Display code analysis",
        "Ctrl+S",
        "▥",
        "panels",
    ),
    ("focus_mode", "Focus mode", "Focus on selected task", "F", "◎", "panels"),
    (
        "show_events",
        "Show events",
        "Open agent event stream",
        "<leader> e",
        "◉",
        "dialogs",
    ),
    (
        "show_memory",
        "Show memory",
        "Open memory browser and notebook",
        "<leader> b",
        "◉",
        "dialogs",
    ),
    (
        "save_session",
        "Save session",
        "Save current session",
        "Ctrl+Shift+S",
        "▾",
        "session",
    ),
    ("new_session", "New session", "Start new session", "<leader> n", "✦", "session"),
    (
        "list_sessions",
        "Session history",
        "Browse saved sessions",
        "<leader> l",
        "◇",
        "session",
    ),
    (
        "toggle_dark",
        "Dark mode",
        "Toggle dark/light mode",
        "<leader> d",
        "◐",
        "theme",
    ),
    ("cycle_theme", "Cycle theme", "Switch between themes", "<leader> c", "◐", "theme"),
    (
        "copy",
        "Copy selection",
        "Copy to clipboard",
        "Ctrl+Shift+C",
        "⊞",
        "clipboard",
    ),
    (
        "paste",
        "Smart paste",
        "Paste with detection",
        "Ctrl+Shift+V",
        "↓",
        "clipboard",
    ),
    (
        "constitution",
        "Create Constitution",
        "Project constitution guide",
        "",
        "◆",
        "general",
    ),
    ("settings", "Settings", "API keys and LLM parameters", "", "⚙", "general"),
    ("paint", "Paint (launcher)", "Open ANSI editor screen", "Ctrl+G", "◐", "tools"),
    (
        "monitor",
        "Monitor (browser)",
        "Open embedded browser in TUI",
        "Ctrl+M",
        "◎",
        "tools",
    ),
    (
        "launch_monitor",
        "External monitor (Chawan)",
        "Suspend TUI and run Chawan",
        "",
        "↗",
        "tools",
    ),
    (
        "token_usage",
        "Token usage",
        "View session consumption",
        "Ctrl+Shift+T",
        "▥",
        "session",
    ),
)


def default_palette_commands() -> tuple[Command, ...]:
    """Materialize the unique built-in palette commands."""
    commands = tuple(Command(*spec) for spec in _SPECS)
    ids = [command.id for command in commands]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate built-in palette command ID")
    return commands


def register_default_palette_commands(registry: Any) -> None:
    """Register the built-in catalog in a compatible command registry."""
    for command in default_palette_commands():
        registry.register(command)
