"""Presentation-token port used by Core without importing a UI adapter."""

from __future__ import annotations


class _FallbackIcons:
    """Minimal icon set used when the CLI UI layer is unavailable."""

    SUCCESS = "[OK]"
    ERROR = "[ERR]"
    WARNING = "[!]"
    INFO = "[i]"
    CANCEL = "[x]"
    FILE = "[F]"
    DIR = "[D]"
    BULLET = "-"
    STATS = "[#]"
    SEARCH = "[?]"
    RUN = "[>]"
    OPS = "[O]"
    AGENT = "[A]"
    QUESTION = "[?]"
    ROCKET = "[>]"
    IDLE = "[ ]"
    THINKING = "[...]"
    WORKING = "[~]"


class _FallbackStyles:
    """Minimal style set used when the CLI UI layer is unavailable."""

    SUCCESS = "green"
    ERROR = "red"
    WARNING = "yellow"
    INFO = "cyan"
    PRIMARY = "cyan"
    SECONDARY = "blue"
    MUTED = "dim white"
    TITLE = "bold white"

    @staticmethod
    def safe_style(name: str, fallback: str = "") -> str:
        """Return a style string safely, never None."""
        return fallback


class _TokenProxyMeta(type):
    provider: type

    def __getattr__(cls, name: str):
        return getattr(cls.provider, name)


class UIIcons(metaclass=_TokenProxyMeta):
    """Late-bound icon tokens configured by the active presentation adapter."""

    provider = _FallbackIcons


class UIStyles(metaclass=_TokenProxyMeta):
    """Late-bound style tokens configured by the active presentation adapter."""

    provider = _FallbackStyles


def configure_ui_tokens(*, icons: type, styles: type) -> None:
    """Register presentation tokens without introducing a Core→adapter import."""
    UIIcons.provider = icons
    UIStyles.provider = styles


def reset_ui_tokens() -> None:
    """Restore standalone-safe tokens, primarily for isolated runtimes/tests."""
    UIIcons.provider = _FallbackIcons
    UIStyles.provider = _FallbackStyles


__all__ = ["UIIcons", "UIStyles", "configure_ui_tokens", "reset_ui_tokens"]
