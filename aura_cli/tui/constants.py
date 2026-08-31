"""Visual constants for Aura TUI.

Centralised geometric/unicode icons, aligned with aura_minimal (Apple HIG).
Sem emoji — only geometric unicode, symbols and typographic characters.

Categories:
    - Status indicators
    - Status
    - Actions and operations
    - Agents and system
    - stema
    - Messages and notifications
"""

import locale
import os
import sys

# ─────────────────────────────────────────────────────────────────────────────
# Arrows and Basic Symbols
# ─────────────────────────────────────────────────────────────────────────────
ARROW = "→"
ARROW_LEFT = "←"
ARROW_UP = "↑"
ARROW_DOWN = "↓"
BULLET = "▪"
DIAMOND = "◆"
SEPARATOR = "│"

# ─────────────────────────────────────────────────────────────────────────────
# Indicadores de Status
# ─────────────────────────────────────────────────────────────────────────────
SUCCESS = "✔"
ERROR = "✖"
WARNING = "▲"
INFO = "ℹ"
LOADING = "⟳"
IDLE = "⬡"

# ─────────────────────────────────────────────────────────────────────────────
# Marca
# ─────────────────────────────────────────────────────────────────────────────
AURA = "✦"
AURA_STAR = "✦"

# ─────────────────────────────────────────────────────────────────────────────
# File System (geometric)
# ─────────────────────────────────────────────────────────────────────────────
FILE = "◇"
FOLDER = "▷"
FOLDER_OPEN = "▽"
GIT = "ᛘ"

# ─────────────────────────────────────────────────────────────────────────────
# Actions
# ─────────────────────────────────────────────────────────────────────────────
TOOL = "⚒"
SEARCH = "⚲"
EDIT = "✎"
CREATE = "✚"
DELETE = "✖"
SAVE = "▾"
COPY = "⊞"
RUN = "▶"
STOP = "⏹"
PAUSE = "⏸"
REFRESH = "⟳"
EXPORT = "↑"
IMPORT = "↓"

# ─────────────────────────────────────────────────────────────────────────────
# Agents (geometric)
# ─────────────────────────────────────────────────────────────────────────────
AGENT = "◈"
AGI = "◉"
OPS = "▶"
USER = "▪"

# ─────────────────────────────────────────────────────────────────────────────
# Mensagens
# ─────────────────────────────────────────────────────────────────────────────
CHAT = "▣"
THINKING = "⬢"
CODE = "◇"
MEMORY = "◎"
STATS = "▥"
WEB = "◎"
PAINT = "◐"

# ─────────────────────────────────────────────────────────────────────────────
# Status Icons for Task Tree
# ─────────────────────────────────────────────────────────────────────────────
STATUS_ICONS = {
    "pending": "☐",
    "starting": "▶",
    "in-progress": "⟳",
    "running": "⟳",
    "completed": "✔",
    "success": "✔",
    "failed": "✖",
    "error": "✖",
    "cancelled": "⊘",
    "planning": "◆",
    "thinking": "⬢",
    "executing": "⚒",
    "waiting": "▱",
    "blocked": "☒",
}

# ─────────────────────────────────────────────────────────────────────────────
# Severity Icons
# ─────────────────────────────────────────────────────────────────────────────
SEVERITY_ICONS = {
    "error": "✖",
    "warning": "▲",
    "info": "ℹ",
    "hint": "◆",
    "critical": "✖",
}

# Severity icons for toast notifications (includes success + information alias)
TOAST_SEVERITY_ICONS = {
    "success": SUCCESS,
    "error": ERROR,
    "warning": WARNING,
    "info": INFO,
    "information": INFO,
}

# Default titles by severity for toast notifications
TOAST_SEVERITY_TITLES = {
    "success": "Sucesso",
    "error": "Erro",
    "warning": "Aviso",
    "info": "Info",
    "information": "Info",
    "loading": "Aguarde",
}

# ─────────────────────────────────────────────────────────────────────────────
# Indicadores de Modo
# ─────────────────────────────────────────────────────────────────────────────
MODE_ICONS = {
    "normal": "N",
    "insert": "I",
    "visual": "V",
    "command": ":",
    "agi": "◉",
    "ops": "▶",
}


_ASCII_GLYPHS = {
    "ARROW": "->",
    "ARROW_LEFT": "<-",
    "ARROW_UP": "^",
    "ARROW_DOWN": "v",
    "BULLET": "-",
    "DIAMOND": "*",
    "SEPARATOR": "-",
    "SUCCESS": "[ok]",
    "ERROR": "[x]",
    "WARNING": "[!]",
    "INFO": "[i]",
    "LOADING": "...",
    "IDLE": "[ ]",
    "AURA": "*",
    "AURA_STAR": "*",
    "FILE": "[F]",
    "FOLDER": "[D]",
    "FOLDER_OPEN": "[D]",
    "GIT": "(G)",
    "TOOL": "[T]",
    "SEARCH": "?",
    "EDIT": "[E]",
    "CREATE": "+",
    "DELETE": "[x]",
    "SAVE": "[S]",
    "COPY": "[C]",
    "RUN": ">",
    "STOP": "[ ]",
    "PAUSE": "||",
    "REFRESH": "R",
    "EXPORT": "^",
    "IMPORT": "v",
    "AGENT": "[@]",
    "AGI": "[A]",
    "OPS": "[O]",
    "USER": "[U]",
    "CHAT": "[M]",
    "THINKING": "...",
    "CODE": "{/}",
    "MEMORY": "[M]",
    "STATS": "[S]",
    "WEB": "[W]",
    "PAINT": "[P]",
}


def detect_glyph_mode() -> str:
    """Resolve the configured glyph mode without trusting TERM alone."""
    requested = os.environ.get("AURA_TUI_GLYPHS", "auto").strip().lower()
    if requested in {"ascii", "unicode"}:
        return requested

    term = os.environ.get("TERM", "").strip().lower()
    encoding = (
        getattr(sys.stdout, "encoding", None)
        or locale.getpreferredencoding(False)
        or ""
    ).lower()
    if term in {"dumb", "unknown"} or "utf" not in encoding:
        return "ascii"
    return "unicode"


def configure_glyphs(mode: str | None = None) -> str:
    """Apply explicit or automatic glyph selection and return the active mode."""
    active_mode = (mode or os.environ.get("AURA_TUI_GLYPHS", "auto")).lower()
    if active_mode not in {"auto", "ascii", "unicode"}:
        active_mode = "auto"
    if active_mode == "auto":
        active_mode = detect_glyph_mode()

    if active_mode == "ascii":
        for name, value in _ASCII_GLYPHS.items():
            globals()[name] = value
        STATUS_ICONS.update(
            {
                "pending": "[ ]",
                "starting": ">",
                "in-progress": "...",
                "running": "...",
                "completed": "[ok]",
                "success": "[ok]",
                "failed": "[x]",
                "error": "[x]",
                "cancelled": "[x]",
                "planning": "[*]",
                "thinking": "...",
                "executing": ">",
                "waiting": "...",
                "blocked": "[!]",
            }
        )
        SEVERITY_ICONS.update(
            {
                "error": "[x]",
                "warning": "[!]",
                "info": "[i]",
                "hint": "[*]",
                "critical": "[x]",
            }
        )
        MODE_ICONS.update({"agi": "[A]", "ops": "[O]"})
        KEY_ICONS.update(
            {
                "alt": "Alt",
                "shift": "Shift",
                "enter": "Enter",
                "escape": "Esc",
                "tab": "Tab",
            }
        )
    else:
        unicode_values = {
            "ARROW": "→",
            "ARROW_LEFT": "←",
            "ARROW_UP": "↑",
            "ARROW_DOWN": "↓",
            "BULLET": "▪",
            "DIAMOND": "◆",
            "SEPARATOR": "│",
            "SUCCESS": "✔",
            "ERROR": "✖",
            "WARNING": "▲",
            "INFO": "ℹ",
            "LOADING": "⟳",
            "IDLE": "⬡",
            "AURA": "✦",
            "AURA_STAR": "✦",
            "FILE": "◇",
            "FOLDER": "▷",
            "FOLDER_OPEN": "▽",
            "GIT": "ᛘ",
            "TOOL": "⚒",
            "SEARCH": "⚲",
            "EDIT": "✎",
            "CREATE": "✚",
            "DELETE": "✖",
            "SAVE": "▾",
            "COPY": "⊞",
            "RUN": "▶",
            "STOP": "⏹",
            "PAUSE": "⏸",
            "REFRESH": "⟳",
            "EXPORT": "↑",
            "IMPORT": "↓",
            "AGENT": "◈",
            "AGI": "◉",
            "OPS": "▶",
            "USER": "▪",
            "CHAT": "▣",
            "THINKING": "⬢",
            "CODE": "◇",
            "MEMORY": "◎",
            "STATS": "▥",
            "WEB": "◎",
            "PAINT": "◐",
        }
        for name, value in unicode_values.items():
            globals()[name] = value
        STATUS_ICONS.update(
            {
                "pending": "☐",
                "starting": "▶",
                "in-progress": "⟳",
                "running": "⟳",
                "completed": "✔",
                "success": "✔",
                "failed": "✖",
                "error": "✖",
                "cancelled": "⊘",
                "planning": "◆",
                "thinking": "⬢",
                "executing": "⚒",
                "waiting": "▱",
                "blocked": "☒",
            }
        )
        SEVERITY_ICONS.update(
            {"error": "✖", "warning": "▲", "info": "ℹ", "hint": "◆", "critical": "✖"}
        )
        MODE_ICONS.update({"agi": "◉", "ops": "▶"})
        KEY_ICONS.update(
            {"alt": "⌥", "shift": "⇧", "enter": "↵", "escape": "⎋", "tab": "⇥"}
        )
    if "ACTIVE_GLYPH_MODE" in globals():
        globals()["ACTIVE_GLYPH_MODE"] = active_mode
    return active_mode


def get_glyph(name: str, default: str = "") -> str:
    """Return the current semantic glyph value after runtime reconfiguration."""
    value = globals().get(name, default)
    return value if isinstance(value, str) else default


# ─────────────────────────────────────────────────────────────────────────────
# Shortcut Display
# ─────────────────────────────────────────────────────────────────────────────
KEY_ICONS = {
    "ctrl": "^",
    "alt": "⌥",
    "shift": "⇧",
    "enter": "↵",
    "escape": "⎋",
    "tab": "⇥",
}

ACTIVE_GLYPH_MODE = configure_glyphs()

# ─────────────────────────────────────────────────────────────────────────────
# Paleta de Cores (espelha cli/ui/constants.py UIStyles)
# Lidas do ThemeManager em runtime — fallback para valores CLI se ThemeManager
# not available. CSS overrides via theme.tcss take precedence in the TUI.
# ─────────────────────────────────────────────────────────────────────────────


def _get_color(key: str, fallback: str) -> str:
    """Read a color from the native TUI theme manager."""
    try:
        from aura_cli.tui.styles.themes import get_theme_manager

        colors = get_theme_manager().current_theme.colors
        aliases = {
            "muted": "foreground_muted",
            "title": "primary",
            "label": "foreground",
            "code": "code_function",
        }
        val = getattr(colors, aliases.get(key, key), None)
        return val if val else fallback
    except Exception:
        return fallback


COLOR_PRIMARY = _get_color("primary", "cyan")
COLOR_SECONDARY = _get_color("secondary", "blue")
COLOR_SUCCESS = _get_color("success", "green")
COLOR_WARNING = _get_color("warning", "yellow")
COLOR_ERROR = _get_color("error", "red")
COLOR_MUTED = _get_color("muted", "dim white")
COLOR_ACCENT = _get_color("accent", "magenta")
COLOR_TITLE = _get_color("title", "bold cyan")
COLOR_LABEL = _get_color("label", "bold")
COLOR_CODE = _get_color("code", "bright_white")
COLOR_INFO = _get_color("info", "bright_blue")
