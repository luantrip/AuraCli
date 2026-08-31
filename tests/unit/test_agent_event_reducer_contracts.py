"""Contract tests for monotonic agent event reduction."""

from __future__ import annotations

from aura_cli.application.agents.events import AgiEvent, AgiEventType
from aura_cli.application.presentation.agent_event_reducer import AgentEventStateReducer


class _Store:
    def __init__(self) -> None:
        self.tasks: dict[str, dict] = {}
        self.messages: list[dict] = []

    def add_task(self, task_id: str, task_data: dict) -> None:
        self.tasks[task_id] = task_data

    def get_task(self, task_id: str) -> dict | None:
        return self.tasks.get(task_id)

    def add_message(self, message: dict) -> None:
        self.messages.append(message)


def test_terminal_task_cannot_be_reopened_by_late_update() -> None:
    store = _Store()
    reducer = AgentEventStateReducer(store)
    reducer.reduce(
        AgiEvent(
            type=AgiEventType.TASK_START,
            task_id="task-1",
            timestamp=10.0,
            data={"description": "test", "objective": "test"},
        )
    )
    reducer.reduce(
        AgiEvent(
            type=AgiEventType.TASK_CANCELLED,
            task_id="task-1",
            timestamp=20.0,
            data={"reason": "user"},
        )
    )
    reducer.reduce(
        AgiEvent(
            type=AgiEventType.TASK_UPDATE,
            task_id="task-1",
            timestamp=21.0,
            data={"status": "running", "message": "late event"},
        )
    )

    assert store.tasks["task-1"]["status"] == "cancelled"
    assert store.tasks["task-1"]["reason"] == "user"


def test_older_update_cannot_overwrite_newer_running_state() -> None:
    store = _Store()
    reducer = AgentEventStateReducer(store)
    reducer.reduce(
        AgiEvent(
            type=AgiEventType.TASK_START,
            task_id="task-2",
            timestamp=10.0,
            data={"description": "test", "objective": "test"},
        )
    )
    reducer.reduce(
        AgiEvent(
            type=AgiEventType.TASK_UPDATE,
            task_id="task-2",
            timestamp=20.0,
            data={"status": "waiting_external", "message": "new"},
        )
    )
    reducer.reduce(
        AgiEvent(
            type=AgiEventType.TASK_UPDATE,
            task_id="task-2",
            timestamp=19.0,
            data={"status": "running", "message": "old"},
        )
    )

    assert store.tasks["task-2"]["status"] == "waiting_external"
    assert store.tasks["task-2"]["message"] == "new"
