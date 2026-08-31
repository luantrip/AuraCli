"""Contract tests for correlated agent tool events."""

from __future__ import annotations

from queue import Queue

from aura_cli.application.agents.event_emitter import AgiEventAdapter


def test_same_tool_name_keeps_concurrent_execution_ids() -> None:
    queue: Queue = Queue()
    adapter = AgiEventAdapter(queue, task_id="task-1")

    first_id = adapter.tool_executing("read_file", {"path": "one.py"})
    second_id = adapter.tool_executing("read_file", {"path": "two.py"})

    assert first_id is not None
    assert second_id is not None
    assert first_id != second_id

    adapter.tool_result("read_file", True, "one", execution_id=first_id)
    adapter.tool_result("read_file", True, "two", execution_id=second_id)

    events = [queue.get_nowait() for _ in range(4)]
    result_events = [event for event in events if event["type"] == "tool_result"]
    assert [event["data"]["execution_id"] for event in result_events] == [
        first_id,
        second_id,
    ]
    assert all(event["data"]["execution_time"] is not None for event in result_events)
    assert adapter.active_tools == {}


def test_ops_queue_adapter_tracks_tool_execution_ids() -> None:
    from aura_cli.application.agents.queue_event_emitter import QueueAgiAdapter

    queue: Queue = Queue()
    adapter = QueueAgiAdapter(queue, task_id="ops-1")
    execution_id = adapter.tool_executing("run_shell_command", {"command": "true"})
    adapter.tool_result(
        "run_shell_command",
        True,
        "ok",
        execution_id=execution_id,
    )

    events = [queue.get_nowait() for _ in range(2)]
    assert events[0]["data"]["execution_id"] == execution_id
    assert events[1]["data"]["execution_id"] == execution_id
    assert events[1]["data"]["execution_time"] is not None
    assert adapter.active_tools == {}
