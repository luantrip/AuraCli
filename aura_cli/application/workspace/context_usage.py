"""Pure context-window usage calculations."""

from __future__ import annotations


def get_context_percentage(tokens_used: int, max_tokens: int) -> float:
    """Return context usage as a percentage."""
    if max_tokens <= 0:
        return 0.0
    return (tokens_used / max_tokens) * 100


def should_compact_context(
    tokens_used: int,
    max_tokens: int,
    threshold: float = 0.8,
) -> bool:
    """Return whether usage reached the configured fractional threshold."""
    return get_context_percentage(tokens_used, max_tokens) >= threshold * 100
