"""Single declarative catalog for navigable TUI capabilities."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class NavigationSpec:
    command_id: str
    action: str
    route: str
    aliases: tuple[str, ...]
    title: str
    description: str
    shortcut: str = ""
    icon: str = "◇"
    category: str = "navigation"


NAVIGATION_SPECS = (
    NavigationSpec(
        "settings",
        "_open_settings_screen",
        "settings",
        (),
        "Settings",
        "API keys and LLM parameters",
        icon="⚙",
    ),
    NavigationSpec(
        "constitution",
        "_open_constitution_screen",
        "constitution",
        (),
        "Create Constitution",
        "Project constitution guide",
        icon="◆",
    ),
    NavigationSpec(
        "paint",
        "action_push_paint_screen",
        "paint",
        (),
        "Paint (launcher)",
        "Open ANSI editor screen",
        "Ctrl+G",
        "◐",
        "tools",
    ),
    NavigationSpec(
        "files",
        "action_push_file_manager_screen",
        "files",
        ("file_manager",),
        "Files",
        "Open browser or file manager",
        "Ctrl+F",
        "▤",
        "tools",
    ),
    NavigationSpec(
        "monitor",
        "action_push_monitor_screen",
        "monitor",
        (),
        "Monitor (browser)",
        "Open built-in TUI browser",
        "Ctrl+M",
        "◎",
        "tools",
    ),
    NavigationSpec(
        "tools_menu",
        "action_push_tools_menu_screen",
        "tools",
        ("tools_menu",),
        "Tools",
        "Open tool catalogue",
        icon="▦",
        category="tools",
    ),
    NavigationSpec(
        "token_usage",
        "action_show_token_usage",
        "tokens",
        ("token_usage",),
        "Uso de tokens",
        "View session usage",
        "Ctrl+Shift+T",
        "▥",
        "session",
    ),
    NavigationSpec(
        "list_sessions",
        "action_push_history_screen",
        "history",
        ("sessions",),
        "Session history",
        "Browse saved sessions",
        "<leader> l",
        "◇",
        "session",
    ),
)


def route_aliases() -> dict[str, str | None]:
    aliases: dict[str, str | None] = {"home": None}
    for spec in NAVIGATION_SPECS:
        for route in (spec.route, *spec.aliases):
            aliases[route] = spec.route
    return aliases


def navigation_actions() -> dict[str, str]:
    actions: dict[str, str] = {}
    for spec in NAVIGATION_SPECS:
        actions[spec.command_id] = spec.action
        for alias in spec.aliases:
            actions.setdefault(alias, spec.action)
    return actions


__all__ = [
    "NAVIGATION_SPECS",
    "NavigationSpec",
    "navigation_actions",
    "route_aliases",
]
