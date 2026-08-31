"""Tests for neutral live-dashboard decisions."""

from dataclasses import dataclass, field
from enum import Enum

from aura_cli.application.presentation import (
    DashboardState,
    TaskState,
    build_dashboard_summary,
    classify_dashboard_message,
)


class State(Enum):
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class Task:
    state: State


@dataclass
class Dashboard:
    mode: str = "AGI"
    tasks: list[Task] = field(default_factory=list)
    tools_used: list[str] = field(default_factory=list)
    memory_entries: int = 2
    constitution_active: bool = True
    status: str = "done"


def test_classifies_phase_completion_and_tool() -> None:
    decision = classify_dashboard_message("Concluído após read_file")

    assert decision.phase == "completed"
    assert decision.completed is True
    assert decision.tool_name == "Read File"


def test_builds_dashboard_summary_without_rich_types() -> None:
    state = Dashboard(
        tasks=[Task(State.COMPLETED), Task(State.FAILED)], tools_used=["Read File"]
    )

    summary = build_dashboard_summary(state, 4.5)

    assert summary["completed_tasks"] == 1
    assert summary["failed_tasks"] == 1
    assert summary["elapsed_seconds"] == 4.5


def test_dashboard_state_owns_bounded_mutations() -> None:
    state = DashboardState()
    state.set_progress(2)
    state.add_task("one", "First")
    state.update_task("one", state=TaskState.COMPLETED, timestamp=5, result="ok")
    state.add_tool("Read File")
    for index in range(12):
        state.add_message(str(index), "info", float(index))

    assert state.progress == 1.0
    assert state.tasks[0].completed_at == 5
    assert state.tasks[0].result == "ok"
    assert state.tools_used == ["Read File"]
    assert len(state.messages) == 10
