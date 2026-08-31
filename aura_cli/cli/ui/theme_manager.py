"""Theme manager singleton for Aura CLI.

Loads and validates TOML theme files, resolves color references, and
provides centralized access to colors, icons, syntax highlights and
animation settings. Falls back to the aura_minimal built-in theme on load
failures. Access via get_theme_manager().
"""

from importlib import resources
import os
from typing import Any, ClassVar, Dict, List, Optional

import toml

from aura_cli.cli.utils.exceptions import ConfigurationError, UIError

_LAYOUT_DEFAULTS: Dict[str, Any] = {
    "panel_padding": [1, 3],
    "chat_padding": [1, 2],
    "chat_margin": [0, 0, 1, 0],
    "chat_width_ratio": 0.85,
    "dialog_padding": [1, 2],
    "compact_padding": [0, 1],
}
_LAYOUT_ARITIES = {
    "panel_padding": 2,
    "chat_padding": 2,
    "chat_margin": 4,
    "dialog_padding": 2,
    "compact_padding": 2,
}


class ThemeManager:
    """Manages loading and access to UI themes from TOML files.

    Implemented as singleton to ensure consistency across application.

    Attributes:
        themes_dir: Directory containing theme files
        colors: Dict of theme colors
        styles: Dict of theme styles
        layout: Dict of layout settings
        appearance: Dict of appearance settings
        syntax: Dict of syntax highlighting colors
        icons: Dict of icon definitions
        animations: Dict of animation settings
        metadata: Dict of theme metadata (name, version, etc.)
    """

    _instance: Optional["ThemeManager"] = None

    AVAILABLE_THEMES: ClassVar[list] = [
        "aura_minimal",
        "cyberpunk",
        "nebula",
        "holographic",
        "dark",
        "light",
        "mono",
    ]

    def __new__(cls, *args, **kwargs):
        """Enforce singleton pattern."""
        if not cls._instance:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, theme_name: Optional[str] = None):
        """Initialize the instance."""
        if not hasattr(self, "_initialized"):
            self._init_themes_dir()
            self.colors: Dict[str, str] = {}
            self.styles: Dict[str, str] = {}
            self.layout: Dict[str, Any] = {}
            self.appearance: Dict[str, Any] = {}
            self.syntax: Dict[str, str] = {}
            self.icons: Dict[str, Any] = {}
            self.animations: Dict[str, Any] = {}
            self.markdown: Dict[str, str] = {}
            self.metadata: Dict[str, str] = {}
            self._current_theme: str = "aura_minimal"

            if theme_name is None:
                try:
                    from aura_cli.core.config import config_manager

                    theme_name = config_manager.get("theme_name") or "aura_minimal"
                except (ImportError, AttributeError, ConfigurationError):
                    theme_name = "aura_minimal"
                except Exception:
                    import logging

                    logger = logging.getLogger(__name__)

            # Support 'auto' theme - detect from OS
            if theme_name == "auto":
                try:
                    from aura_cli.cli.ui.os_theme import detect_os_theme

                    os_theme = detect_os_theme()
                    theme_name = "aura_minimal" if os_theme == "dark" else "light"
                except Exception as e:
                    import logging

                    logger = logging.getLogger(__name__)
                    logger.warning(
                        f"Failed to detect OS theme: {e}, using 'aura_minimal'"
                    )
                    theme_name = "aura_minimal"

            self.load_theme(theme_name or "aura_minimal")
            self._initialized = True

    def _init_themes_dir(self) -> None:
        """Initialize themes directory path using importlib.resources."""
        try:
            package = resources.files("aura_cli.cli.ui.themes")
            if package.is_dir():
                self.themes_dir = str(package)
                return
        except (
            ModuleNotFoundError,
            FileNotFoundError,
            TypeError,
            AttributeError,
        ) as _e:
            pass  # silenced: {_e}

        fallback_path = os.path.join(os.path.dirname(__file__), "themes")
        self.themes_dir = fallback_path

    @property
    def current_theme(self) -> str:
        """Get the name of the currently loaded theme."""
        return self._current_theme

    @property
    def theme_name(self) -> str:
        """Get the display name from theme metadata."""
        return self.metadata.get("name", self._current_theme)

    @property
    def theme_description(self) -> str:
        """Get the theme description from metadata."""
        return self.metadata.get("description", "")

    def list_themes(self) -> List[str]:
        """List all available theme names."""
        return self.AVAILABLE_THEMES.copy()

    def load_theme(self, theme_name: str) -> bool:
        """Load a theme from its TOML file, falling back to aura_minimal.

        Parses colours, styles, layout, appearance, syntax, icons and
        animations. Pass "auto" to detect the OS light/dark preference.
        Can be called at runtime to switch themes without restart.

        Args:
            theme_name: Theme name without the .toml extension, or "auto".

        Returns:
            True if the theme loaded successfully, False otherwise.

        Raises:
            FileNotFoundError: If neither the requested theme nor aura_minimal exists.
        """
        # Handle 'auto' theme - detect from OS
        if theme_name == "auto":
            try:
                from aura_cli.cli.ui.os_theme import detect_os_theme

                os_theme = detect_os_theme()
                theme_name = "aura_minimal" if os_theme == "dark" else "light"
            except Exception as e:
                import logging

                logger = logging.getLogger(__name__)
                logger.warning(f"Failed to detect OS theme: {e}, using 'aura_minimal'")
                theme_name = "aura_minimal"

        # Resolve legacy / alias theme names
        _ALIASES = {"default": "aura_minimal", "macos": "aura_minimal"}
        theme_name = _ALIASES.get(theme_name, theme_name)

        theme_path = self._get_theme_path(theme_name)

        if theme_path is None:
            if theme_name != "aura_minimal":
                return self.load_theme("aura_minimal")
            else:
                raise FileNotFoundError(
                    f"Base theme 'aura_minimal.toml' not found. "
                    f"Diretório de temas: {self.themes_dir}"
                )

        try:
            with open(theme_path, encoding="utf-8") as f:
                theme_data = toml.load(f)

            self._parse_theme(theme_data)
            self._current_theme = theme_name
            self._validate_contrast()

            if hasattr(self, "_initialized"):
                try:
                    from aura_cli.cli.ui.constants import UIStyles, _clear_theme_cache

                    _clear_theme_cache()

                    UIStyles._reload_styles()
                except (ImportError, AttributeError) as _e:
                    pass  # silenced: {_e}
                except Exception as e:
                    import logging

                    logger = logging.getLogger(__name__)
                    logger.debug(f"Error reloading UIStyles: {e}")

            return True

        except (OSError, toml.TomlDecodeError, KeyError, ValueError) as e:
            if theme_name != "aura_minimal":
                return self.load_theme("aura_minimal")
            else:
                raise UIError(f"Failed to load theme '{theme_name}': {e}") from e
        except Exception as e:
            import logging

            logger = logging.getLogger(__name__)
            logger.error(f"Error loading theme '{theme_name}': {e}", exc_info=True)
            if theme_name != "aura_minimal":
                return self.load_theme("aura_minimal")
            else:
                raise UIError(f"Failed to load theme '{theme_name}': {e}") from e

    def _validate_contrast(self) -> None:
        """Log warning if theme colors do not meet WCAG AA contrast (optional)."""
        try:
            import logging

            from aura_cli.cli.ui.accessibility import ColorContrast

            log = logging.getLogger(__name__)
            bg = (
                self.colors.get("background") or self.colors.get("surface") or "#0d1117"
            )
            if not (isinstance(bg, str) and bg.startswith("#")):
                return
            for key in ("body", "primary", "error", "warning"):
                color = self.styles.get(key) or self.colors.get(key)
                if not isinstance(color, str):
                    continue
                if not ColorContrast.meets_wcag_aa(color, bg):
                    log.warning(
                        "Theme %s: contrast WCAG AA may fail for '%s' on background. "
                        "Consider adjusting colors for accessibility.",
                        self._current_theme,
                        key,
                    )
        except Exception as _e:
            pass  # silenced: {_e}

    def _get_theme_path(self, theme_name: str) -> Optional[str]:
        """Get theme file path using importlib.resources or filesystem."""
        filename = f"{theme_name}.toml"

        try:
            package = resources.files("aura_cli.cli.ui.themes")
            theme_file = package / filename
            if theme_file.is_file():
                return str(theme_file)
        except (
            ModuleNotFoundError,
            FileNotFoundError,
            TypeError,
            AttributeError,
        ) as _e:
            pass  # silenced: {_e}

        filesystem_path = os.path.join(self.themes_dir, filename)
        if os.path.exists(filesystem_path):
            return filesystem_path

        return None

    @classmethod
    def _normalize_layout_tokens(cls, raw_layout: Any) -> Dict[str, Any]:
        """Normalize TOML layout tokens without allowing malformed geometry."""
        source = raw_layout if isinstance(raw_layout, dict) else {}
        normalized: Dict[str, Any] = dict(_LAYOUT_DEFAULTS)

        for name, default in _LAYOUT_DEFAULTS.items():
            value = source.get(name, default)
            if name == "chat_width_ratio":
                try:
                    ratio = float(value)
                except (TypeError, ValueError):
                    ratio = float(default)
                normalized[name] = min(max(ratio, 0.45), 1.0)
                continue

            arity = _LAYOUT_ARITIES[name]
            if isinstance(value, (list, tuple)) and len(value) == arity:
                values = tuple(value)
                if all(
                    isinstance(item, int) and not isinstance(item, bool) and item >= 0
                    for item in values
                ):
                    normalized[name] = list(values)

        for name, value in source.items():
            if name not in normalized:
                normalized[name] = value
        return normalized

    def _parse_theme(self, theme_data: Dict) -> None:
        """Parse theme data and store all sections."""
        self.colors = theme_data.get("colors", {})
        self.layout = self._normalize_layout_tokens(theme_data.get("layout", {}))
        self.appearance = theme_data.get("appearance", {})
        self.metadata = theme_data.get("metadata", {})
        self.syntax = theme_data.get("syntax", {})
        self.icons = theme_data.get("icons", {})
        self.animations = theme_data.get("animations", {})
        self.markdown = theme_data.get("markdown", {})

        raw_styles = theme_data.get("styles", {})
        raw_borders = theme_data.get("borders", {})
        raw_styles.update(raw_borders)

        self.styles = {
            name: self._resolve_style(style_def)
            for name, style_def in raw_styles.items()
        }

    def _resolve_style(self, style_def: str) -> str:
        """Resolve style definition by substituting color references.

        Args:
            style_def: Style definition string with potential color references

        Returns:
            Resolved style string with color references replaced
        """
        parts = style_def.split()
        resolved_parts = [self.colors.get(part, part) for part in parts]
        return " ".join(resolved_parts)

    def get_style(self, name: str) -> str:
        """Get style by name with fallback to color or original name."""
        if name in self.styles:
            return self.styles[name]
        if name in self.colors:
            return self.colors[name]
        return name

    def get_color(self, name: str) -> str:
        """Get color by name with fallback to original name."""
        return self.colors.get(name, name)

    def get_layout_property(self, name: str, default: Any = None) -> Any:
        """Get layout property by name."""
        return self.layout.get(name, default)

    def get_appearance_property(self, name: str, default: Any = None) -> Any:
        """Get appearance property by name."""
        return self.appearance.get(name, default)

    def get_syntax_color(self, token_type: str) -> str:
        """
        Get syntax highlighting color for a token type.

        Args:
            token_type: Type of syntax token (keyword, string, number, etc.)

        Returns:
            Color value for the token type
        """
        return self.syntax.get(token_type, self.get_color("foreground"))

    def get_syntax_theme(self) -> str:
        """
        Get the syntax theme name for Pygments/Rich.

        Returns:
            Name of the syntax theme (e.g., 'monokai', 'github-light')
        """
        return self.appearance.get("syntax_theme", "monokai")

    def get_markdown_style(self, element: str, default: Optional[str] = None) -> str:
        """Get markdown style for a specific element.

        Args:
            element: Markdown element name (heading_1, code, link, etc.)
            default: Default style if not found

        Returns:
            Style string for the markdown element
        """
        style = self.markdown.get(element, default)
        if style:
            return self._resolve_style(style)
        return default or ""

    def get_icon(self, name: str, default: str = "•") -> str:
        """
        Get icon by name.

        Args:
            name: Icon name (e.g., 'status_success', 'file_folder')
            default: Default icon if not found

        Returns:
            Icon character or string
        """
        return self.icons.get(name, default)

    def get_spinner_frames(self) -> List[str]:
        """
        Get spinner animation frames.

        Returns:
            List of spinner frame characters
        """
        return self.icons.get(
            "spinner_frames", ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
        )

    def get_animation_property(self, name: str, default: Any = None) -> Any:
        """
        Get animation property by name.

        Args:
            name: Animation property name (e.g., 'scan_speed', 'pulse_speed')
            default: Default value if not found

        Returns:
            Animation property value
        """
        return self.animations.get(name, default)

    def is_animation_enabled(self, animation_type: str) -> bool:
        """
        Check if a specific animation type is enabled.

        Args:
            animation_type: Type of animation (e.g., 'glow', 'pulse', 'scanline')

        Returns:
            True if animation is enabled
        """
        key = f"{animation_type}_enabled"
        return self.appearance.get(key, False)

    def get_metadata(self, key: str, default: str = "") -> str:
        """
        Get theme metadata by key.

        Args:
            key: Metadata key (name, version, author, description)
            default: Default value if not found

        Returns:
            Metadata value
        """
        return self.metadata.get(key, default)

    def is_dark_theme(self) -> bool:
        """
        Check if current theme is a dark theme.

        Returns:
            True if background color is dark
        """
        bg = self.colors.get("background", "#000000")
        if bg.startswith("#"):
            try:
                r = int(bg[1:3], 16)
                g = int(bg[3:5], 16)
                b = int(bg[5:7], 16)
                luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255
                return luminance < 0.5
            except (ValueError, IndexError) as _e:
                pass  # silenced: {_e}
        dark_names = ["black", "grey", "gray"]
        return any(dark in bg.lower() for dark in dark_names)

    def get_border_style(self, variant: str = "primary") -> str:
        """
        Get border style for a variant.

        Args:
            variant: Border variant (primary, secondary, success, etc.)

        Returns:
            Border style string
        """
        return self.get_style(f"border_{variant}")

    def get_status_style(self, status: str) -> str:
        """
        Get style for a status indicator.

        Args:
            status: Status name (idle, thinking, working, success, error, etc.)

        Returns:
            Status style string
        """
        return self.get_style(f"status_{status}")


theme_manager = ThemeManager()


def get_theme_manager() -> ThemeManager:
    """Get global ThemeManager instance."""
    return theme_manager


def load_theme(theme_name: str) -> bool:
    """
    Convenience function to load a theme.

    Args:
        theme_name: Name of theme to load

    Returns:
        True if theme loaded successfully
    """
    return get_theme_manager().load_theme(theme_name)


def get_current_theme() -> str:
    """
    Get the name of the currently loaded theme.

    Returns:
        Current theme name
    """
    return get_theme_manager().current_theme


def list_available_themes() -> List[str]:
    """
    List all available theme names.

    Returns:
        List of theme names
    """
    return get_theme_manager().list_themes()
