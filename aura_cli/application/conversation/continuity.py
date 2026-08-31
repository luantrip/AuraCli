"""Bounded continuation policy for autonomous conversational turns."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import re
import time
from typing import Callable


class TurnStopReason(str, Enum):
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"
    BUDGET = "budget"
    TIME_LIMIT = "time_limit"
    STEP_LIMIT = "step_limit"
    USER = "user"


_CONTINUOUS_AUTHORIZATION = re.compile(
    r"\b(siga automaticamente|continue automaticamente|não pare|nao pare|"
    r"até concluir|ate concluir|do not stop|keep going|continue until)\b",
    re.IGNORECASE,
)


def allows_continuation(request: str) -> bool:
    return bool(_CONTINUOUS_AUTHORIZATION.search(request))


@dataclass
class ContinuationController:
    max_iterations: int = 8
    max_seconds: float = 300.0
    checkpoint_interval: int = 5
    clock: Callable[[], float] = time.monotonic
    iterations: int = 0
    operations_since_checkpoint: int = 0
    started_at: float = field(init=False)

    def __post_init__(self) -> None:
        if self.max_iterations < 1 or self.max_seconds <= 0:
            raise ValueError("continuation limits must be positive")
        self.started_at = self.clock()

    def begin_iteration(self) -> TurnStopReason | None:
        if self.clock() - self.started_at >= self.max_seconds:
            return TurnStopReason.TIME_LIMIT
        if self.iterations >= self.max_iterations:
            return TurnStopReason.STEP_LIMIT
        self.iterations += 1
        return None

    def record_operations(self, count: int) -> bool:
        self.operations_since_checkpoint += max(count, 0)
        if self.operations_since_checkpoint < self.checkpoint_interval:
            return False
        self.operations_since_checkpoint = 0
        return True


def stop_message(reason: TurnStopReason) -> str:
    messages = {
        TurnStopReason.TIME_LIMIT: "Execução interrompida: limite de tempo do turno atingido.",
        TurnStopReason.STEP_LIMIT: "Execução interrompida: limite de etapas do turno atingido.",
        TurnStopReason.BUDGET: "Execução interrompida: orçamento do turno esgotado.",
        TurnStopReason.USER: "Execução interrompida pelo usuário.",
        TurnStopReason.BLOCKED: "Execução bloqueada; é necessária uma condição externa.",
        TurnStopReason.FAILED: "Execução encerrada após falha terminal.",
        TurnStopReason.COMPLETED: "Execução concluída.",
    }
    return messages[reason]


__all__ = [
    "ContinuationController",
    "TurnStopReason",
    "allows_continuation",
    "stop_message",
]
