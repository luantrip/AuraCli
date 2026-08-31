"""UI constants for Aura CLI — unified design system.

Defines UIIcons, UIStyles, UIMessages, UILayout and Indent constants.
Style values are loaded from ThemeManager so themes can be switched at
runtime without code changes. The icon system integrates with
core/icon_set.py for Nerd Fonts / UTF-8 / ASCII rendering modes.
"""

from typing import ClassVar, Optional


def _get_theme():
    """Get current theme (function to allow reloading)."""
    from aura_cli.cli.ui.theme_manager import get_theme_manager

    return get_theme_manager()


_theme_cache = None


def _get_theme_cached():
    """Get theme with caching (lazy initialization)."""
    global _theme_cache
    if _theme_cache is None:
        _theme_cache = _get_theme()
    return _theme_cache


def _clear_theme_cache():
    """Clear theme cache (used when theme changes)."""
    global _theme_cache
    _theme_cache = None


try:
    from aura_cli.cli.ui.accessibility import AlternativeText

    ACCESSIBILITY_AVAILABLE = True
except ImportError:
    ACCESSIBILITY_AVAILABLE = False
    AlternativeText = None  # type: ignore[misc,assignment]


_icon_set = None


def _get_icon_set():
    """Get IconSet instance (lazy load)."""
    global _icon_set
    if _icon_set is None:
        try:
            from aura_cli.cli.ui.core.icon_set import get_icon_set

            _icon_set = get_icon_set()
        except ImportError:
            _icon_set = None
    return _icon_set


class UIIcons:
    """Professional visual icons using Unicode geometric/technical symbols.

    Style: "Assembly/Retro-Future"

    Categories:
        - Status: Geometric shapes for states
        - Actions: Technical glyphs for operations
        - Agents: System and agent indicators
    """

    IDLE = "○"  # Empty circle - waiting
    THINKING = "⬢"  # Filled hexagon - processing
    WORKING = "⟳"  # Technical circular arrow
    LOADING = "▱"  # Paralelogramo
    SUCCESS = "✔"  # Heavy checkmark
    ERROR = "✖"  # Heavy X
    WARNING = "▲"  # Solid triangle
    INFO = "ℹ"  # Serif Info
    CANCEL = "⊘"  # Circled division slash

    TOOL = "⚒"  # Hammer and Pick
    FILE = "◇"  # Diamond (hollow)
    DIR = "▣"  # White square with black square inside
    RUN = "▶"  # Play
    SEARCH = "⚲"  # Scepter/Loop
    STATS = "◆"  # Black diamond
    EDIT = "✎"  # Pencil lower right
    CREATE = "✚"  # Heavy Plus
    DELETE = "✖"  # Heavy Multiply (Cleaner than trash)
    SAVE = "⊡"  # Square with dot
    COPY = "❐"  # Two squares
    PASTE = "▥"  # Square with horizontal fill
    UNDO = "↶"  # Arrow curve left
    REDO = "↷"  # Arrow curve right

    AURA = "✦"  # Four pointed star (The Aura)
    AGENT = "◈"  # Diamond with dot
    OPS = "⚡"  # High voltage
    AGI = "⬡"  # Hexagon
    USER = "▹"  # Right-pointing triangle (small)
    SYSTEM = "⊞"  # Squared plus

    MESSAGE = "◬"  # Triangle with dot
    NOTIFICATION = "◉"  # Circle with dot
    CHAT = "▷"  # Right-pointing triangle

    GIT = "ᛘ"  # Runic letter (Looks like branch)
    COMMIT = "◎"  # Bullseye
    BRANCH = "ᛦ"  # Runic letter (Looks like branch split)
    MERGE = "ᛨ"  # Runic letter (Looks like merge)

    BULLET = "▪"  # Small black square
    ARROW = "➔"  # Heavy wide headed right arrow
    ARROW_UP = "⇧"  # Upwards white arrow
    ARROW_DOWN = "⇩"  # Downwards white arrow
    DASH = "━"  # Heavy horizontal
    SEPARATOR = "│"  # Light vertical
    CORNER = "┕"  # Box drawings light up and right
    TEE = "┝"  # Box drawings light vertical and right

    TODO = "☐"  # Ballot box
    DONE = "☑"  # Ballot box with check
    IN_PROGRESS = "◪"  # Circle with upper left quadrant black
    BLOCKED = "☒"  # Ballot box with X

    PRIORITY_HIGH = "▲"  # Black up pointing triangle
    PRIORITY_MEDIUM = "◆"  # Black diamond
    PRIORITY_LOW = "▼"  # Black down pointing triangle

    CLOCK = "◔"  # Circle with upper right quadrant
    TIMER = "◑"  # Circle with right half
    CALENDAR = "▦"  # Square with vertical fill

    ROCKET = "△"  # Triangle
    SPARKLES = "✧"  # Small four-pointed star (hollow)
    LIGHTNING = "⚡"  # Lightning bolt for speed

    ASCII_MODE = False

    @classmethod
    def set_ascii_mode(cls, enabled: bool = True):
        """Enable or disable ASCII-only icon mode."""
        cls.ASCII_MODE = enabled
        if enabled:
            cls._set_ascii_icons()
        else:
            cls._set_unicode_icons()

    @classmethod
    def _set_ascii_icons(cls):
        """Set ASCII icons as fallback."""
        cls.IDLE = "[ ]"
        cls.THINKING = "[*]"
        cls.WORKING = "(+)"
        cls.LOADING = "..."
        cls.SUCCESS = "OK"
        cls.ERROR = "!!"
        cls.WARNING = "/!\\"
        cls.INFO = "(i)"
        cls.CANCEL = "(X)"
        cls.TOOL = "[T]"
        cls.FILE = "[F]"
        cls.DIR = "[D]"
        cls.RUN = ">"
        cls.SEARCH = "?"
        cls.STATS = "[S]"
        cls.EDIT = "/"
        cls.CREATE = "+"
        cls.DELETE = "x"
        cls.AURA = "*"
        cls.AGENT = "@"
        cls.OPS = "$"
        cls.BULLET = "-"
        cls.ARROW = "->"
        cls.DASH = "-"
        cls.SEPARATOR = "|"

    @classmethod
    def _set_unicode_icons(cls):
        """Restore Unicode icons (Assembly Style)."""
        cls.IDLE = "○"
        cls.THINKING = "⬢"
        cls.WORKING = "⟳"
        cls.SUCCESS = "✔"
        cls.ERROR = "✖"
        cls.WARNING = "▲"
        cls.INFO = "ℹ"
        cls.CANCEL = "⊘"
        cls.TOOL = "⚒"
        cls.FILE = "◇"
        cls.DIR = "▣"
        cls.RUN = "▶"
        cls.SEARCH = "⚲"
        cls.BULLET = "▪"
        cls.ARROW = "➔"
        cls.DASH = "━"
        cls.SEPARATOR = "│"

    @staticmethod
    def with_alt(icon: str, include_alt: bool = False) -> str:
        """Return the icon with an alternative fallback."""
        if not include_alt or not ACCESSIBILITY_AVAILABLE:
            return icon

        return (
            AlternativeText.describe_icon(icon) if AlternativeText is not None else icon
        )

    @classmethod
    def get_status_icon(cls, status: str) -> str:
        """Return the status icon for a given state string."""
        status_map = {
            "idle": cls.IDLE,
            "thinking": cls.THINKING,
            "working": cls.WORKING,
            "loading": cls.LOADING,
            "success": cls.SUCCESS,
            "completed": cls.DONE,
            "done": cls.DONE,
            "error": cls.ERROR,
            "failed": cls.ERROR,
            "warning": cls.WARNING,
            "info": cls.INFO,
            "cancelled": cls.CANCEL,
            "pending": cls.TODO,
            "in_progress": cls.IN_PROGRESS,
            "blocked": cls.BLOCKED,
        }
        return status_map.get(status.lower(), cls.BULLET)

    @classmethod
    def get(cls, name: str) -> str:
        """
        Get icon by name (unified interface with IconSet).

        Args:
            name: Icon name (e.g., 'success', 'error', 'file')

        Returns:
            Icon string
        """
        icon_set = _get_icon_set()
        if icon_set:
            return icon_set.get(name)
        return getattr(cls, name.upper(), cls.BULLET)

    @classmethod
    def get_file_icon(cls, filename: str, is_directory: bool = False) -> str:
        """
        Get file-type specific icon (integrates with IconSet).

        Args:
            filename: File name
            is_directory: Whether it's a directory

        Returns:
            Appropriate icon
        """
        icon_set = _get_icon_set()
        if icon_set:
            return icon_set.get_file_icon(filename, is_directory)
        return cls.DIR if is_directory else cls.FILE


class UIStyles:
    """
    Standardized Rich styles, loaded dynamically from ThemeManager.
    """

    _DEFAULTS: ClassVar[dict] = {
        "primary": "cyan",
        "secondary": "blue",
        "success": "green",
        "warning": "yellow",
        "error": "red",
        "info": "blue",
        "muted": "dim white",
        "accent": "magenta",
        "title": "bold white",
        "subtitle": "white",
        "label": "white",
        "code": "white",
        "highlight": "yellow",
        "body": "white",
        "caption": "dim white",
        "status_idle": "dim white",
        "status_thinking": "yellow",
        "status_working": "cyan",
        "status_success": "green",
        "status_error": "red",
        "status_warning": "yellow",
        "agent_agi": "magenta",
        "agent_ops": "blue",
        "agent_chat": "cyan",
        "loading": "cyan",
        "spinner": "cyan",
        "progress": "cyan",
        "border_primary": "cyan",
        "border_secondary": "blue",
        "border_success": "green",
        "border_warning": "yellow",
        "border_error": "red",
        "border_muted": "dim white",
        "border_accent": "magenta",
    }

    @classmethod
    def _reload_styles(cls):
        """Reload styles for the current theme at runtime."""
        try:
            _clear_theme_cache()
            theme = _get_theme()

            for key in cls._DEFAULTS:
                attr_name = key.upper()
                new_style = theme.get_style(key)
                if new_style:
                    setattr(cls, attr_name, new_style)
        except Exception as e:
            import logging

            logger = logging.getLogger(__name__)
            logger.debug(f"Error reloading styles: {e}")

    @classmethod
    def _ensure_initialized(cls):
        """Ensure styles are initialized (alias for _init_styles/reload)."""
        cls._reload_styles()

    @classmethod
    def _init_styles(cls):
        """Initialize styles from theme (called on first access)."""
        cls._reload_styles()

    PRIMARY = "cyan"
    SECONDARY = "blue"
    SUCCESS = "green"
    WARNING = "yellow"
    ERROR = "red"
    INFO = "blue"
    MUTED = "dim white"
    ACCENT = "magenta"

    TITLE = "bold white"
    SUBTITLE = "white"
    LABEL = "white"
    CODE = "white"
    HIGHLIGHT = "yellow"
    BODY = "white"
    CAPTION = "dim white"

    STATUS_IDLE = "dim white"
    STATUS_THINKING = "yellow"
    STATUS_WORKING = "cyan"
    STATUS_SUCCESS = "green"
    STATUS_ERROR = "red"
    STATUS_WARNING = "yellow"

    AGENT_AGI = "magenta"
    AGENT_OPS = "blue"
    AGENT_CHAT = "cyan"

    LOADING = "cyan"
    SPINNER = "cyan"
    PROGRESS = "cyan"

    BORDER_PRIMARY = "cyan"
    BORDER_SECONDARY = "blue"
    BORDER_SUCCESS = "green"
    BORDER_WARNING = "yellow"
    BORDER_ERROR = "red"
    BORDER_MUTED = "dim white"
    BORDER_ACCENT = "magenta"

    USER_CHAT_BORDER = "none"
    AGENT_CHAT_BORDER = "none"
    SYSTEM_CHAT_BORDER = "dim white"
    CHAT_SENDER_STYLE = "bold"
    CHAT_TIMESTAMP_STYLE = "dim italic"
    CHAT_TIMESTAMP_FORMAT = "%H:%M"

    @classmethod
    def get_style(cls, name: str, fallback: str = "white") -> str:
        """Get style value safely."""
        try:
            return getattr(cls, name.upper(), fallback)
        except AttributeError:
            return fallback

    @classmethod
    def __getattr__(cls, name: str) -> str:
        """Allow case-insensitive attribute access.

        Args:
            name: Attribute name (case-insensitive)

        Returns:
            Attribute value from uppercase version of name
        """
        return getattr(cls, name.upper())

    @classmethod
    def safe_style(cls, style_name: str, fallback: str = "white") -> str:
        """Get style value safely, never returning None.

        Args:
            style_name: Name of style attribute
            fallback: Fallback value if style is None

        Returns:
            Style value (never None)
        """
        try:
            value = getattr(cls, style_name)
            return value if value is not None else fallback
        except AttributeError:
            return fallback


class UIMessages:
    """UI message templates for tool execution."""

    @staticmethod
    def tool_executing(tool_name: str) -> str:
        """Format tool executing message."""
        return f"{UIIcons.TOOL} Executing {tool_name}..."

    @staticmethod
    def tool_success(tool_name: str, execution_time: Optional[float] = None) -> str:
        """Format tool success message."""
        time_str = f" ({execution_time:.2f}s)" if execution_time else ""
        return f"{UIIcons.SUCCESS} {tool_name} finished{time_str}"

    @staticmethod
    def tool_error(tool_name: str, error: str) -> str:
        """Format tool error message."""
        return f"{UIIcons.ERROR} {tool_name} failed: {error}"


class UILayout:
    """UI layout constants for borders and spacing."""

    HORIZONTAL = "─"
    VERTICAL = "│"
    METADATA_SEPARATOR = "·"


class Indent:
    """Standard indentation constants for consistent spacing."""

    CORE = "  "  # 2 spaces - standard indentation
    NESTED = "    "  # 4 spaces - nested content
    LABEL = "  "  # 2 spaces - label offset
    CONTENT = "    "  # 4 spaces - content offset


# Apply theme styles at import time so hex colors from themes like
# aura_minimal (#007AFF) are reflected in UIStyles class attributes,
# not just the hardcoded fallback values defined above.
# Wrapped in try/except so circular-import safety is preserved during
# early bootstrap before ThemeManager is fully initialized.
with __import__("contextlib").suppress(Exception):
    UIStyles._reload_styles()

# Register this adapter's dynamic tokens through the Core presentation port.
from aura_cli.core.ui_bridge import configure_ui_tokens as _configure_ui_tokens

_configure_ui_tokens(icons=UIIcons, styles=UIStyles)
