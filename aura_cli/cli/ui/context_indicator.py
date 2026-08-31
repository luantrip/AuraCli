"""
Context usage indicator for Aura CLI.

Provides visual feedback about context window usage with color-coded percentage.
Inspired by Kiro CLI's context usage indicator.
"""

from rich.text import Text

from aura_cli.application.workspace.context_usage import (
    get_context_percentage,
    should_compact_context,
)
from aura_cli.cli.ui.constants import UIStyles

__all__ = [
    "get_context_indicator",
    "get_context_indicator_string",
    "get_context_percentage",
    "should_compact_context",
]


def get_context_indicator(tokens_used: int, max_tokens: int) -> Text:
    """
    Get color-coded context usage indicator.

    Color scheme:
    - Green: < 50% usage (safe)
    - Yellow: 50-89% usage (warning)
    - Red: 90-100% usage (critical)

    Args:
        tokens_used: Number of tokens currently used
        max_tokens: Maximum tokens available

    Returns:
        Rich Text object with colored percentage

    Example:
        >>> indicator = get_context_indicator(1000, 10000)
        >>> print(indicator)  # "10%" in green
    """
    percentage = get_context_percentage(tokens_used, max_tokens)

    # Determine color based on usage
    if percentage < 50:
        color = UIStyles.STATUS_SUCCESS
    elif percentage < 90:
        color = UIStyles.STATUS_WARNING
    else:
        color = UIStyles.STATUS_ERROR

    return Text(f"{percentage:.0f}%", style=color)


def get_context_indicator_string(tokens_used: int, max_tokens: int) -> str:
    """
    Get context indicator as plain string with Rich markup.

    Args:
        tokens_used: Number of tokens currently used
        max_tokens: Maximum tokens available

    Returns:
        String with Rich color markup

    Example:
        >>> indicator = get_context_indicator_string(1000, 10000)
        >>> print(indicator)  # "[green]10%[/]"
    """
    percentage = get_context_percentage(tokens_used, max_tokens)

    if percentage < 50:
        color = UIStyles.STATUS_SUCCESS
    elif percentage < 90:
        color = UIStyles.STATUS_WARNING
    else:
        color = UIStyles.STATUS_ERROR

    return f"[{color}]{percentage:.0f}%[/]"
