"""Audit agent event streams for explicit visual lifecycle symmetry."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from aura_cli.application.agents.events import AgiEvent, AgiEventType


@dataclass(frozen=True)
class LifecycleAudit:
    started: tuple[str, ...]
    terminal: tuple[str, ...]
    resumable: tuple[str, ...]
    incomplete: tuple[str, ...]
    orphan_terminal: tuple[str, ...]

    @property
    def is_symmetric(self) -> bool:
        return not self.incomplete and not self.orphan_terminal


def audit_event_lifecycles(events: Iterable[AgiEvent]) -> LifecycleAudit:
    """Prove that each task start reaches a terminal or resumable visible state."""
    started: set[str] = set()
    terminal: set[str] = set()
    resumable: set[str] = set()
    active: set[str] = set()
    orphan_terminal: set[str] = set()

    terminal_types = {
        AgiEventType.TASK_COMPLETE,
        AgiEventType.TASK_ERROR,
        AgiEventType.TASK_CANCELLED,
    }
    for event in events:
        task_id = event.task_id
        if event.type == AgiEventType.TASK_START:
            started.add(task_id)
            active.add(task_id)
            terminal.discard(task_id)
            resumable.discard(task_id)
            continue

        if event.type in terminal_types or (
            event.type == AgiEventType.APPROVAL_RESOLVED
            and event.data.get("status") == "declined"
        ):
            if task_id not in started:
                orphan_terminal.add(task_id)
            terminal.add(task_id)
            active.discard(task_id)
            resumable.discard(task_id)
            continue

        if event.type in {
            AgiEventType.APPROVAL_REQUESTED,
            AgiEventType.EXTERNAL_WAIT_STARTED,
        } or (
            event.type == AgiEventType.TASK_INTERRUPTED
            and bool(event.data.get("resumable"))
        ):
            if task_id in started:
                active.discard(task_id)
                resumable.add(task_id)
            continue

        if (
            event.type
            in {
                AgiEventType.APPROVAL_RESOLVED,
                AgiEventType.EXTERNAL_WAIT_ENDED,
            }
            and task_id in started
        ):
            resumable.discard(task_id)
            active.add(task_id)

    return LifecycleAudit(
        started=tuple(sorted(started)),
        terminal=tuple(sorted(terminal)),
        resumable=tuple(sorted(resumable)),
        incomplete=tuple(sorted(active)),
        orphan_terminal=tuple(sorted(orphan_terminal)),
    )


__all__ = ["LifecycleAudit", "audit_event_lifecycles"]
