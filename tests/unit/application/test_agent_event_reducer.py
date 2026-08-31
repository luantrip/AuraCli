"""State-transition contracts for presentation-facing agent events."""

from aura_cli.application.agents.events import AgiEvent, AgiEventType
from aura_cli.application.presentation.agent_event_reducer import AgentEventStateReducer
from aura_cli.application.presentation.state_store import ReactiveStateStore


class EventStore(ReactiveStateStore):
    def __init__(self) -> None:
        super().__init__({"tasks": {}, "messages": []})

    def add_task(self, task_id: str, task_data: dict) -> None:
        self.set(f"tasks.{task_id}", task_data)

    def get_task(self, task_id: str) -> dict | None:
        return self.get(f"tasks.{task_id}")

    def add_message(self, message: dict) -> None:
        self.set("messages", [*self.get("messages", []), message])


def event(
    event_type: AgiEventType,
    task_id: str,
    data: dict,
    *,
    parent: str | None = None,
    timestamp: float = 10.0,
) -> AgiEvent:
    return AgiEvent(
        type=event_type,
        task_id=task_id,
        parent_task_id=parent,
        timestamp=timestamp,
        data=data,
    )


def test_task_lifecycle_does_not_mutate_previously_returned_task() -> None:
    store = EventStore()
    reducer = AgentEventStateReducer(store)
    reducer.reduce(event(AgiEventType.TASK_START, "root", {"description": "Build"}))
    original = store.get_task("root")

    reducer.reduce(
        event(AgiEventType.TASK_UPDATE, "root", {"status": "waiting", "message": "IO"})
    )

    assert original == {
        "id": "root",
        "name": "Build",
        "objective": "",
        "status": "running",
        "started_at": 10.0,
        "children": {},
        "parent_id": None,
    }
    assert store.get_task("root")["status"] == "waiting"


def test_subtask_and_tool_transitions_are_nested_under_parent() -> None:
    store = EventStore()
    reducer = AgentEventStateReducer(store)
    reducer.reduce(event(AgiEventType.TASK_START, "root", {}))
    reducer.reduce(
        event(
            AgiEventType.SUBTASK_START,
            "child",
            {"description": "Inspect"},
            parent="root",
        )
    )
    effect = reducer.reduce(
        event(
            AgiEventType.TOOL_EXECUTING,
            "tool",
            {"tool_name": "read_file", "tool_args": {"path": "a.py"}},
            parent="root",
        )
    )
    reducer.reduce(
        event(
            AgiEventType.TOOL_RESULT,
            "tool",
            {"tool_name": "read_file", "success": True, "result": "ok"},
            parent="root",
        )
    )

    children = store.get_task("root")["children"]
    assert children["child"]["status"] == "running"
    assert children["tool"]["status"] == "completed"
    assert effect.chat is not None
    assert '"path": "[oculto]"' in effect.chat.content
    assert "a.py" not in effect.chat.content


def test_chat_event_persists_message_and_requests_visual_effects() -> None:
    store = EventStore()
    reduction = AgentEventStateReducer(store).reduce(
        event(
            AgiEventType.CHAT_MESSAGE,
            "root",
            {"sender": "Aura", "content": "Pronto", "metadata": {"model": "local"}},
        )
    )

    assert store.get("messages")[0]["content"] == "Pronto"
    assert reduction.hide_thinking is True
    assert reduction.chat is not None and reduction.chat.sender == "Aura"


def test_tool_result_is_bounded_and_handles_non_numeric_elapsed_time() -> None:
    store = EventStore()
    reduction = AgentEventStateReducer(store, result_limit=5).reduce(
        event(
            AgiEventType.TOOL_RESULT,
            "tool",
            {
                "tool_name": "shell",
                "success": False,
                "result": "abcdefgh",
                "execution_time": "unknown",
                "error": "failed",
            },
        )
    )

    assert reduction.chat is not None
    assert "abcde\n... (truncated)" in reduction.chat.content
    assert "Error:** failed" in reduction.chat.content


def test_execution_id_correlates_tool_events_owned_by_a_task() -> None:
    store = EventStore()
    reducer = AgentEventStateReducer(store)
    reducer.reduce(event(AgiEventType.TASK_START, "root", {}))
    reducer.reduce(
        event(
            AgiEventType.TOOL_EXECUTING,
            "root",
            {"execution_id": "exec-1", "tool_name": "read_file", "tool_args": {}},
        )
    )
    reducer.reduce(
        event(
            AgiEventType.TOOL_RESULT,
            "root",
            {
                "execution_id": "exec-1",
                "tool_name": "read_file",
                "success": True,
                "result": "ok",
            },
        )
    )

    assert store.get_task("root")["children"]["exec-1"]["status"] == "completed"
