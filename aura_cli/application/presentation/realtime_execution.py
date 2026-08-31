"""Canonical temporal language for live execution feedback."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum

from aura_cli.application.presentation.work_items import WorkItemEnvelope, WorkItemState


class ExecutionMotion(str, Enum):
    STILL = "still"
    ACTIVE = "active"
    STREAMING = "streaming"
    WAITING = "waiting"
    TERMINAL = "terminal"


@dataclass(frozen=True)
class RealtimeExecution:
    key: str
    motion: ExecutionMotion
    elapsed_seconds: int
    heartbeat_due: bool
    background: bool
    replace: bool
    consolidate: bool


def describe_realtime_execution(
    item: WorkItemEnvelope,
    *,
    now: datetime | None = None,
    heartbeat_seconds: int = 15,
    background: bool = False,
) -> RealtimeExecution:
    """Derive toolkit-neutral live behavior from a canonical work item."""
    current = item.finished_at or now or datetime.now(timezone.utc)
    anchor = item.started_at or item.updated_at
    elapsed = max(0, int((current - anchor).total_seconds()))
    motion = _motion(item.state)
    live = motion in {
        ExecutionMotion.ACTIVE,
        ExecutionMotion.STREAMING,
        ExecutionMotion.WAITING,
    }
    return RealtimeExecution(
        key=item.identity.stable_key,
        motion=motion,
        elapsed_seconds=elapsed,
        heartbeat_due=live and heartbeat_seconds > 0 and elapsed >= heartbeat_seconds,
        background=background,
        replace=motion is not ExecutionMotion.TERMINAL,
        consolidate=motion is ExecutionMotion.TERMINAL,
    )


def format_elapsed(seconds: int) -> str:
    seconds = max(0, int(seconds))
    minutes, remainder = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours}h{minutes:02d}m"
    if minutes:
        return f"{minutes}m{remainder:02d}s"
    return f"{remainder}s"


def _motion(state: WorkItemState) -> ExecutionMotion:
    if state is WorkItemState.STREAMING:
        return ExecutionMotion.STREAMING
    if state in {WorkItemState.WAITING_EXTERNAL, WorkItemState.AWAITING_USER}:
        return ExecutionMotion.WAITING
    if state in {WorkItemState.PREPARING, WorkItemState.RUNNING}:
        return ExecutionMotion.ACTIVE
    if state in {
        WorkItemState.COMPLETED,
        WorkItemState.PARTIAL,
        WorkItemState.FAILED,
        WorkItemState.DECLINED,
        WorkItemState.CANCELLED,
        WorkItemState.INTERRUPTED,
    }:
        return ExecutionMotion.TERMINAL
    return ExecutionMotion.STILL


__all__ = [
    "ExecutionMotion",
    "RealtimeExecution",
    "describe_realtime_execution",
    "format_elapsed",
]
