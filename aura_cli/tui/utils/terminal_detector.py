"""Terminal Detector for Aura TUI.

Detects terminal characteristics for optimal theme and feature selection.

Features:
- Background color detection (light/dark)
- Terminal emulator identification
- Color capability detection (none/basic/256/truecolor)
- True color support verification
- Unicode support detection
- Terminal dimensions

Components:
- TerminalInfo: Terminal characteristics dataclass
- Background detection algorithms
- Color capability probing
- Terminal program identification
"""

from __future__ import annotations

from dataclasses import dataclass
import logging
import os
import sys
from typing import ClassVar, Literal, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class TerminalInfo:
    """Information about the terminal environment."""

    background: Literal["light", "dark", "unknown"]
    terminal_program: str
    term_type: str
    color_support: Literal["none", "basic", "256", "truecolor"]
    supports_unicode: bool
    width: int
    height: int

    @property
    def is_dark(self) -> bool:
        """Check if terminal has dark background."""
        return self.background == "dark"

    @property
    def is_light(self) -> bool:
        """Check if terminal has light background."""
        return self.background == "light"

    @property
    def supports_truecolor(self) -> bool:
        """Check if terminal supports 24-bit color."""
        return self.color_support == "truecolor"


class TerminalDetector:
    """Detects terminal characteristics for optimal theme and colour configuration.

    Probes background colour (light vs dark), terminal emulator identity,
    colour depth (true-colour / 256 / 8) and Unicode support. Results are
    available via detect() → TerminalInfo.
    """

    DARK_DEFAULT_TERMINALS: ClassVar[set] = {
        "iterm.app",
        "hyper",
        "alacritty",
        "kitty",
        "wezterm",
        "windows terminal",
        "gnome-terminal",
        "konsole",
        "tilix",
    }

    LIGHT_DEFAULT_TERMINALS: ClassVar[set] = {
        "apple_terminal",
    }

    def __init__(self):
        """Initialize the detector."""
        self._cached_info: Optional[TerminalInfo] = None

    def detect(self, force_refresh: bool = False) -> TerminalInfo:
        """
        Detect terminal information.

        Args:
            force_refresh: Force re-detection even if cached

        Returns:
            TerminalInfo with detected characteristics
        """
        if self._cached_info and not force_refresh:
            return self._cached_info

        background = self._detect_background_color()
        terminal_program = os.environ.get("TERM_PROGRAM", "").lower()
        term_type = os.environ.get("TERM", "").lower()
        color_support = self._detect_color_support()
        supports_unicode = self._detect_unicode_support()
        width, height = self._get_terminal_size()

        self._cached_info = TerminalInfo(
            background=background,
            terminal_program=terminal_program,
            term_type=term_type,
            color_support=color_support,
            supports_unicode=supports_unicode,
            width=width,
            height=height,
        )

        logger.debug(f"Terminal detected: {self._cached_info}")
        return self._cached_info

    def _detect_background_color(self) -> Literal["light", "dark", "unknown"]:
        """
        Detect if terminal has light or dark background.

        Uses multiple methods in order of reliability:
        1. COLORFGBG environment variable
        2. OSC 11 query (xterm-compatible)
        3. Terminal program defaults
        4. Default to dark
        """
        # Method 1: COLORFGBG (set by many terminals)
        colorfgbg = os.environ.get("COLORFGBG", "")
        if colorfgbg:
            result = self._parse_colorfgbg(colorfgbg)
            if result:
                return result

        # Method 2: macOS/iTerm specific
        iterm_profile = os.environ.get("ITERM_PROFILE", "")
        if "light" in iterm_profile.lower():
            return "light"
        if "dark" in iterm_profile.lower():
            return "dark"

        # Method 3: Check terminal-specific environment
        term_bg = os.environ.get("TERMINAL_BACKGROUND", "").lower()
        if term_bg in ("light", "dark"):
            return term_bg  # type: ignore[return-value]

        # Method 4: OSC 11 query (can hang, use carefully)
        if (
            sys.stdout.isatty()
            and os.environ.get("AURA_DETECT_TERMINAL_BG", "0") == "1"
        ):
            osc_result = self._query_osc11()
            if osc_result:
                return osc_result

        # Method 5: Terminal program defaults
        terminal_program = os.environ.get("TERM_PROGRAM", "").lower()
        if terminal_program in self.LIGHT_DEFAULT_TERMINALS:
            return "light"
        if terminal_program in self.DARK_DEFAULT_TERMINALS:
            return "dark"

        # Default assumption: dark
        return "dark"

    def _parse_colorfgbg(self, value: str) -> Optional[Literal["light", "dark"]]:
        """Parse COLORFGBG environment variable."""
        try:
            parts = value.split(";")
            if len(parts) >= 2:
                bg_val = int(parts[-1])
                if bg_val == 0:
                    return "dark"
                elif bg_val == 7 or bg_val == 15:
                    return "light"
                elif bg_val < 8:
                    return "dark"
                else:
                    return "light"
        except (ValueError, IndexError):
            return None
        return None

    def _query_osc11(self) -> Optional[Literal["light", "dark"]]:
        """
        Query terminal background via OSC 11.

        Note: This can hang on some terminals, use with caution.
        """
        try:
            import select
            import termios
            import tty

            if not sys.stdin.isatty() or not sys.stdout.isatty():
                return None

            fd = sys.stdin.fileno()
            old_settings = termios.tcgetattr(fd)

            try:
                tty.setraw(fd)

                sys.stdout.write("\033]11;?\033\\")
                sys.stdout.flush()

                if select.select([sys.stdin], [], [], 0.1)[0]:
                    response = ""
                    while len(response) < 50:
                        if select.select([sys.stdin], [], [], 0.05)[0]:
                            char = sys.stdin.read(1)
                            response += char
                            if char in ("\\", "\007"):
                                break
                        else:
                            break

                    if "rgb:" in response:
                        return self._parse_osc11_response(response)
            finally:
                termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        except Exception as e:
            logger.debug(f"OSC 11 query failed: {e}")

        return None

    def _parse_osc11_response(
        self, response: str
    ) -> Optional[Literal["light", "dark"]]:
        """Parse OSC 11 response to determine background brightness."""
        try:
            rgb_part = response.split("rgb:")[1].split("\\")[0].split("\007")[0]
            r_hex, g_hex, b_hex = rgb_part.split("/")

            r = int(r_hex[:2], 16)
            g = int(g_hex[:2], 16)
            b = int(b_hex[:2], 16)

            luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255

            return "light" if luminance > 0.5 else "dark"
        except Exception as e:
            logger.debug(f"Failed to parse OSC 11 response: {e}")
            return None

    def _detect_color_support(self) -> Literal["none", "basic", "256", "truecolor"]:
        """Detect terminal color capabilities."""
        colorterm = os.environ.get("COLORTERM", "").lower()
        if colorterm in ("truecolor", "24bit"):
            return "truecolor"

        term = os.environ.get("TERM", "").lower()

        if "truecolor" in term or "24bit" in term or "-direct" in term:
            return "truecolor"

        term_program = os.environ.get("TERM_PROGRAM", "").lower()
        if term_program in {"iterm.app", "hyper", "alacritty", "kitty", "wezterm"}:
            return "truecolor"

        if "256color" in term:
            return "256"

        if term and term != "dumb":
            return "basic"

        return "none"

    def _detect_unicode_support(self) -> bool:
        """Detect if terminal supports Unicode."""
        lang = os.environ.get("LANG", "").lower()
        lc_all = os.environ.get("LC_ALL", "").lower()

        if "utf-8" in lang or "utf-8" in lc_all:
            return True
        if "utf8" in lang or "utf8" in lc_all:
            return True

        try:
            if sys.stdout.encoding and "utf" in sys.stdout.encoding.lower():
                return True
        except Exception:
            return False

        term_program = os.environ.get("TERM_PROGRAM", "").lower()
        return term_program in {"iterm.app", "hyper", "alacritty", "kitty", "wezterm"}

    def _get_terminal_size(self) -> Tuple[int, int]:
        """Get terminal dimensions."""
        try:
            size = os.get_terminal_size()
            return size.columns, size.lines
        except OSError:
            return 80, 24  # Default fallback


_detector: Optional[TerminalDetector] = None


def _get_detector() -> TerminalDetector:
    """Get or create the global detector."""
    global _detector
    if _detector is None:
        _detector = TerminalDetector()
    return _detector


def detect_background_color() -> Literal["light", "dark", "unknown"]:
    """
    Detect terminal background color.

    Returns:
        "light", "dark", or "unknown"
    """
    return _get_detector().detect().background


def get_optimal_theme() -> str:
    """
    Get the optimal theme name for the current terminal.

    Returns:
        Theme name (e.g., "nebula-dark" or "nebula-light")
    """
    info = _get_detector().detect()

    if info.is_light:
        return "nebula-light"
    else:
        return "nebula-dark"


def get_terminal_info() -> TerminalInfo:
    """
    Get complete terminal information.

    Returns:
        TerminalInfo with all detected characteristics
    """
    return _get_detector().detect()


def should_use_ascii_fallback() -> bool:
    """
    Check if ASCII fallback should be used instead of Unicode.

    Returns:
        True if Unicode is not supported
    """
    return not _get_detector().detect().supports_unicode
