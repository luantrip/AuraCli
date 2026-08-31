from queue import Queue
from unittest.mock import MagicMock

from aura_cli.application.agents.events import AgiEvent, AgiTaskStartEvent
from aura_cli.tui.core.sync_manager import SyncManager


def _manager(queue: Queue) -> SyncManager:
    app = MagicMock()
    app.set_timer.return_value = MagicMock()
    app.query_one.side_effect = LookupError("widget not mounted")
    store = MagicMock()
    return SyncManager(app=app, status_queue=queue, store=store)


def _start(index: int) -> dict:
    return AgiTaskStartEvent.create(
        task_id=f"task-{index}",
        description=f"Task {index}",
        objective="test",
    ).to_dict()


def test_process_batch_applies_handler_and_stream_in_fifo_order() -> None:
    manager = _manager(Queue())
    manager._running = True
    observed: list[tuple[str, str]] = []

    def handler(event: AgiEvent) -> None:
        observed.append(("handler", event.task_id))

    events = [AgiEvent.from_dict(_start(1)), AgiEvent.from_dict(_start(2))]
    manager._pending_batch.events.extend(events)
    manager._event_handlers = {event.type: handler for event in events}
    manager._emit_to_event_stream = lambda event: observed.append(
        ("stream", event.task_id)
    )

    manager._process_batch()

    assert observed == [
        ("handler", "task-1"),
        ("stream", "task-1"),
        ("handler", "task-2"),
        ("stream", "task-2"),
    ]


def test_poll_discards_unknown_event_and_continues_to_valid_event() -> None:
    queue = Queue()
    queue.put({"type": "future_event", "task_id": "unknown", "data": {}})
    queue.put(_start(1))
    manager = _manager(queue)
    manager._running = True

    manager._poll_queue()

    assert manager._pending_batch.count == 1
    assert manager._pending_batch.events[0].task_id == "task-1"
    assert manager.get_metrics()["invalid_events"] == 1


def test_poll_enforces_max_batch_size_without_consuming_overflow() -> None:
    queue = Queue()
    for index in range(150):
        queue.put(_start(index))
    manager = _manager(queue)
    manager._running = True

    manager._poll_queue()
    manager._poll_queue()
    manager._poll_queue()

    assert manager._pending_batch.count == manager.MAX_BATCH_SIZE
    assert queue.qsize() == 50
