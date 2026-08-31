"""Terminal event idempotency contracts for QueueAgiAdapter."""

from queue import Queue

from aura_cli.application.agents.queue_event_emitter import QueueAgiAdapter


def test_complete_task_emits_only_once():
    events = Queue()
    adapter = QueueAgiAdapter(events, task_id="task-1")

    adapter.complete_task(True, result="done")
    adapter.complete_task(True, result="duplicate")

    assert events.qsize() == 1
    assert events.get_nowait()["data"]["result"] == "done"


def test_error_and_cancel_are_terminal_and_idempotent():
    error_events = Queue()
    error_adapter = QueueAgiAdapter(error_events, task_id="error-task")
    error_adapter.error_task("failed")
    error_adapter.error_task("duplicate")
    assert error_events.qsize() == 1

    cancel_events = Queue()
    cancel_adapter = QueueAgiAdapter(cancel_events, task_id="cancel-task")
    cancel_adapter.cancel_task("user")
    cancel_adapter.cancel_task("duplicate")
    assert cancel_events.qsize() == 1


def test_intermediate_updates_can_precede_one_terminal_event():
    events = Queue()
    adapter = QueueAgiAdapter(events, task_id="task-2")

    adapter.update_task("running", "started")
    adapter.emit_chat_message("agent", "working")
    adapter.complete_task(True, result="done")

    assert events.qsize() == 3
