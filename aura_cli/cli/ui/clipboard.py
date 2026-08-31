"""Clipboard integration for Aura CLI — cross-platform copy to system clipboard.

Uses pbcopy (macOS), xclip/xsel (Linux) or clip (Windows). copy_to_clipboard(),
copy_code() and copy_command() provide specialised entry points with Rich
feedback. Fails gracefully when clipboard commands are unavailable.
"""

import platform
import subprocess
from typing import Optional

import rich
from rich.panel import Panel
from rich.text import Text

from aura_cli.cli.ui.constants import UIIcons, UIStyles
from aura_cli.cli.ui.display_facade import get_console

console = get_console()


def copy_to_clipboard(text: str) -> bool:
    """Copy text to system clipboard using native commands.

    Supports multiple platforms:
        - macOS: uses pbcopy
        - Linux: tries xclip, then xsel
        - Windows: uses clip

    Args:
        text: Text to copy

    Returns:
        True if successful, False otherwise
    """
    system = platform.system()

    try:
        if system == "Darwin":
            process = subprocess.Popen(
                ["pbcopy"],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            process.communicate(input=text.encode("utf-8"))
            return process.returncode == 0

        elif system == "Linux":
            for cmd in [
                ["xclip", "-selection", "clipboard"],
                ["xsel", "--clipboard", "--input"],
            ]:
                try:
                    process = subprocess.Popen(
                        cmd,
                        stdin=subprocess.PIPE,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                    )
                    process.communicate(input=text.encode("utf-8"))
                    if process.returncode == 0:
                        return True
                except FileNotFoundError:
                    continue
            return False

        elif system == "Windows":
            process = subprocess.Popen(
                ["clip"],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            process.communicate(input=text.encode("utf-8"))
            return process.returncode == 0
        else:
            return False
    except Exception:
        return False


def display_copy_feedback(success: bool, content_type: str = "content") -> None:
    """Display a Rich toast panel with copy feedback.

    Args:
        success: Whether the copy succeeded.
        content_type: Content label shown in the message (e.g. "code", "command").
    """

    if success:
        feedback_text = Text()
        feedback_text.append(f"{UIIcons.SUCCESS} ", style=UIStyles.SUCCESS)
        feedback_text.append(
            f"{content_type.capitalize()} ", style=UIStyles.SUCCESS + " bold"
        )
        feedback_text.append("copied to clipboard", style=UIStyles.SUCCESS)

        feedback_panel = Panel(
            feedback_text,
            border_style=UIStyles.BORDER_SUCCESS,
            padding=(1, 2),
            box=rich.box.ROUNDED,
        )
        console.print(feedback_panel)
    else:
        feedback_text = Text()
        feedback_text.append(f"{UIIcons.ERROR} ", style=UIStyles.ERROR)
        feedback_text.append(
            "Failed to copy to clipboard", style=UIStyles.ERROR + " bold"
        )

        feedback_panel = Panel(
            feedback_text,
            border_style=UIStyles.BORDER_ERROR,
            padding=(1, 2),
            box=rich.box.ROUNDED,
        )
        console.print(feedback_panel)


def copy_code(code: str, language: Optional[str] = None) -> bool:
    """Copy code to the clipboard with visual feedback.

    Args:
        code: Code string to copy.
        language: Optional language label shown in feedback (e.g. "python").

    Returns:
        True if successful, False otherwise.
    """
    success = copy_to_clipboard(code)
    content_label = "code" if not language else f"{language} code"
    display_copy_feedback(success, content_label)
    return success


def copy_command(command: str) -> bool:
    """Copy a shell command to the clipboard with visual feedback.

    Args:
        command: Shell command string to copy.

    Returns:
        True if successful, False otherwise.
    """
    success = copy_to_clipboard(command)
    display_copy_feedback(success, "command")
    return success


def copy_text(text: str, label: str = "text") -> bool:
    """Copy any text to the clipboard with visual feedback.

    Args:
        text: Text to copy.
        label: Content label shown in feedback (e.g. "output", "result").

    Returns:
        True if successful, False otherwise.
    """
    success = copy_to_clipboard(text)
    display_copy_feedback(success, label)
    return success
