"""Aura CLI TUI auxiliary tool integration.

Provides launcher/integration helpers for optional tools outside the main
chat/delegation runtime.

Features:
    - AuraPaint: native ANSI art editor launcher
    - File Manager: optional TUI file browser launcher
    - Monitor: optional terminal web browser launcher
    - Automatic tool availability detection
    - Subprocess and screen integration

Tools:
    AuraPaint: native ANSI art editor
    Files: auxiliary file manager
    Monitor: auxiliary browser
"""

from dataclasses import dataclass
import importlib.util
import os
from pathlib import Path
import shutil
import sys
from typing import Optional

from aura_cli.tui.tools.monitor import (
    get_monitor_binary as _get_monitor_binary,
)

__all__ = [
    "FILES_AVAILABLE",
    "MONITOR_AVAILABLE",
    "PAINT_AVAILABLE",
    "TUIFI_AVAILABLE",
    "ToolAvailability",
    "get_monitor_binary",
    "get_tool_availability",
    "launch_files",
    "launch_monitor",
    "launch_paint",
]


@dataclass(frozen=True)
class ToolAvailability:
    """Current availability snapshot for auxiliary TUI tools."""

    paint: bool
    files: bool
    monitor: bool
    monitor_binary: str | None = None

    @property
    def any_available(self) -> bool:
        """Return whether at least one auxiliary tool can be launched."""
        return self.paint or self.files or self.monitor


def _check_command(cmd: str) -> bool:
    """Check if command is available in PATH.

    Args:
        cmd: Command name to check

    Returns:
        True if command exists in PATH
    """
    return shutil.which(cmd) is not None


def _find_monitor_binary() -> Optional[str]:
    """Delegate monitor discovery to its package-level authority."""
    return _get_monitor_binary(refresh=True)


def get_tool_availability() -> ToolAvailability:
    """Resolve the current availability of auxiliary tools.

    The module-level booleans below remain as compatibility snapshots. New UI
    surfaces should use this function so an installed/removed binary is not
    cached forever in a screen imported earlier.
    """
    monitor_binary = _find_monitor_binary()
    return ToolAvailability(
        paint=importlib.util.find_spec("aura_cli.tui.tools.paint") is not None,
        files=_check_command("tuifi"),
        monitor=monitor_binary is not None,
        monitor_binary=monitor_binary,
    )


_TOOL_AVAILABILITY = get_tool_availability()
PAINT_AVAILABLE = _TOOL_AVAILABILITY.paint
TUIFI_AVAILABLE = _TOOL_AVAILABILITY.files
FILES_AVAILABLE = _TOOL_AVAILABILITY.files
_MONITOR_BINARY = _TOOL_AVAILABILITY.monitor_binary
MONITOR_AVAILABLE = _TOOL_AVAILABILITY.monitor


def get_monitor_binary() -> Optional[str]:
    """Get the current monitor binary path."""
    return _get_monitor_binary(refresh=True)


def launch_paint(path: Optional[str] = None) -> int:
    """Launch the bundled AuraPaint editor in a separate process.

    Launches Paint in a separate process to avoid event loop conflicts.

    Args:
        path: Optional file path to open

    Returns:
        Exit code from process (0 on success)
    """
    import subprocess

    cmd = [sys.executable, "-m", "aura_cli.tui.tools.paint"]
    if path:
        cmd.append(path)

    try:
        result = subprocess.run(cmd)
        return result.returncode
    except Exception as e:
        print(f"Error launching AuraPaint: {e}")
        return 1


def launch_files(path: Optional[str] = None) -> int:
    """Launch TUIFIManager file manager or show fallback message.

    Args:
        path: Optional directory path to start in

    Returns:
        Exit code from process
    """
    if not TUIFI_AVAILABLE or not get_tool_availability().files:
        print(
            "TUIFIManager não está instalado; use Ctrl+F dentro da TUI "
            "para o gerenciador integrado."
        )
        return 1

    cmd = ["tuifi"]
    if path:
        cmd.append(path)
    try:
        import subprocess

        result = subprocess.run(cmd, capture_output=False)
        return result.returncode
    except Exception as e:
        from aura_cli.core.logger import get_logger

        get_logger(__name__).warning(f"Error launching tuifi: {e}")
        return 1


def launch_monitor(url: Optional[str] = None) -> int:
    """Launch Chawan terminal browser.

    Args:
        url: Optional URL to open

    Returns:
        Exit code from process
    """
    binary = get_monitor_binary() or "cha"
    cmd = [binary]
    if url:
        cmd.append(url)
    try:
        import subprocess

        result = subprocess.run(cmd, capture_output=False)
        return result.returncode
    except FileNotFoundError:
        from aura_cli.core.logger import get_logger

        get_logger(__name__).warning(f"Monitor '{binary}' not found.")
        return 1
    except Exception as e:
        from aura_cli.core.logger import get_logger

        get_logger(__name__).warning(f"Error launching monitor: {e}")
        return 1
