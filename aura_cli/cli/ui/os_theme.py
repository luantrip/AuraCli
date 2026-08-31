"""OS Theme Detection - Detect system dark/light mode.

Provides cross-platform detection of OS theme preference for automatic
theme selection in Aura CLI.

Supported Platforms:
    - macOS: Uses `defaults read` to check AppleInterfaceStyle
    - Linux: Checks GTK/GNOME settings via gsettings
    - Windows: Reads Registry for theme preference

Features:
    - Cross-platform detection
    - Fallback to 'dark' if detection fails
    - Cached result for performance
    - Logging for debugging

Usage:
    >>> from aura_cli.cli.ui.os_theme import detect_os_theme
    >>> theme = detect_os_theme()
    >>> print(theme)  # 'dark' or 'light'
"""

import logging
import platform
import subprocess
from typing import Literal, Optional

logger = logging.getLogger(__name__)

# Cache for theme detection (avoid repeated subprocess calls)
_cached_theme: Optional[Literal["dark", "light"]] = None


def detect_os_theme() -> Literal["dark", "light"]:
    """Detect OS theme preference (dark/light mode).

    Checks system settings to determine if dark or light mode is active.
    Falls back to 'dark' if detection fails or is unsupported.

    Returns:
        'dark' or 'light' based on OS settings

    Example:
        >>> theme = detect_os_theme()
        >>> if theme == 'dark':
        ...     load_theme('default')
        ... else:
        ...     load_theme('light-minimal')
    """
    global _cached_theme

    # Return cached result if available
    if _cached_theme:
        return _cached_theme

    system = platform.system()

    try:
        if system == "Darwin":  # macOS
            _cached_theme = _detect_macos_theme()
        elif system == "Linux":
            _cached_theme = _detect_linux_theme()
        elif system == "Windows":
            _cached_theme = _detect_windows_theme()
        else:
            logger.warning(f"Unsupported platform for theme detection: {system}")
            _cached_theme = "dark"
    except Exception as e:
        logger.error(f"Error detecting OS theme: {e}")
        _cached_theme = "dark"

    logger.info(f"Detected OS theme: {_cached_theme}")
    return _cached_theme


def _detect_macos_theme() -> Literal["dark", "light"]:
    """Detect macOS theme via defaults command.

    Returns:
        'dark' if AppleInterfaceStyle is Dark, 'light' otherwise
    """
    try:
        # Check AppleInterfaceStyle (only exists if Dark Mode is enabled)
        subprocess.check_output(
            ["defaults", "read", "-g", "AppleInterfaceStyle"],
            stderr=subprocess.DEVNULL,
            text=True,
        ).strip()
        return "dark"
    except subprocess.CalledProcessError:
        # Key doesn't exist = Light Mode
        return "light"


def _detect_linux_theme() -> Literal["dark", "light"]:
    """Detect Linux theme via gsettings (GNOME/GTK).

    Returns:
        'dark' if GTK theme contains 'dark', 'light' otherwise
    """
    try:
        # Try GNOME/GTK settings
        result = (
            subprocess.check_output(
                ["gsettings", "get", "org.gnome.desktop.interface", "gtk-theme"],
                stderr=subprocess.DEVNULL,
                text=True,
            )
            .strip()
            .lower()
        )

        # Check if theme name contains 'dark'
        if "dark" in result:
            return "dark"
        return "light"
    except (subprocess.CalledProcessError, FileNotFoundError):
        # gsettings not available or failed
        logger.debug("gsettings not available, trying alternative methods")

        # Try checking color-scheme (newer GNOME)
        try:
            result = (
                subprocess.check_output(
                    ["gsettings", "get", "org.gnome.desktop.interface", "color-scheme"],
                    stderr=subprocess.DEVNULL,
                    text=True,
                )
                .strip()
                .lower()
            )

            if "dark" in result:
                return "dark"
            return "light"
        except (subprocess.CalledProcessError, FileNotFoundError):
            pass

    # Fallback to dark
    return "dark"


def _detect_windows_theme() -> Literal["dark", "light"]:
    """Detect Windows theme via Registry.

    Returns:
        'dark' if AppsUseLightTheme is 0, 'light' otherwise
    """
    try:
        import winreg

        # Open Registry key
        key = winreg.OpenKey(  # type: ignore[attr-defined]
            winreg.HKEY_CURRENT_USER,  # type: ignore[attr-defined]
            r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize",
        )

        # Read AppsUseLightTheme value (0 = dark, 1 = light)
        value, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")  # type: ignore[attr-defined]
        winreg.CloseKey(key)  # type: ignore[attr-defined]

        return "light" if value == 1 else "dark"
    except (ImportError, OSError, FileNotFoundError):
        # winreg not available or key doesn't exist
        return "dark"


def clear_theme_cache() -> None:
    """Clear cached theme detection result.

    Forces re-detection on next call to detect_os_theme().
    Useful if OS theme changes during runtime.
    """
    global _cached_theme
    _cached_theme = None
    logger.debug("Theme cache cleared")
