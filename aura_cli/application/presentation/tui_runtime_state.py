"""Semantic runtime state for TUI status, footer, and loading presentation."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from aura_cli.application.presentation.tui_surfaces import (
    PresentationIntent,
    SurfaceRequest,
)


class RuntimePhase(str, Enum):
    """Stable lifecycle phases exposed to the TUI chrome."""

    BOOTING = "booting"
    READY = "ready"
    LOADING = "loading"
    THINKING = "thinking"
    EXECUTING = "executing"
    WAITING_INPUT = "waiting_input"
    ERROR = "error"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    STOPPED = "stopped"

    # Compatibility aliases for the first reducer draft and external callers.
    RUNNING = EXECUTING
    WAITING_USER = WAITING_INPUT
    FAILED = ERROR
    SUCCEEDED = COMPLETED


class RuntimeAction(str, Enum):
    """Local app actions that do not originate from a surface request."""

    BOOT = "booting"
    READY = "ready"
    LOADING = "loading"
    THINKING = "thinking"
    EXECUTING = "executing"
    WAITING_INPUT = "waiting_input"
    ERROR = "error"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    STOPPED = "stopped"


@dataclass(frozen=True)
class TuiRuntimeState:
    """Current semantic phase and the latest user-facing status message."""

    phase: RuntimePhase = RuntimePhase.READY
    message: str = ""
    task_id: str | None = None

    @property
    def loading_visible(self) -> bool:
        """Return whether the animated loading indicator should be visible."""
        return self.phase in {
            RuntimePhase.LOADING,
            RuntimePhase.THINKING,
            RuntimePhase.EXECUTING,
        }

    @property
    def is_busy(self) -> bool:
        """Return whether work is active or waiting for user input."""
        return self.loading_visible or self.phase is RuntimePhase.WAITING_INPUT

    @property
    def footer_message(self) -> str:
        """Return the concise status suitable for footer chrome."""
        defaults = {
            RuntimePhase.BOOTING: "Inicializando",
            RuntimePhase.READY: "Pronto",
            RuntimePhase.LOADING: "Carregando",
            RuntimePhase.THINKING: "Pensando",
            RuntimePhase.EXECUTING: "Executando",
            RuntimePhase.WAITING_INPUT: "Aguardando sua decisão",
            RuntimePhase.ERROR: "Erro",
            RuntimePhase.COMPLETED: "Concluído",
            RuntimePhase.CANCELLED: "Cancelado",
            RuntimePhase.STOPPED: "Interrompido",
        }
        return self.message or defaults[self.phase]


def transition_runtime_state(
    current: TuiRuntimeState,
    action: RuntimeAction,
    *,
    message: str = "",
    task_id: str | None = None,
) -> TuiRuntimeState:
    """Apply one local lifecycle action without importing Textual."""
    phase = RuntimePhase(action.value)
    if phase is RuntimePhase.READY:
        return TuiRuntimeState(phase=phase)
    return TuiRuntimeState(
        phase=phase,
        message=message,
        task_id=task_id if task_id is not None else current.task_id,
    )


def reduce_runtime_state(
    current: TuiRuntimeState,
    request: SurfaceRequest,
) -> TuiRuntimeState:
    """Reduce one surface intent into a stable runtime phase.

    Surface content is displayed as context only. It never determines a phase.
    The backwards-compatible surface contract therefore maps generic progress
    to ``executing``; callers with local lifecycle knowledge can use
    :func:`transition_runtime_state` for loading or thinking.
    """
    intent = request.intent
    if intent is PresentationIntent.PROGRESS:
        return TuiRuntimeState(
            RuntimePhase.EXECUTING,
            request.content,
            request.task_id,
        )
    if intent is PresentationIntent.DECISION:
        return TuiRuntimeState(
            RuntimePhase.WAITING_INPUT,
            request.content or "Aguardando sua decisão",
            request.task_id,
        )
    if intent is PresentationIntent.SUCCESS:
        return TuiRuntimeState(
            RuntimePhase.COMPLETED,
            request.content,
            request.task_id,
        )
    if intent is PresentationIntent.RESPONSE:
        return TuiRuntimeState(
            RuntimePhase.COMPLETED,
            request.content,
            request.task_id,
        )
    if intent is PresentationIntent.ERROR:
        return TuiRuntimeState(
            RuntimePhase.ERROR,
            request.content,
            request.task_id,
        )
    # Warnings remain in their notification/activity surface. They do not
    # represent a runtime phase transition and must not be promoted to errors.
    return current


__all__ = [
    "RuntimeAction",
    "RuntimePhase",
    "TuiRuntimeState",
    "reduce_runtime_state",
    "transition_runtime_state",
]
