"""Compatibility adapter for application tangent management."""

from typing import Any, Callable, Dict, List, Optional

from aura_cli.application.workspace.tangent import (
    ConversationCheckpoint,
    TangentState,
)
from aura_cli.application.workspace.tangent import (
    TangentManager as ApplicationTangentManager,
)
from aura_cli.core.logger import get_logger

logger = get_logger(__name__)


ForgetSelector = Callable[[List[Dict[str, Any]]], Optional[int]]

_registered_selector: Optional[ForgetSelector] = None


def configure_forget_selector(selector: Optional[ForgetSelector]) -> None:
    """Register the interactive picker used by ``/tangent forget``.

    ``core`` must not import the presentation layer, so the CLI injects its prompt
    at startup. Passing ``None`` restores the plain-text fallback.
    """
    global _registered_selector
    _registered_selector = selector


def _forget_selection(user_messages: List[Dict[str, Any]]) -> Optional[int]:
    """Resolve how many messages to forget; ``None`` means cancelled.

    Any failure cancels. It must never default to forgetting a message: dropping
    conversation history is destructive and a broken prompt is not consent.
    """
    try:
        if _registered_selector is not None:
            return _registered_selector(user_messages)
        return int(input(f"How many messages to forget? (1-{len(user_messages)}): "))
    except (ValueError, EOFError, KeyboardInterrupt):
        return None
    except Exception as exc:
        logger.warning("Forget selection failed; cancelling: %s", exc)
        return None


class TangentManager(ApplicationTangentManager):
    """Application manager configured with the terminal selection adapter."""

    def __init__(self) -> None:
        super().__init__(forget_selector=_forget_selection)


__all__ = [
    "ConversationCheckpoint",
    "TangentManager",
    "TangentState",
    "configure_forget_selector",
]
