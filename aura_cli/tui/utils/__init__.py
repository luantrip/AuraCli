"""
Utility modules for Aura TUI.

This package contains helper utilities:
- Terminal Detector: Detects terminal capabilities and background
- Clipboard Utils: Cross-platform clipboard operations
"""

from aura_cli.tui.utils.clipboard_utils import (
    ClipboardManager,
    get_clipboard,
    set_clipboard,
)
from aura_cli.tui.utils.terminal_detector import (
    TerminalDetector,
    detect_background_color,
    get_optimal_theme,
    get_terminal_info,
)

__all__ = [
    "ClipboardManager",
    "TerminalDetector",
    "detect_background_color",
    "get_clipboard",
    "get_optimal_theme",
    "get_terminal_info",
    "set_clipboard",
]
