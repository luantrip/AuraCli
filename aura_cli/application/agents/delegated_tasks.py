"""State and lifecycle policies for work delegated to background agents."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from copy import deepcopy
from dataclasses import dataclass
from enum import Enum
import logging
import threading
import time
from typing import Any, Protocol

logger = logging.getLogger(__name__)

DelegatedTask = dict[str, Any]
PersistDelegatedTask = Callable[..., None]


class DelegatedTaskStatus(str, Enum):
    ACCEPTED = "accepted"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMED_OUT = "timed_out"


_STATUS_ALIASES = {
    "queued": DelegatedTaskStatus.ACCEPTED,
    "started": DelegatedTaskStatus.ACCEPTED,
    "in_progress": DelegatedTaskStatus.RUNNING,
    "success": DelegatedTaskStatus.COMPLETED,
    "done": DelegatedTaskStatus.COMPLETED,
    "error": DelegatedTaskStatus.FAILED,
    "stopped": DelegatedTaskStatus.CANCELLED,
    "timeout": DelegatedTaskStatus.TIMED_OUT,
}


def normalize_delegated_status(status: str) -> DelegatedTaskStatus:
    normalized = str(status or "").casefold()
    try:
        return DelegatedTaskStatus(normalized)
    except ValueError:
        return _STATUS_ALIASES.get(normalized, DelegatedTaskStatus.ACCEPTED)


class DelegatedWorker(Protocol):
    final_result: Mapping[str, Any] | None
    final_error: Mapping[str, Any] | None
    last_snapshot_path: str | None
    completed_at: float | None


@dataclass(frozen=True)
class DelegatedTaskCounts:
    total: int
    agi: int
    ops: int


class DelegatedTaskRegistry:
    """Own delegated-task state without depending on threads, CLI, or storage."""

    def __init__(
        self,
        persist_callback: PersistDelegatedTask | None = None,
        *,
        clock: Callable[[], float] = time.time,
    ) -> None:
        self._tasks: dict[str, DelegatedTask] = {}
        self._persist_callback = persist_callback
        self._clock = clock
        self._lock = threading.RLock()

    @staticmethod
    def _snapshot_task(task: DelegatedTask) -> DelegatedTask:
        """Copy task data without attempting to deepcopy a live worker object."""
        return {
            key: value if key == "worker_ref" else deepcopy(value)
            for key, value in task.items()
        }

    def _live_task(self, task: DelegatedTask) -> DelegatedTask | None:
        task_id = str(task.get("task_id") or "")
        return self._tasks.get(task_id) if task_id else None

    def _sync_snapshot(self, target: DelegatedTask, source: DelegatedTask) -> None:
        if target is not source:
            target.clear()
            target.update(self._snapshot_task(source))

    @property
    def tasks(self) -> dict[str, DelegatedTask]:
        """Return a defensive snapshot of registry tasks."""
        with self._lock:
            return {
                task_id: self._snapshot_task(task)
                for task_id, task in self._tasks.items()
            }

    @property
    def live_tasks(self) -> dict[str, DelegatedTask]:
        """Return the legacy mutable map for the CLI adapter only."""
        return self._tasks

    def register_task(
        self,
        *,
        agent_type: str,
        task_id: str,
        thread_name: str,
        prompt: str,
        delegation_payload: Mapping[str, Any],
        mode: str | None = None,
        worker_ref: DelegatedWorker | Any | None = None,
    ) -> None:
        with self._lock:
            if task_id in self._tasks:
                return
            created_at = self._clock()
            task = {
                "task_id": task_id,
                "agent_type": agent_type,
                "thread_name": thread_name,
                "prompt": prompt,
                "mode": mode,
                "delegation_payload": deepcopy(dict(delegation_payload)),
                "created_at": created_at,
                "persisted_status": DelegatedTaskStatus.ACCEPTED.value,
                "worker_ref": worker_ref,
                "final_result": None,
                "final_error": None,
                "snapshot_path": None,
                "fallback_reason": None,
            }
            self._tasks[task_id] = task
            self._persist_task(task)

    def add_rehydrated_task(self, task: Mapping[str, Any]) -> bool:
        """Add persisted state once, without writing it back during hydration."""
        task_id = str(task.get("task_id") or "")
        with self._lock:
            if not task_id or task_id in self._tasks:
                return False
            hydrated = deepcopy(dict(task))
            hydrated.setdefault("worker_ref", None)
            self._tasks[task_id] = hydrated
            return True

    def reconcile_state(self, task: DelegatedTask) -> bool:
        """Copy a live worker's final state and persist only when it changed."""
        with self._lock:
            live_task = self._live_task(task)
            if live_task is None:
                return False
            worker = live_task.get("worker_ref")
            if worker is None:
                return False
            changed = False
            final_result = getattr(worker, "final_result", None)
            final_error = getattr(worker, "final_error", None)
            snapshot_path = getattr(worker, "last_snapshot_path", None)
            completed_at = getattr(worker, "completed_at", None)

            if final_result and final_result != live_task.get("final_result"):
                live_task["final_result"] = deepcopy(dict(final_result))
                live_task["persisted_status"] = normalize_delegated_status(
                    str(final_result.get("status", "completed"))
                ).value
                live_task["fallback_reason"] = final_result.get("fallback_reason")
                changed = True
            if final_error and final_error != live_task.get("final_error"):
                live_task["final_error"] = deepcopy(dict(final_error))
                live_task["persisted_status"] = DelegatedTaskStatus.FAILED.value
                live_task["fallback_reason"] = final_error.get("fallback_reason")
                changed = True
            for key, value in (
                ("snapshot_path", snapshot_path),
                ("completed_at", completed_at),
            ):
                if value and value != live_task.get(key):
                    live_task[key] = value
                    changed = True
            if changed:
                self._persist_task(live_task)
            self._sync_snapshot(task, live_task)
            return changed

    def resolve_task(
        self, task_id: str = "", agent_type: str = ""
    ) -> DelegatedTask | None:
        with self._lock:
            if task_id:
                task = self._tasks.get(task_id)
                return self._snapshot_task(task) if task else None
            candidates = self.sorted_tasks(agent_type)
            return candidates[0] if candidates else None

    def sorted_tasks(self, agent_type: str = "") -> list[DelegatedTask]:
        with self._lock:
            candidates = sorted(
                self._tasks.values(),
                key=lambda item: item.get("created_at", 0),
                reverse=True,
            )
            normalized = agent_type.strip().casefold()
            if normalized:
                candidates = [
                    task
                    for task in candidates
                    if str(task.get("agent_type", "")).casefold() == normalized
                ]
            return [self._snapshot_task(task) for task in candidates]

    def counts(self) -> DelegatedTaskCounts:
        with self._lock:
            types = [
                str(task.get("agent_type", "")).casefold()
                for task in self._tasks.values()
            ]
            return DelegatedTaskCounts(
                len(types), types.count("agi"), types.count("ops")
            )

    def update_status(self, task: DelegatedTask, status: str) -> bool:
        normalized = normalize_delegated_status(status).value
        terminal_statuses = {
            DelegatedTaskStatus.COMPLETED.value,
            DelegatedTaskStatus.FAILED.value,
            DelegatedTaskStatus.CANCELLED.value,
            DelegatedTaskStatus.TIMED_OUT.value,
        }
        with self._lock:
            live_task = self._live_task(task)
            if live_task is None:
                return False
            current = normalize_delegated_status(
                str(live_task.get("persisted_status") or "")
            ).value
            if current in terminal_statuses and normalized != current:
                self._sync_snapshot(task, live_task)
                return False
            if normalized == current:
                self._sync_snapshot(task, live_task)
                return False
            live_task["persisted_status"] = normalized
            self._persist_task(live_task)
            self._sync_snapshot(task, live_task)
            return True

    def mark_terminal(
        self,
        task: DelegatedTask,
        status: DelegatedTaskStatus,
        *,
        reason: str | None = None,
    ) -> bool:
        if status not in {
            DelegatedTaskStatus.COMPLETED,
            DelegatedTaskStatus.FAILED,
            DelegatedTaskStatus.CANCELLED,
            DelegatedTaskStatus.TIMED_OUT,
        }:
            raise ValueError(f"not a terminal delegation status: {status.value}")
        with self._lock:
            live_task = self._live_task(task)
            if live_task is None:
                return False
            changed = self.update_status(live_task, status.value)
            if reason and reason != live_task.get("terminal_reason"):
                live_task["terminal_reason"] = reason
                changed = True
                self._persist_task(live_task)
            self._sync_snapshot(task, live_task)
            return changed

    def _persist_task(self, task: DelegatedTask) -> None:
        if self._persist_callback is None:
            return
        try:
            self._persist_callback(
                task_id=str(task["task_id"]),
                agent_type=str(task.get("agent_type") or ""),
                thread_name=str(task.get("thread_name") or ""),
                prompt=str(task.get("prompt") or ""),
                mode=task.get("mode"),
                delegation_payload=task.get("delegation_payload", {}) or {},
                status=str(task.get("persisted_status") or "unknown"),
                created_at=float(
                    task.get("created_at", self._clock()) or self._clock()
                ),
                final_result=task.get("final_result"),
                final_error=task.get("final_error"),
                snapshot_path=task.get("snapshot_path"),
                fallback_reason=task.get("fallback_reason"),
            )
        except Exception:
            logger.exception("Could not persist delegated task %r", task.get("task_id"))


__all__ = [
    "DelegatedTask",
    "DelegatedTaskCounts",
    "DelegatedTaskRegistry",
    "DelegatedTaskStatus",
    "DelegatedWorker",
    "PersistDelegatedTask",
    "normalize_delegated_status",
]
