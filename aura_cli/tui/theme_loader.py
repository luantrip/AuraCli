"""Theme Loader for Aura TUI.

Integrates Aura CLI TOML-based theme system with Textual's CSS design system,
enabling seamless theme application across CLI and TUI interfaces.

Features:
- Dynamic theme loading from theme manager
- Color mapping to Textual design system
- CSS variable generation for TCSS
- Inline style application for compatibility
- Graceful fallback to defaults

Integration:
- Uses TUI theme manager (tui/styles/themes.py) as primary source
- Falls back to CLI theme manager for compatibility
- Maps to Textual design system colors
- Applies via CSS variables and inline styles
"""

import contextlib

from textual.app import App

from aura_cli.core.logger import get_logger

_logger = get_logger(__name__)

try:
    from aura_cli.tui.styles.themes import get_theme_manager as get_tui_theme_manager

    TUI_THEME_AVAILABLE = True
except ImportError:
    TUI_THEME_AVAILABLE = False


def _get_color_from_manager(color_name: str) -> str:
    """Get color from available theme manager.

    Tries TUI theme manager first, falls back to CLI theme manager.

    Args:
        color_name: Name of color to retrieve

    Returns:
        Color value as hex string or None
    """
    if TUI_THEME_AVAILABLE:
        try:
            tui_manager = get_tui_theme_manager()
            theme = tui_manager.current_theme
            colors = theme.colors

            color_map = {
                "primary": colors.primary,
                "secondary": colors.secondary,
                "accent": colors.primary,
                "background": colors.background,
                "surface": colors.surface,
                "warning": colors.warning,
                "error": colors.error,
                "success": colors.success,
                "muted": colors.foreground_muted,
                "highlight": colors.primary,
                "body": colors.foreground,
            }

            return color_map.get(color_name) or ""
        except Exception as error:
            _logger.debug("Theme color %s unavailable: %s", color_name, error)

    return ""


def apply_nebula_theme(app: App) -> None:
    """Apply current Aura CLI theme to Textual app.

    Maps Aura theme colors to Textual design system using the
    CLI theme TOML as the source of truth.
    """
    try:
        theme_colors = _load_theme_colors()

        if hasattr(app, "design"):
            for name, color in theme_colors.items():
                if color and name in (
                    "primary",
                    "secondary",
                    "accent",
                    "background",
                    "surface",
                    "warning",
                    "error",
                    "success",
                ):
                    with contextlib.suppress(Exception):
                        app.design[name] = color

        _apply_inline_styles(app)

    except Exception as e:
        _logger.debug(f"Aviso: não foi possível aplicar tema: {e}")


def _load_theme_colors() -> dict:
    """Load colors from the native TUI theme authority."""
    defaults = {
        "primary": "#7aa2f7",
        "secondary": "#bb9af7",
        "accent": "#7dcfff",
        "background": "#1a1b26",
        "surface": "#24283b",
        "muted": "#565f89",
        "warning": "#e0af68",
        "error": "#f7768e",
        "success": "#9ece6a",
    }
    return {
        name: _get_color_from_manager(name) or fallback
        for name, fallback in defaults.items()
    }


def _apply_inline_styles(app: App) -> None:
    """Apply inline styles for dynamic theming compatibility.

    Sets CSS properties directly on widgets for maximum compatibility
    across Textual versions.

    Args:
        app: Textual App instance
    """
    try:
        bg_color = _get_color_from_manager("background")

        if app.screen:
            app.screen.styles.background = bg_color if bg_color else "#0a0a12"

    except Exception as error:
        _logger.debug("Inline TUI theme styles unavailable: %s", error)


def get_textual_theme_dict() -> dict:
    """Get theme values as dictionary for Textual CSS variables."""
    colors = _load_theme_colors()
    return {f"${k}": v for k, v in colors.items() if v}
