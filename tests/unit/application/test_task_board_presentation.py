"""Tests for neutral task-board projections."""

from dataclasses import dataclass

from aura_cli.application.presentation.task_board import (
    build_task_board_columns,
    task_progress,
)


@dataclass
class Task:
    text: str
    is_done: bool = False
    is_pending: bool = True


def test_projects_current_priority_todo_and_done_columns() -> None:
    current = Task("Implement API")
    regular = Task("Write docs")
    done = Task("Finished", is_done=True, is_pending=False)

    columns = build_task_board_columns([current, regular, done], current_task=current)

    assert columns["doing"] == [current]
    assert columns["todo"] == [regular]
    assert columns["priority"] == [current]
    assert columns["done"] == [done]


def test_task_progress_handles_empty_and_bounds() -> None:
    assert task_progress(0, 0) == 0.0
    assert task_progress(4, 1) == 25.0
    assert task_progress(1, 2) == 100.0
