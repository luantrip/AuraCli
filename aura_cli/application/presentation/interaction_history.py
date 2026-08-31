"""Presentation-neutral interaction history model."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import time
from typing import Any, Callable


class InteractionStatus(Enum):
    """Lifecycle states for one LLM interaction."""

    RUNNING = "running"
    SUCCESS = "success"
    ERROR = "error"
    CANCELLED = "cancelled"


@dataclass
class Interaction:
    """One recorded prompt, response and its execution metadata."""

    id: str
    timestamp: float
    prompt: str
    response: str | None = None
    status: InteractionStatus = InteractionStatus.RUNNING
    prompt_tokens: int = 0
    generated_tokens: int = 0
    execution_time: float = 0.0
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    error: str | None = None

    def __post_init__(self) -> None:
        if self.tool_calls is None:
            self.tool_calls = []


class ConsoleHistory:
    """In-memory interaction collection independent from its rendering surface."""

    def __init__(self, clock: Callable[[], float] = time.time) -> None:
        self._clock = clock
        self.interactions: list[Interaction] = []
        self.selected_id: str | None = None

    def add_interaction(self, prompt: str, interaction_id: str | None = None) -> str:
        timestamp = self._clock()
        resolved_id = interaction_id or f"interaction_{int(timestamp * 1000)}"
        self.interactions.append(Interaction(resolved_id, timestamp, prompt))
        self.selected_id = resolved_id
        return resolved_id

    def update_interaction(
        self,
        interaction_id: str,
        response: str | None = None,
        status: InteractionStatus | None = None,
        prompt_tokens: int | None = None,
        generated_tokens: int | None = None,
        execution_time: float | None = None,
        tool_calls: list[dict[str, Any]] | None = None,
        error: str | None = None,
    ) -> bool:
        interaction = self.get_interaction(interaction_id)
        if interaction is None:
            return False
        changes = {
            "response": response,
            "status": status,
            "prompt_tokens": prompt_tokens,
            "generated_tokens": generated_tokens,
            "execution_time": execution_time,
            "tool_calls": tool_calls,
            "error": error,
        }
        for name, value in changes.items():
            if value is not None:
                setattr(interaction, name, value)
        return True

    def get_interaction(self, interaction_id: str) -> Interaction | None:
        return next(
            (item for item in self.interactions if item.id == interaction_id), None
        )
