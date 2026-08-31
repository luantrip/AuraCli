"""Neutral state models for delegated tasks and tool execution panels."""

from __future__ import annotations

from dataclasses import dataclass, field
import time
from typing import Any, Callable, Iterable


@dataclass
class DelegatedTaskState:
    description: str
    status: str = "pending"
    tool_count: int = 0
    duration: float = 0.0
    error: str = ""
    start_time: float = field(default_factory=time.time)

    def mark_running(self, tool_count: int = 0) -> None:
        self.status = "running"
        self.tool_count = tool_count

    def mark_done(self, tool_count: int, duration: float) -> None:
        self.status = "done"
        self.tool_count = tool_count
        self.duration = duration

    def mark_failed(self, error: str) -> None:
        self.status = "failed"
        self.error = error

    @property
    def terminal(self) -> bool:
        return self.status in {"done", "failed"}


@dataclass
class ToolExecutionState:
    name: str
    args: dict[str, Any]
    status: str = "pending"
    result: str | None = None
    duration: float | None = None
    error: str | None = None
    start_time: float = field(default_factory=time.time)

    def mark_running(self) -> None:
        self.status = "running"

    def mark_success(
        self,
        result: str,
        duration: float | None = None,
        clock: Callable[[], float] = time.time,
    ) -> None:
        self.status = "success"
        self.result = result
        self.duration = duration if duration is not None else clock() - self.start_time

    def mark_error(
        self,
        error: str,
        duration: float | None = None,
        clock: Callable[[], float] = time.time,
    ) -> None:
        self.status = "error"
        self.error = error
        self.duration = duration if duration is not None else clock() - self.start_time


def delegated_tasks_complete(tasks: Iterable[DelegatedTaskState]) -> bool:
    items = list(tasks)
    return bool(items) and all(item.terminal for item in items)


def summarize_tool_executions(
    executions: Iterable[ToolExecutionState],
) -> dict[str, float | int]:
    items = list(executions)
    return {
        "success": sum(item.status == "success" for item in items),
        "error": sum(item.status == "error" for item in items),
        "duration": sum(item.duration or 0.0 for item in items),
    }
