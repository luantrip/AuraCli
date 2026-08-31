"""Dynamic theme system for Aura TUI — light/dark/auto variants.

ThemeManager detects terminal capabilities, supports runtime switching,
generates CSS variables and persists the selected theme. Access via
get_theme_manager(); set_theme("dark"/"light"/"auto") to switch.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import logging
from typing import TYPE_CHECKING, Callable, Dict, List, Optional

if TYPE_CHECKING:
    from textual.app import App

logger = logging.getLogger(__name__)


class ThemeMode(Enum):
    """Theme mode options."""

    LIGHT = "light"
    DARK = "dark"
    AUTO = "auto"


@dataclass
class ThemeColors:
    """Color definitions for a theme."""

    background: str = "#1a1a2e"
    background_secondary: str = "#16213e"
    background_tertiary: str = "#0f0f23"
    foreground: str = "#e4e4e7"
    foreground_muted: str = "#a1a1aa"

    primary: str = "#00d9ff"
    primary_muted: str = "#0099b3"
    secondary: str = "#7c3aed"
    secondary_muted: str = "#5b21b6"

    success: str = "#10b981"
    warning: str = "#f59e0b"
    error: str = "#ef4444"
    info: str = "#3b82f6"

    border: str = "#27272a"
    border_active: str = "#00d9ff"
    surface: str = "#27272a"
    surface_hover: str = "#3f3f46"

    code_background: str = "#0f0f23"
    code_keyword: str = "#c678dd"
    code_string: str = "#98c379"
    code_number: str = "#d19a66"
    code_comment: str = "#5c6370"
    code_function: str = "#61afef"

    chat_user: str = "#3b82f6"
    chat_assistant: str = "#10b981"
    chat_system: str = "#f59e0b"

    diff_add_bg: str = "#1e3a1e"
    diff_add_fg: str = "#51cf66"
    diff_remove_bg: str = "#3a1e1e"
    diff_remove_fg: str = "#ff6b6b"
    task_border: str = "#f59e0b"
    task_active: str = "#fbbf24"
    task_done: str = "#10b981"
    thought_fg: str = "#94a3b8"
    tree_line: str = "#475569"


@dataclass
class Theme:
    """Complete theme definition."""

    name: str
    mode: ThemeMode
    colors: ThemeColors = field(default_factory=ThemeColors)
    description: str = ""

    def to_css_variables(self) -> str:
        """Generate CSS variables from theme colors."""
        lines = [":root {"]

        for field_name in self.colors.__dataclass_fields__:
            value = getattr(self.colors, field_name)
            css_var = f"--theme-{field_name.replace('_', '-')}"
            lines.append(f"    {css_var}: {value};")

        lines.append("}")
        return "\n".join(lines)


NEBULA_DARK = Theme(
    name="Nebula Dark",
    mode=ThemeMode.DARK,
    colors=ThemeColors(
        background="#1a1a2e",
        background_secondary="#16213e",
        background_tertiary="#0f0f23",
        foreground="#e4e4e7",
        foreground_muted="#a1a1aa",
        primary="#00d9ff",
        primary_muted="#0099b3",
        secondary="#9a67f1",
        secondary_muted="#5b21b6",
        success="#10b981",
        warning="#f59e0b",
        error="#ef4444",
        info="#3b82f6",
        border="#27272a",
        border_active="#00d9ff",
        surface="#27272a",
        surface_hover="#3f3f46",
        code_background="#0f0f23",
        code_keyword="#c678dd",
        code_string="#98c379",
        code_number="#d19a66",
        code_comment="#787e88",
        code_function="#61afef",
        chat_user="#3b82f6",
        chat_assistant="#10b981",
        chat_system="#f59e0b",
        diff_add_bg="#1e3a1e",
        diff_add_fg="#51cf66",
        diff_remove_bg="#3a1e1e",
        diff_remove_fg="#ff6b6b",
        task_border="#f59e0b",
        task_active="#fbbf24",
        task_done="#10b981",
        thought_fg="#94a3b8",
        tree_line="#475569",
    ),
    description="Default dark theme with cosmic nebula aesthetics",
)

NEBULA_LIGHT = Theme(
    name="Nebula Light",
    mode=ThemeMode.LIGHT,
    colors=ThemeColors(
        background="#fafafa",
        background_secondary="#f4f4f5",
        background_tertiary="#e4e4e7",
        foreground="#18181b",
        foreground_muted="#6f6f78",
        primary="#0279b7",
        primary_muted="#0369a1",
        secondary="#7c3aed",
        secondary_muted="#6d28d9",
        success="#04845c",
        warning="#ae5f05",
        error="#dc2626",
        info="#2563eb",
        border="#d4d4d8",
        border_active="#0284c7",
        surface="#ffffff",
        surface_hover="#f4f4f5",
        code_background="#f4f4f5",
        code_keyword="#924ad7",
        code_string="#11813a",
        code_number="#ea580c",
        code_comment="#6f6f75",
        code_function="#2563eb",
        chat_user="#2563eb",
        chat_assistant="#04845c",
        chat_system="#ae5f05",
    ),
    description="Light theme for bright environments",
)

MIDNIGHT = Theme(
    name="Midnight",
    mode=ThemeMode.DARK,
    colors=ThemeColors(
        background="#0d1117",
        background_secondary="#161b22",
        background_tertiary="#010409",
        foreground="#c9d1d9",
        foreground_muted="#8b949e",
        primary="#58a6ff",
        primary_muted="#388bfd",
        secondary="#bc8cff",
        secondary_muted="#a371f7",
        success="#3fb950",
        warning="#d29922",
        error="#f85149",
        info="#58a6ff",
        border="#30363d",
        border_active="#58a6ff",
        surface="#21262d",
        surface_hover="#30363d",
        code_background="#0d1117",
        code_keyword="#ff7b72",
        code_string="#a5d6ff",
        code_number="#79c0ff",
        code_comment="#8b949e",
        code_function="#d2a8ff",
        chat_user="#58a6ff",
        chat_assistant="#3fb950",
        chat_system="#d29922",
    ),
    description="GitHub-inspired dark theme",
)

SOLAR_LIGHT = Theme(
    name="Solar Light",
    mode=ThemeMode.LIGHT,
    colors=ThemeColors(
        background="#fdf6e3",
        background_secondary="#eee8d5",
        background_tertiary="#fdf6e3",
        foreground="#5f747b",
        foreground_muted="#616a6a",
        primary="#2076b2",
        primary_muted="#2176b5",
        secondary="#666ab8",
        secondary_muted="#5a5fa3",
        success="#687700",
        warning="#8f6c00",
        error="#d5302e",
        info="#2076b2",
        border="#93a1a1",
        border_active="#268bd2",
        surface="#fdf6e3",
        surface_hover="#eee8d5",
        code_background="#eee8d5",
        code_keyword="#606e00",
        code_string="#1e746d",
        code_number="#d33682",
        code_comment="#616a6a",
        code_function="#268bd2",
        chat_user="#2076b2",
        chat_assistant="#687700",
        chat_system="#8f6c00",
    ),
    description="Solarized-inspired light theme",
)

DRACULA = Theme(
    name="Dracula",
    mode=ThemeMode.DARK,
    colors=ThemeColors(
        background="#282a36",
        background_secondary="#44475a",
        background_tertiary="#21222c",
        foreground="#f8f8f2",
        foreground_muted="#adb6d0",
        primary="#bd93f9",
        primary_muted="#9d79d9",
        secondary="#ff79c6",
        secondary_muted="#ff55a6",
        success="#50fa7b",
        warning="#ffb86c",
        error="#ff5555",
        info="#8be9fd",
        border="#44475a",
        border_active="#bd93f9",
        surface="#44475a",
        surface_hover="#6272a4",
        code_background="#21222c",
        code_keyword="#ff79c6",
        code_string="#f1fa8c",
        code_number="#bd93f9",
        code_comment="#7b89b3",
        code_function="#50fa7b",
        chat_user="#8be9fd",
        chat_assistant="#50fa7b",
        chat_system="#ffb86c",
    ),
    description="Dracula color scheme",
)

MACOS_LIGHT = Theme(
    name="macOS Light",
    mode=ThemeMode.LIGHT,
    colors=ThemeColors(
        background="#FFFFFF",
        background_secondary="#F5F5F7",
        background_tertiary="#E8E8ED",
        foreground="#1D1D1F",
        foreground_muted="#6f6f73",
        primary="#0071ed",
        primary_muted="#409CFF",
        secondary="#a64ed3",
        secondary_muted="#DA8FFF",
        success="#23873d",
        warning="#ad6500",
        error="#de332a",
        info="#5856D6",
        border="#D2D2D7",
        border_active="#007AFF",
        surface="#FFFFFF",
        surface_hover="#F0F0F5",
        code_background="#F5F5F7",
        code_keyword="#9e4ac8",
        code_string="#22813a",
        code_number="#FF9500",
        code_comment="#6f6f73",
        code_function="#007AFF",
        chat_user="#0071ed",
        chat_assistant="#23873d",
        chat_system="#ad6500",
    ),
    description="Clean, elegant light theme inspired by Apple's macOS design",
)

THEMES: Dict[str, Theme] = {
    "nebula-dark": NEBULA_DARK,
    "nebula-light": NEBULA_LIGHT,
    "midnight": MIDNIGHT,
    "solar-light": SOLAR_LIGHT,
    "dracula": DRACULA,
    "macos-light": MACOS_LIGHT,
}


class ThemeManager:
    """
    Manages themes and provides runtime theme switching.

    Example:
        ```python
        manager = ThemeManager(app)
        manager.set_theme("dracula")

        # Or use auto-detection
        manager.set_theme("auto")

        # Get current theme
        theme = manager.current_theme
        ```
    """

    def __init__(self, app: Optional[App] = None):
        """Initialize the instance."""
        self.app = app
        self._current_theme: Theme = NEBULA_DARK
        self._mode: ThemeMode = ThemeMode.AUTO
        self._subscribers: List[Callable[[Theme], None]] = []
        self._custom_themes: Dict[str, Theme] = {}

    @property
    def current_theme(self) -> Theme:
        """Get the current theme."""
        return self._current_theme

    @property
    def mode(self) -> ThemeMode:
        """Get the current theme mode."""
        return self._mode

    @property
    def available_themes(self) -> List[str]:
        """Get list of available theme names."""
        return list(THEMES.keys()) + list(self._custom_themes.keys())

    def set_theme(self, theme_name: str) -> bool:
        """
        Set the current theme by name.

        Args:
            theme_name: Theme name or "auto" for automatic detection

        Returns:
            True if theme was changed successfully
        """
        if theme_name == "auto":
            self._mode = ThemeMode.AUTO
            theme = self._detect_optimal_theme()
        elif theme_name in THEMES:
            self._mode = (
                ThemeMode.DARK
                if THEMES[theme_name].mode == ThemeMode.DARK
                else ThemeMode.LIGHT
            )
            theme = THEMES[theme_name]
        elif theme_name in self._custom_themes:
            theme = self._custom_themes[theme_name]
            self._mode = theme.mode
        else:
            logger.warning(f"Unknown theme: {theme_name}")
            return False

        old_theme = self._current_theme
        self._current_theme = theme

        self._notify_subscribers(theme)

        if self.app:
            self._apply_theme_to_app(theme)

        logger.info(f"Theme changed from {old_theme.name} to {theme.name}")
        return True

    def _detect_optimal_theme(self) -> Theme:
        """Detect optimal theme based on terminal background."""
        try:
            from aura_cli.tui.utils.terminal_detector import TerminalDetector

            detector = TerminalDetector()
            info = detector.detect()

            if info.background == "light":
                return MACOS_LIGHT
            else:
                return NEBULA_DARK
        except Exception as e:
            logger.debug(f"Failed to detect terminal theme: {e}")
            return NEBULA_DARK

    def _apply_theme_to_app(self, theme: Theme):
        """Apply theme to Textual app."""
        if not self.app:
            return

        try:
            self.app.dark = theme.mode == ThemeMode.DARK  # type: ignore[attr-defined]
            # Re-evaluate CSS so the injected $theme-* variables (see
            # AuraTUI.get_css_variables) pick up the new theme colors live.
            try:
                self.app.refresh_css()
            except Exception as css_error:
                logger.debug("refresh_css failed: %s", css_error)
            self.app.refresh()

            try:
                from aura_cli.tui.core.event_bus import TUIEvents

                TUIEvents.bus.publish(
                    "tui.theme.change",
                    {
                        "theme_name": theme.name,
                        "auto_detected": False,
                    },
                )
            except Exception as error:
                logger.debug("Theme change event publication failed: %s", error)
        except Exception as e:
            logger.error(f"Failed to apply theme to app: {e}")

    def subscribe(self, callback: Callable[[Theme], None]) -> Callable[[], None]:
        """
        Subscribe to theme changes.

        Args:
            callback: Function called when theme changes

        Returns:
            Unsubscribe function
        """
        self._subscribers.append(callback)

        def unsubscribe():
            """Remove a subscriber from the event bus."""
            if callback in self._subscribers:
                self._subscribers.remove(callback)

        return unsubscribe

    def _notify_subscribers(self, theme: Theme):
        """Notify all subscribers of theme change."""
        for callback in self._subscribers:
            try:
                callback(theme)
            except Exception as e:
                logger.error(f"Error in theme subscriber: {e}")

    def register_theme(self, theme: Theme) -> None:
        """
        Register a custom theme.

        Args:
            theme: Theme to register
        """
        key = theme.name.lower().replace(" ", "-")
        self._custom_themes[key] = theme
        logger.info(f"Registered custom theme: {theme.name}")

    def get_theme_css(self, theme_name: Optional[str] = None) -> str:
        """
        Get CSS variables for a theme.

        Args:
            theme_name: Theme name (uses current if not provided)

        Returns:
            CSS string with theme variables in a :root block
        """
        if theme_name:
            theme = THEMES.get(theme_name) or self._custom_themes.get(theme_name)
            if not theme:
                theme = self._current_theme
        else:
            theme = self._current_theme

        return theme.to_css_variables()

    def toggle_mode(self) -> Theme:
        """
        Toggle between light and dark mode.

        Returns:
            The new current theme
        """
        if self._current_theme.mode == ThemeMode.DARK:
            self.set_theme("macos-light")
        else:
            self.set_theme("nebula-dark")

        return self._current_theme


_theme_manager: Optional[ThemeManager] = None


def get_theme_manager(app: Optional[App] = None) -> ThemeManager:
    """Get or create the global theme manager."""
    global _theme_manager

    if _theme_manager is None:
        _theme_manager = ThemeManager(app)
    elif app and _theme_manager.app is None:
        _theme_manager.app = app

    return _theme_manager


def set_theme(theme_name: str) -> bool:
    """Convenience function to set theme."""
    return get_theme_manager().set_theme(theme_name)


def toggle_theme() -> Theme:
    """Convenience function to toggle theme mode."""
    return get_theme_manager().toggle_mode()


def get_current_theme() -> Theme:
    """Convenience function to get current theme."""
    return get_theme_manager().current_theme
