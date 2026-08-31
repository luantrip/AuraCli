"""Lifecycle protocol for suspending into and returning from external tools."""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum


class ExternalToolPhase(str, Enum):
    SUSPENDING = "suspending"
    LAUNCHING = "launching"
    ATTACHED = "attached"
    RETURNING = "returning"
    COMPLETED = "completed"
    FAILED = "failed"
    INTERRUPTED = "interrupted"


@dataclass(frozen=True)
class ExternalToolSession:
    session_id: str
    tool_name: str
    phase: ExternalToolPhase
    initial_cwd: str
    current_cwd: str
    artifacts: tuple[str, ...] = ()
    exit_code: int | None = None
    error: str | None = None
    focus_returned: bool = False

    @property
    def cwd_changed(self) -> bool:
        return self.current_cwd != self.initial_cwd


_ALLOWED = {
    ExternalToolPhase.SUSPENDING: {
        ExternalToolPhase.LAUNCHING,
        ExternalToolPhase.FAILED,
    },
    ExternalToolPhase.LAUNCHING: {ExternalToolPhase.ATTACHED, ExternalToolPhase.FAILED},
    ExternalToolPhase.ATTACHED: {
        ExternalToolPhase.RETURNING,
        ExternalToolPhase.INTERRUPTED,
        ExternalToolPhase.FAILED,
    },
    ExternalToolPhase.RETURNING: {
        ExternalToolPhase.COMPLETED,
        ExternalToolPhase.FAILED,
        ExternalToolPhase.INTERRUPTED,
    },
}


def begin_external_tool(
    session_id: str, tool_name: str, cwd: str
) -> ExternalToolSession:
    return ExternalToolSession(
        session_id, tool_name, ExternalToolPhase.SUSPENDING, cwd, cwd
    )


def transition_external_tool(
    session: ExternalToolSession,
    phase: ExternalToolPhase,
    *,
    cwd: str | None = None,
    artifacts: tuple[str, ...] | None = None,
    exit_code: int | None = None,
    error: str | None = None,
    focus_returned: bool | None = None,
) -> ExternalToolSession:
    if phase is session.phase:
        return session
    if phase not in _ALLOWED.get(session.phase, set()):
        raise ValueError(
            f"illegal external tool transition: {session.phase.value} -> {phase.value}"
        )
    return replace(
        session,
        phase=phase,
        current_cwd=cwd or session.current_cwd,
        artifacts=artifacts if artifacts is not None else session.artifacts,
        exit_code=exit_code if exit_code is not None else session.exit_code,
        error=error if error is not None else session.error,
        focus_returned=(
            focus_returned if focus_returned is not None else session.focus_returned
        ),
    )


__all__ = [
    "ExternalToolPhase",
    "ExternalToolSession",
    "begin_external_tool",
    "transition_external_tool",
]
