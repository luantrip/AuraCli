"""
AuraConfirmation Utilities - Standardized confirmation prompts.

Provides consistent confirmation prompts with styled messages and
keyboard interrupt handling.

Note: This module provides utility functions, not ComponentBase classes.
For component-based UI, see other components in this package.

Features:
    - Styled Prompts: Warning-styled confirmation messages
    - Default Values: Configurable default (Yes/No)
    - Interrupt Handling: Graceful KeyboardInterrupt/EOFError handling
    - Cancellation Message: Clear cancellation feedback
    - Timer Visual: Optional timeout with visual countdown (polls stdin)
    - Rich Context: Panel with context information

Usage:
    >>> from aura_cli.cli.ui.components.confirmation import ask_confirmation
    >>> if ask_confirmation("Delete file?", default=False):
    ...     delete_file()
"""

import select
import sys
import time
from typing import Optional

from rich.text import Text

from aura_cli.application.presentation.cli_visual import SurfaceChrome
from aura_cli.application.presentation.confirmation import parse_confirmation_answer
from aura_cli.cli.ui.composition.visual_surface import surface_panel
from aura_cli.cli.ui.constants import UIIcons, UIStyles


def _confirm_with_timeout(
    message: str,
    default: bool,
    prompt_suffix: str,
    timeout: float,
    console,
    warning_style: str,
) -> bool:
    """Inner loop for timed confirmation via select.select polling."""
    console.print(Text(message, style=warning_style))
    start_time = time.time()

    while time.time() - start_time < timeout:
        remaining = int(timeout - (time.time() - start_time))
        sys.stdout.write(f"\r  {UIIcons.TIMER} ({remaining}s) {prompt_suffix}: ")
        sys.stdout.flush()

        try:
            ready, _, _ = select.select([sys.stdin], [], [], 0.5)
        except (OSError, ValueError):
            ready = []
            time.sleep(0.5)

        if not ready:
            continue

        try:
            raw = sys.stdin.readline()
        except (KeyboardInterrupt, EOFError):
            sys.stdout.write("\r" + " " * 80 + "\r")
            sys.stdout.flush()
            console.print(
                Text(
                    f"{UIIcons.CANCEL} Operação cancelada pelo usuário.",
                    style=warning_style,
                )
            )
            return False

        sys.stdout.write("\r" + " " * 80 + "\r")
        sys.stdout.flush()

        if not raw:
            return default

        result = parse_confirmation_answer(raw, default)
        if result is not None:
            return result
        else:
            console.print(
                Text(
                    "  Entrada inválida. Use s/n ou pressione Enter.",
                    style=warning_style,
                )
            )

    # Timeout reached
    sys.stdout.write("\r" + " " * 80 + "\r")
    sys.stdout.flush()
    console.print(
        Text(f"{UIIcons.TIMER} Timeout — operação cancelada.", style=warning_style)
    )
    return False


def _confirm_blocking(
    message: str,
    default: bool,
    prompt_suffix: str,
    console,
    warning_style: str,
) -> bool:
    """Inner loop for blocking (no-timeout) confirmation — up to 3 attempts."""
    for _ in range(3):
        try:
            sys.stdout.write(f"{message} {prompt_suffix} ")
            sys.stdout.flush()
            line = sys.stdin.readline()
            if not line:
                return default
            result = parse_confirmation_answer(line, default)
            if result is not None:
                return result
            console.print(
                Text(
                    "Entrada inválida. Responda com s/n ou pressione Enter para o padrão.",
                    style=warning_style,
                )
            )
        except (KeyboardInterrupt, EOFError):
            console.print(
                Text(
                    f"\n{UIIcons.CANCEL} Operação cancelada pelo usuário.",
                    style=warning_style,
                )
            )
            return False
    return default


def ask_confirmation(
    message: str,
    default: bool = True,
    context: Optional[str] = None,
    timeout: Optional[float] = None,
) -> bool:
    """
    Display standardized confirmation prompt with optional context panel.

    Uses a minimal, robust stdin-based implementation to avoid issues with
    nested event loops or conflicting input handlers.

    When *timeout* is set, the prompt polls stdin using select.select() so
    the user can respond at any point during the countdown.

    Args:
        message: Message to display in prompt
        default: Default value if user presses Enter (default: True)
        context: Optional context information to display
        timeout: Optional timeout in seconds (auto-rejects if exceeded)

    Returns:
        True if user confirms, False otherwise
    """
    from aura_cli.cli.ui.display_facade import get_console

    console = get_console()

    # Context panel (optional)
    if context:
        body_style = UIStyles.safe_style("BODY", "white")
        subtitle_style = UIStyles.safe_style("SUBTITLE", "white")
        border_style = UIStyles.safe_style("BORDER_MUTED", "dim white")
        context_panel = surface_panel(
            Text(context, style=body_style),
            title=f"[{subtitle_style}]{UIIcons.INFO} Contexto[/{subtitle_style}]",
            border_style=border_style,
            chrome=SurfaceChrome.FOCUS,
            console_width=console.width,
        )
        console.print(context_panel)

    warning_style = UIStyles.safe_style("WARNING", "yellow")
    prompt_suffix = "[S/n]" if default else "[s/N]"

    if timeout is not None and timeout > 0:
        return _confirm_with_timeout(
            message, default, prompt_suffix, timeout, console, warning_style
        )

    return _confirm_blocking(message, default, prompt_suffix, console, warning_style)


# Register the Rich implementation without making Core import this adapter.
from aura_cli.core.tools.human_intervention_adapter import (
    configure_local_confirmation_handler,
)

configure_local_confirmation_handler(
    lambda message, **kwargs: ask_confirmation(message, **kwargs)
)
