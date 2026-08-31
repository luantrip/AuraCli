"""
Clipboard Utilities for Aura TUI.

Provides cross-platform clipboard operations:
- Copy text to clipboard
- Paste text from clipboard
- Smart paste detection (files, images, large text)
"""

from __future__ import annotations

import base64
from dataclasses import dataclass
import logging
import mimetypes
import os
from pathlib import Path
import platform
import subprocess
from typing import Literal, Optional

logger = logging.getLogger(__name__)


@dataclass
class ClipboardContent:
    """Represents clipboard content with metadata."""

    content: str
    content_type: Literal["text", "file_path", "image_data", "large_text", "unknown"]
    metadata: dict

    @property
    def is_file_path(self) -> bool:
        """Return True if the text looks like a file path."""
        return self.content_type == "file_path"

    @property
    def is_image(self) -> bool:
        """Return True if the text is an image file path."""
        return self.content_type == "image_data"

    @property
    def is_large_text(self) -> bool:
        """Return True if the text exceeds the large-text threshold."""
        return self.content_type == "large_text"

    @property
    def line_count(self) -> int:
        """Return the number of lines in the text."""
        return self.content.count("\n") + 1


class ClipboardManager:
    """Cross-platform clipboard manager for the TUI.

    Supports macOS (pbcopy/pbpaste), Linux (xclip / xsel / wl-copy) and
    Windows (pyperclip or built-in). paste_smart() returns a typed result
    that distinguishes file paths, large text and regular text.
    """

    LARGE_TEXT_THRESHOLD = 10  # lines
    LARGE_TEXT_CHARS = 500  # characters

    def __init__(self):
        """Initialize clipboard manager."""
        self._system = platform.system().lower()
        self._clipboard_cmd = self._detect_clipboard_command()

    def _detect_clipboard_command(self) -> Optional[dict]:
        """Detect available clipboard commands."""
        if self._system == "darwin":
            return {"copy": ["pbcopy"], "paste": ["pbpaste"]}

        elif self._system == "linux":
            # Check for Wayland
            if os.environ.get("WAYLAND_DISPLAY") and self._command_exists("wl-copy"):
                return {"copy": ["wl-copy"], "paste": ["wl-paste"]}
            # Check for X11
            if self._command_exists("xclip"):
                return {
                    "copy": ["xclip", "-selection", "clipboard"],
                    "paste": ["xclip", "-selection", "clipboard", "-o"],
                }
            if self._command_exists("xsel"):
                return {
                    "copy": ["xsel", "--clipboard", "--input"],
                    "paste": ["xsel", "--clipboard", "--output"],
                }

        elif self._system == "windows":
            return {"copy": ["clip"], "paste": None}  # Use pyperclip for paste

        return None

    def _command_exists(self, cmd: str) -> bool:
        """Check if a command exists."""
        try:
            subprocess.run(["which", cmd], capture_output=True, check=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False

    def copy(self, text: str) -> bool:
        """
        Copy text to clipboard.

        Args:
            text: Text to copy

        Returns:
            True if successful
        """
        if not self._clipboard_cmd:
            return self._copy_pyperclip(text)

        try:
            process = subprocess.Popen(
                self._clipboard_cmd["copy"],
                stdin=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
            )
            process.communicate(text.encode("utf-8"))
            return process.returncode == 0
        except Exception as e:
            logger.error(f"Clipboard copy failed: {e}")
            return self._copy_pyperclip(text)

    def paste(self) -> Optional[str]:
        """
        Paste text from clipboard.

        Returns:
            Clipboard content or None if failed
        """
        if not self._clipboard_cmd or not self._clipboard_cmd.get("paste"):
            return self._paste_pyperclip()

        try:
            result = subprocess.run(
                self._clipboard_cmd["paste"], capture_output=True, text=True
            )
            if result.returncode == 0:
                return result.stdout
        except Exception as e:
            logger.error(f"Clipboard paste failed: {e}")

        return self._paste_pyperclip()

    def paste_smart(self) -> Optional[ClipboardContent]:
        """
        Paste with smart content detection.

        Detects:
        - File paths
        - Image data (base64)
        - Large text blocks
        - Regular text

        Returns:
            ClipboardContent with type and metadata
        """
        raw = self.paste()
        if raw is None:
            return None

        raw = raw.strip()
        if not raw:
            return ClipboardContent(content="", content_type="text", metadata={})

        # Check for file path
        if self._is_file_path(raw):
            path = Path(raw)
            metadata = {
                "exists": path.exists(),
                "is_file": path.is_file() if path.exists() else False,
                "is_dir": path.is_dir() if path.exists() else False,
            }
            if path.exists() and path.is_file():
                mime, _ = mimetypes.guess_type(str(path))
                metadata["mime_type"] = mime  # type: ignore[assignment]
                metadata["size"] = path.stat().st_size  # type: ignore[assignment]

                # Check if it's an image
                if mime and mime.startswith("image/"):
                    return ClipboardContent(
                        content=raw, content_type="image_data", metadata=metadata
                    )

            return ClipboardContent(
                content=raw, content_type="file_path", metadata=metadata
            )

        # Check for large text
        line_count = raw.count("\n") + 1
        if line_count > self.LARGE_TEXT_THRESHOLD or len(raw) > self.LARGE_TEXT_CHARS:
            return ClipboardContent(
                content=raw,
                content_type="large_text",
                metadata={
                    "lines": line_count,
                    "characters": len(raw),
                    "preview": raw[:100] + "..." if len(raw) > 100 else raw,
                },
            )

        # Regular text
        return ClipboardContent(
            content=raw,
            content_type="text",
            metadata={"lines": line_count, "characters": len(raw)},
        )

    def _is_file_path(self, text: str) -> bool:
        """Check if text looks like a file path."""
        # Quick checks
        if "\n" in text or len(text) > 500:
            return False

        text = text.strip()

        # Check for common path patterns
        if text.startswith(("/", "~/", "./", "../")):
            return True
        if text.startswith(("C:\\", "D:\\")):  # Windows
            return True

        # Check if it's an existing path
        try:
            path = Path(text).expanduser()
            return path.exists()
        except Exception:
            return False

    def read_file_as_base64(self, file_path: str) -> Optional[str]:
        """
        Read a file and return base64 encoded content.

        Args:
            file_path: Path to file

        Returns:
            Base64 encoded string or None
        """
        try:
            path = Path(file_path).expanduser()
            with open(path, "rb") as f:
                return base64.b64encode(f.read()).decode("utf-8")
        except Exception as e:
            logger.error(f"Failed to read file as base64: {e}")
            return None

    def _copy_pyperclip(self, text: str) -> bool:
        """Fallback to pyperclip for copying."""
        try:
            import pyperclip

            pyperclip.copy(text)
            return True
        except ImportError:
            logger.warning("pyperclip not installed, clipboard operations limited")
            return False
        except Exception as e:
            logger.error(f"pyperclip copy failed: {e}")
            return False

    def _paste_pyperclip(self) -> Optional[str]:
        """Fallback to pyperclip for pasting."""
        try:
            import pyperclip

            return pyperclip.paste()
        except ImportError:
            logger.warning("pyperclip not installed, clipboard operations limited")
            return None
        except Exception as e:
            logger.error(f"pyperclip paste failed: {e}")
            return None


# =============================================================================
# Convenience Functions
# =============================================================================

_manager: Optional[ClipboardManager] = None


def _get_manager() -> ClipboardManager:
    """Get or create the global clipboard manager."""
    global _manager
    if _manager is None:
        _manager = ClipboardManager()
    return _manager


def get_clipboard() -> Optional[str]:
    """
    Get text from clipboard.

    Returns:
        Clipboard content or None
    """
    return _get_manager().paste()


def set_clipboard(text: str) -> bool:
    """
    Set clipboard content.

    Args:
        text: Text to copy

    Returns:
        True if successful
    """
    return _get_manager().copy(text)


def get_clipboard_smart() -> Optional[ClipboardContent]:
    """
    Get clipboard content with smart detection.

    Returns:
        ClipboardContent with type detection
    """
    return _get_manager().paste_smart()
