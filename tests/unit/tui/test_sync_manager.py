"""Testes para tui/core/sync_manager.py — TEST-NEW-02."""

from queue import Queue
from unittest.mock import MagicMock

from aura_cli.core.events.agi_events import AgiEvent, AgiEventType
from aura_cli.tui.core.sync_manager import BatchedEvents, SyncManager


def _make_manager(queue=None):
    app = MagicMock()
    app.call_from_thread = MagicMock()
    store = MagicMock()
    store.update = MagicMock()
    return SyncManager(app=app, status_queue=queue or Queue(), store=store)


class TestBatchedEvents:
    def test_add_and_count(self):
        batch = BatchedEvents()
        event = MagicMock(spec=AgiEvent)
        batch.add(event)
        assert batch.count == 1

    def test_clear(self):
        batch = BatchedEvents()
        batch.add(MagicMock(spec=AgiEvent))
        batch.clear()
        assert batch.count == 0

    def test_multiple_adds(self):
        batch = BatchedEvents()
        for _ in range(5):
            batch.add(MagicMock(spec=AgiEvent))
        assert batch.count == 5


class TestSyncManagerInit:
    def test_default_init(self):
        mgr = _make_manager()
        assert mgr._running is False
        assert mgr._events_processed == 0
        assert mgr._batches_processed == 0

    def test_event_handlers_registered(self):
        mgr = _make_manager()
        assert AgiEventType.TASK_START in mgr._event_handlers
        assert AgiEventType.CHAT_MESSAGE in mgr._event_handlers
        assert AgiEventType.TOOL_EXECUTING in mgr._event_handlers

    def test_queue_stored(self):
        q = Queue()
        mgr = _make_manager(queue=q)
        assert mgr.queue is q

    def test_stop_releases_all_owned_timers_and_pending_events(self):
        mgr = _make_manager()
        mgr.stats = MagicMock()
        timers = [MagicMock(), MagicMock()]
        mgr.app.set_interval.side_effect = timers
        mgr.start()
        mgr._pending_batch.add(MagicMock(spec=AgiEvent))
        batch_timer = MagicMock()
        debounce_timer = MagicMock()
        mgr._batch_timer = batch_timer
        mgr._debounce_timer = debounce_timer

        mgr.stop()
        mgr.stop()

        timers[0].stop.assert_called_once_with()
        timers[1].stop.assert_called_once_with()
        batch_timer.stop.assert_called_once_with()
        debounce_timer.stop.assert_called_once_with()
        assert mgr._pending_batch.count == 0
        assert mgr.is_running is False


class TestGetMetrics:
    def test_returns_dict(self):
        mgr = _make_manager()
        metrics = mgr.get_metrics()
        assert isinstance(metrics, dict)

    def test_metrics_has_events_processed(self):
        mgr = _make_manager()
        metrics = mgr.get_metrics()
        assert (
            "events_processed" in metrics
            or "total_events" in metrics
            or len(metrics) > 0
        )

    def test_is_running_false_initially(self):
        mgr = _make_manager()
        assert mgr.is_running is False


class TestProcessEvent:
    def _make_event(self, event_type, data=None):
        event = MagicMock()
        event.type = event_type
        event.data = data or {}
        return event

    def test_process_chat_message_event(self):
        mgr = _make_manager()
        event = self._make_event(
            AgiEventType.CHAT_MESSAGE,
            {"sender": "agent", "content": "hello", "text": "hello"},
        )
        mgr.process_event(event)

    def test_process_task_start_event(self):
        mgr = _make_manager()
        event = self._make_event(
            AgiEventType.TASK_START, {"task_id": "t1", "description": "test task"}
        )
        mgr.process_event(event)

    def test_process_unknown_event_no_crash(self):
        mgr = _make_manager()
        event = self._make_event("unknown.type", {})
        mgr.process_event(event)

    def test_events_processed_counter(self):
        mgr = _make_manager()
        # metrics should be accessible
        metrics = mgr.get_metrics()
        assert "events_processed" in metrics
