"""Correlation contracts for the stateful agent event emitter."""

from queue import Queue

from aura_cli.application.agents.event_emitter import AgiEventAdapter


def test_tool_start_and_result_share_execution_identity_without_changing_task_owner() -> (
    None
):
    queue = Queue()
    adapter = AgiEventAdapter(queue, task_id="task-1")

    adapter.tool_executing("read_file", {"path": "a.py"})
    adapter.tool_result("read_file", True, "contents")

    started = queue.get_nowait()
    completed = queue.get_nowait()
    assert started["task_id"] == completed["task_id"] == "task-1"
    assert started["data"]["execution_id"] == completed["data"]["execution_id"]
    assert started["data"]["execution_id"].startswith("tool_")
