"""Lightweight execution context shared across core tools.

Provides a thread-safe registry that the CLI layer populates at the start of
each tool-calling turn and clears at the end. Core tools (e.g. vision_tools)
read from here to obtain references that are owned by the CLI layer (such as
the active conversation history) without creating an illegal import dependency
from ``aura_cli.core`` → ``aura_cli.cli``.

Pattern:
    The CLI (function_call_handler.py) calls ``set_*`` before the tool loop
    and ``clear_execution_context()`` in the ``finally`` block.

    Core tools call ``get_*`` to retrieve the current values.

All setters are optional: if the CLI does not call them (e.g. in tests or
alternative runtimes) the getters return None and tools degrade gracefully.
"""

from __future__ import annotations

import threading
from typing import Any, MutableSequence, Optional

_lock = threading.Lock()

# Active conversation history for the current tool-calling turn.
# Type is intentionally Any to avoid importing concrete message types here.
_active_conversation_history: Optional[MutableSequence[Any]] = None


def set_active_conversation_history(history: Optional[MutableSequence[Any]]) -> None:
    """Register the active conversation history list for this turn.

    Called by the CLI layer at the start of each function-call loop.

    Args:
        history: The mutable conversation history list, or None to clear.
    """
    global _active_conversation_history
    with _lock:
        _active_conversation_history = history


def get_active_conversation_history() -> Optional[MutableSequence[Any]]:
    """Return the active conversation history for the current turn, or None."""
    with _lock:
        return _active_conversation_history


def clear_execution_context() -> None:
    """Clear all per-turn state.

    Should be called in the ``finally`` block of the function-call loop to
    prevent stale references from leaking between turns.
    """
    set_active_conversation_history(None)


__all__ = [
    "clear_execution_context",
    "get_active_conversation_history",
    "set_active_conversation_history",
]
