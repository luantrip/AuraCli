"""Central registry for opening TUI screens from the main app."""

from __future__ import annotations

from enum import Enum
import importlib
from typing import Any, Callable, Optional, Type, cast

from textual.screen import Screen

from aura_cli.tui.commands.navigation_catalog import route_aliases


class ScreenId(str, Enum):
    """Stable identifiers for screens reachable from TUI navigation."""

    SETTINGS = "settings"
    CONSTITUTION = "constitution"
    PAINT = "paint"
    FILES = "files"
    MONITOR = "monitor"
    TOOLS_MENU = "tools_menu"
    TOKEN_USAGE = "token_usage"
    HISTORY = "history"
    DIFF_CONFIRM = "diff_confirm"


# Keep screen imports lazy while making the complete registry inspectable.
_SCREEN_SPECS: dict[ScreenId, tuple[str, str]] = {
    ScreenId.SETTINGS: ("aura_cli.tui.screens.settings_screen", "SettingsScreen"),
    ScreenId.CONSTITUTION: (
        "aura_cli.tui.screens.constitution_screen",
        "ConstitutionScreen",
    ),
    ScreenId.PAINT: ("aura_cli.tui.screens.paint_screen", "PaintScreen"),
    ScreenId.FILES: ("aura_cli.tui.screens.files_screen", "FilesScreen"),
    ScreenId.MONITOR: ("aura_cli.tui.screens.monitor_screen", "MonitorScreen"),
    ScreenId.TOOLS_MENU: (
        "aura_cli.tui.screens.tools_menu_screen",
        "ToolsMenuScreen",
    ),
    ScreenId.TOKEN_USAGE: (
        "aura_cli.tui.screens.token_usage_screen",
        "TokenUsageScreen",
    ),
    ScreenId.HISTORY: ("aura_cli.tui.screens.history_screen", "HistoryScreen"),
    ScreenId.DIFF_CONFIRM: (
        "aura_cli.tui.screens.diff_confirmation_screen",
        "DiffConfirmationScreen",
    ),
}

_ROUTE_TO_SCREEN = {
    "settings": ScreenId.SETTINGS,
    "constitution": ScreenId.CONSTITUTION,
    "paint": ScreenId.PAINT,
    "files": ScreenId.FILES,
    "monitor": ScreenId.MONITOR,
    "tools": ScreenId.TOOLS_MENU,
    "tokens": ScreenId.TOKEN_USAGE,
    "history": ScreenId.HISTORY,
}
_ROUTE_ALIASES = {
    alias: None if route is None else _ROUTE_TO_SCREEN[route]
    for alias, route in route_aliases().items()
}


def resolve_route(route_type: str) -> ScreenId | None:
    """Resolve a public navigation route to its registered screen."""
    normalized = route_type.strip().casefold().replace("-", "_")
    if normalized not in _ROUTE_ALIASES:
        raise ValueError(f"Unknown TUI route: {route_type}")
    return _ROUTE_ALIASES[normalized]


def navigate_route(app: Any, route_type: str, **params: Any) -> bool:
    """Navigate to a registered route; home closes the current screen."""
    screen_id = resolve_route(route_type)
    if screen_id is None:
        if len(app.screen_stack) > 1:
            app.pop_screen()
        return True
    open_screen(app, screen_id, **params)
    return True


def _build_screen(screen_id: ScreenId, **kwargs: Any) -> Screen:
    """Build a registered screen while keeping optional dependencies lazy."""
    try:
        module_name, class_name = _SCREEN_SPECS[screen_id]
    except KeyError as error:
        raise ValueError(f"Unknown screen: {screen_id}") from error
    module = importlib.import_module(module_name)
    screen_type = cast(Type[Screen], getattr(module, class_name))
    return screen_type(**kwargs)


def open_screen(
    app,
    screen_id: ScreenId,
    callback: Optional[Callable[..., Any]] = None,
    **kwargs: Any,
) -> None:
    """Instantiate and push a registered screen."""
    screen = _build_screen(screen_id, **kwargs)
    stack = getattr(app, "windows", None)
    if stack is not None:
        stack.push_screen(screen, callback)
    elif callback is not None:
        app.push_screen(screen, callback)
    else:
        app.push_screen(screen)


async def open_screen_wait(app, screen_id: ScreenId, **kwargs: Any) -> Any:
    """Push a modal screen and await its dismiss result."""
    screen = _build_screen(screen_id, **kwargs)
    return await app.push_screen_wait(screen)


def screen_class(screen_id: ScreenId) -> Type[Screen]:
    """Return screen class without instantiating (tests / typing)."""
    return type(_build_screen(screen_id))


__all__ = [
    "ScreenId",
    "_build_screen",
    "navigate_route",
    "open_screen",
    "open_screen_wait",
    "resolve_route",
    "screen_class",
]
