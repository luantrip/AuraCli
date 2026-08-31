"""
Icon Set System - Multi-mode icon support.

Provides icons with automatic fallback based on terminal capabilities:
- NERD: Full Nerd Font icons
- UTF8: Unicode symbols
- ASCII: Plain ASCII fallback
"""

from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional

from aura_cli.application.file_icons import FileIcon


class IconSetType(str, Enum):
    """Icon set types for different terminal capabilities."""

    NERD = "nerd"
    UTF8 = "utf8"
    ASCII = "ascii"


@dataclass
class IconDefinition:
    """Icon definition with fallbacks."""

    nerd: str
    utf8: str
    ascii: str

    def get(self, icon_type: IconSetType) -> str:
        """Get icon for specified type."""
        if icon_type == IconSetType.NERD:
            return self.nerd
        elif icon_type == IconSetType.UTF8:
            return self.utf8
        return self.ascii


class IconSet:
    """
    Icon set manager with automatic fallback and caching.

    Provides consistent icons across different terminal capabilities.
    """

    def __init__(self, icon_type: IconSetType = IconSetType.UTF8):
        """Initialize the icon set for the given terminal capability type."""
        self._type = icon_type
        self._icons: Dict[str, IconDefinition] = {}
        self._resolved_cache: Dict[str, str] = {}
        self._setup_icons()

    def _setup_icons(self) -> None:
        """Setup icon definitions."""
        self._icons = {
            "success": IconDefinition("", "✔", "[OK]"),
            "error": IconDefinition("", "✖", "[!!]"),
            "warning": IconDefinition("", "▲", "/!\\"),
            "info": IconDefinition("", "ℹ", "(i)"),
            "pending": IconDefinition("", "○", "[ ]"),
            "running": IconDefinition("", "◉", "[*]"),
            "complete": IconDefinition("", "●", "[x]"),
            "play": IconDefinition("", "▶", ">"),
            "pause": IconDefinition("", "⏸", "||"),
            "stop": IconDefinition("", "⏹", "[]"),
            "reload": IconDefinition("", "⟳", "(R)"),
            "save": IconDefinition("", "💾", "[S]"),
            "copy": IconDefinition("", "❐", "[C]"),
            "paste": IconDefinition("", "📋", "[P]"),
            "edit": IconDefinition("", "✎", "[E]"),
            "delete": IconDefinition("", "✖", "[D]"),
            "search": IconDefinition("", "🔍", "?"),
            "file": IconDefinition("", "📄", "[F]"),
            "folder": IconDefinition("", "📂", "[D]"),
            "folder_open": IconDefinition("", "📂", "[D]"),
            "folder_closed": IconDefinition("", "📁", "[d]"),
            "code": IconDefinition("", "⌨", "{/}"),
            "terminal": IconDefinition("", "💻", ">_"),
            "git": IconDefinition("", "ᛘ", "(G)"),
            "branch": IconDefinition("", "ᛦ", "-<"),
            "commit": IconDefinition("", "◎", "(o)"),
            "merge": IconDefinition("", "ᛨ", "><"),
            "tag": IconDefinition("", "🏷", "#"),
            "user": IconDefinition("", "👤", "[U]"),
            "bot": IconDefinition("󰚩", "🤖", "[B]"),
            "aura": IconDefinition("✦", "✦", "*"),
            "message": IconDefinition("", "💬", "[M]"),
            "thinking": IconDefinition("", "💭", "..."),
            "typing": IconDefinition("", "⌨", "..."),
            "settings": IconDefinition("", "⚙", "[S]"),
            "plugin": IconDefinition("", "🔌", "[+]"),
            "clock": IconDefinition("", "⏰", "[T]"),
            "bell": IconDefinition("", "🔔", "(!)"),
            "lock": IconDefinition("", "🔒", "[L]"),
            "unlock": IconDefinition("", "🔓", "[U]"),
            "arrow_right": IconDefinition("", "→", "->"),
            "arrow_left": IconDefinition("", "←", "<-"),
            "arrow_up": IconDefinition("", "↑", "^"),
            "arrow_down": IconDefinition("", "↓", "v"),
            "chevron_right": IconDefinition("", "›", ">"),
            "chevron_left": IconDefinition("", "‹", "<"),
            "chevron_down": IconDefinition("", "⌄", "v"),
            "chevron_up": IconDefinition("", "⌃", "^"),
            "bullet": IconDefinition("", "▪", "-"),
            "dash": IconDefinition("─", "─", "-"),
            "separator": IconDefinition("│", "│", "|"),
            "dot": IconDefinition("●", "●", "*"),
            "star": IconDefinition("", "★", "*"),
            "sparkle": IconDefinition("", "✨", "*"),
            "lightning": IconDefinition("", "⚡", "!"),
            "rocket": IconDefinition("", "🚀", "^"),
            # Spinners (single frame)
            "spinner_1": IconDefinition("", "⠋", "|"),
            "spinner_2": IconDefinition("", "⠙", "/"),
            "spinner_3": IconDefinition("", "⠹", "-"),
            "spinner_4": IconDefinition("", "⠸", "\\"),
        }

    @property
    def icon_type(self) -> IconSetType:
        """Current icon type."""
        return self._type

    @icon_type.setter
    def icon_type(self, value: IconSetType) -> None:
        """Set icon type."""
        self._type = value

    def get(self, name: str) -> str:
        """
        Get icon by name (cached).

        Args:
            name: Icon identifier

        Returns:
            Icon string for current type
        """
        cache_key = f"{name}_{self._type.value}"

        if cache_key in self._resolved_cache:
            return self._resolved_cache[cache_key]

        if name in self._icons:
            icon = self._icons[name].get(self._type)
            self._resolved_cache[cache_key] = icon
            return icon

        self._resolved_cache[cache_key] = name
        return name

    def clear_cache(self):
        """Clear the resolved icon cache."""
        self._resolved_cache.clear()

    def __getattr__(self, name: str) -> str:
        """Allow attribute-style access to icons."""
        if name.startswith("_"):
            raise AttributeError(name)
        return self.get(name)

    def get_file_icon(self, filename: str, is_directory: bool = False) -> str:
        """
        Get file-type specific icon.

        Uses FileIcon system for Nerd fonts, falls back to generic for others.
        """
        if self._type == IconSetType.NERD:
            return FileIcon.get_icon(filename, is_directory)

        if self._type == IconSetType.UTF8:
            return self.get("folder" if is_directory else "file")

        return "[D]" if is_directory else "[F]"

    def spinner_frames(self) -> List[str]:
        """Get spinner animation frames."""
        if self._type == IconSetType.NERD:
            return ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
        elif self._type == IconSetType.UTF8:
            return ["◐", "◓", "◑", "◒"]
        else:
            return ["|", "/", "-", "\\"]

    def progress_blocks(self) -> List[str]:
        """Get progress bar block characters."""
        if self._type == IconSetType.NERD or self._type == IconSetType.UTF8:
            return ["░", "▒", "▓", "█"]
        else:
            return [" ", ".", ":", "#"]

    def box_chars(self) -> Dict[str, str]:
        """Get box drawing characters."""
        if self._type in (IconSetType.NERD, IconSetType.UTF8):
            return {
                "tl": "╭",
                "tr": "╮",
                "bl": "╰",
                "br": "╯",
                "h": "─",
                "v": "│",
                "t": "┬",
                "b": "┴",
                "l": "├",
                "r": "┤",
                "cross": "┼",
            }
        else:
            return {
                "tl": "+",
                "tr": "+",
                "bl": "+",
                "br": "+",
                "h": "-",
                "v": "|",
                "t": "+",
                "b": "+",
                "l": "+",
                "r": "+",
                "cross": "+",
            }


_icon_set: Optional[IconSet] = None


def get_icon_set() -> IconSet:
    """Get global IconSet instance."""
    global _icon_set
    if _icon_set is None:
        _icon_set = IconSet()
    return _icon_set


def detect_icon_support() -> IconSetType:
    """Detect terminal icon support level."""
    import os

    term = os.environ.get("TERM", "")
    term_program = os.environ.get("TERM_PROGRAM", "")

    nerd_terms = ["iTerm", "kitty", "alacritty", "wezterm", "hyper"]
    if any(nt.lower() in term_program.lower() for nt in nerd_terms):
        return IconSetType.NERD

    if "256color" in term or "xterm" in term:
        return IconSetType.UTF8

    return IconSetType.ASCII
