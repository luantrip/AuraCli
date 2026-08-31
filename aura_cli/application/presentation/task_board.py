"""Neutral projection of todo tasks into Kanban-style columns."""

from __future__ import annotations

from typing import Iterable, Protocol, TypeVar


class TodoTaskView(Protocol):
    text: str
    is_done: bool
    is_pending: bool


TaskT = TypeVar("TaskT", bound=TodoTaskView)
DEFAULT_PRIORITY_KEYWORDS = (
    "header",
    "hero",
    "ui",
    "api",
    "auth",
    "critical",
    "urgent",
)


def build_task_board_columns(
    tasks: Iterable[TaskT],
    *,
    current_task: TaskT | None = None,
    max_per_column: int = 5,
    priority_keywords: Iterable[str] = DEFAULT_PRIORITY_KEYWORDS,
) -> dict[str, list[TaskT]]:
    """Project todo tasks into todo, doing, done and priority columns."""
    items = list(tasks)
    done = [task for task in items if task.is_done]
    pending = [task for task in items if task.is_pending]
    doing = [current_task] if current_task is not None else []
    keywords = tuple(word.casefold() for word in priority_keywords)
    priority = [
        task
        for task in pending
        if any(word in task.text.casefold() for word in keywords)
    ][:max_per_column]
    todo = [task for task in pending if task not in doing][:max_per_column]
    return {
        "todo": todo,
        "doing": doing,
        "done": done[:max_per_column],
        "priority": priority,
    }


def task_progress(total: int, done: int) -> float:
    """Return a bounded task completion percentage."""
    if total <= 0:
        return 0.0
    return min(100.0, max(0.0, done / total * 100.0))
