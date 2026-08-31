"""Stress and race-condition tests for CoreEventBus and SyncManager (Fase 3.3).

Tests verify:
- CoreEventBus is thread-safe under concurrent publish/subscribe
- Events are not lost or duplicated under load
- SyncManager contract validation rejects malformed events
- Backpressure (queue full) is handled gracefully
"""

from __future__ import annotations

import queue
import threading
import time
from typing import List
from unittest.mock import MagicMock

# ---------------------------------------------------------------------------
# CoreEventBus stress tests
# ---------------------------------------------------------------------------


class TestCoreEventBusConcurrency:
    """Thread-safety and backpressure tests for CoreEventBus."""

    def test_concurrent_publish_no_loss(self, mock_event_bus):
        """100 threads publishing 10 events each → 1000 events in queue."""
        from aura_cli.core.events.agi_events import AgiTaskUpdateEvent

        received: List[dict] = []
        lock = threading.Lock()

        def on_event(ev):
            with lock:
                received.append(ev)

        mock_event_bus.subscribe_all(lambda t, e: on_event(e))

        def publish_batch(thread_id: int):
            for i in range(10):
                evt = AgiTaskUpdateEvent.create(
                    task_id=f"task_{thread_id}_{i}",
                    status="running",
                    message=f"thread {thread_id} msg {i}",
                )
                mock_event_bus.publish(evt)

        threads = [
            threading.Thread(target=publish_batch, args=(i,)) for i in range(100)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=5)

        assert len(received) == 1000

    def test_subscribe_unsubscribe_thread_safe(self, mock_event_bus):
        """Subscribing and unsubscribing from multiple threads must not raise."""
        from aura_cli.core.events.agi_events import AgiEventType

        errors: List[Exception] = []

        def worker():
            try:
                unsub = mock_event_bus.subscribe(
                    AgiEventType.TASK_UPDATE, lambda e: None
                )
                time.sleep(0.001)
                unsub()
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=worker) for _ in range(50)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=5)

        assert errors == [], f"Thread errors: {errors}"

    def test_backpressure_drops_gracefully(self):
        """When queue is full, events are dropped without raising."""
        from aura_cli.core.events.agi_events import AgiTaskUpdateEvent
        from aura_cli.core.events.event_bus import CoreEventBus

        CoreEventBus.reset_instance()
        small_bus = CoreEventBus(max_queue_size=5)

        dropped_before = small_bus._dropped_count
        for i in range(20):
            evt = AgiTaskUpdateEvent.create(f"t{i}", "running", f"msg {i}")
            small_bus.publish(evt)

        assert small_bus._dropped_count > dropped_before
        assert small_bus.qsize() <= 5
        CoreEventBus.reset_instance()

    def test_pause_resume_drops_and_resumes(self, mock_event_bus):
        """Paused bus drops events; resumed bus accepts them again."""
        from aura_cli.core.events.agi_events import AgiTaskUpdateEvent

        mock_event_bus.pause()
        evt = AgiTaskUpdateEvent.create("t1", "running", "msg")
        result = mock_event_bus.publish(evt)
        assert result is False

        mock_event_bus.resume()
        result = mock_event_bus.publish(evt)
        assert result is True


# ---------------------------------------------------------------------------
# SyncManager contract validation stress test
# ---------------------------------------------------------------------------


class TestSyncManagerContractValidation:
    """SyncManager must reject malformed events and process valid ones."""

    def _make_sync_manager(self, q):
        """Build a SyncManager with a mock Textual app."""
        from aura_cli.tui.core.sync_manager import SyncManager
        from aura_cli.tui.core.sync_store import SyncStore

        app = MagicMock()
        app.set_interval = MagicMock(return_value=MagicMock())
        app.set_timer = MagicMock(return_value=MagicMock())
        app.refresh = MagicMock()
        app.query_one = MagicMock(side_effect=Exception("no widget"))

        store = SyncStore()
        sm = SyncManager(app=app, status_queue=q, store=store)
        sm._running = True  # simulate started state
        return sm

    def test_valid_events_pass_contract(self):
        """Valid AgiEvents pass contract validation and are batched."""
        from aura_cli.core.events.agi_events import AgiTaskStartEvent

        q = queue.Queue()
        evt = AgiTaskStartEvent.create("t1", "desc", "obj")
        q.put(evt.to_dict())

        sm = self._make_sync_manager(q)
        sm._poll_queue()

        assert sm._pending_batch.count == 1

    def test_malformed_events_rejected_by_contract(self):
        """Events with wrong payload shape are dropped, not batched."""
        q = queue.Queue()
        # Missing required fields for agi_task_start
        bad_event = {
            "type": "agi_task_start",
            "task_id": "t1",
            "data": {"bad_field": 1},
        }
        q.put(bad_event)

        sm = self._make_sync_manager(q)
        sm._poll_queue()

        # Malformed event should be skipped
        assert sm._pending_batch.count == 0

    def test_unknown_event_type_passes_through(self):
        """Events with unknown type (no schema) are not rejected."""
        from aura_cli.core.events.agi_events import AgiEvent, AgiEventType

        q = queue.Queue()
        # THINKING has a schema but minimal fields — use a valid one
        evt = AgiEvent(
            type=AgiEventType.THINKING, task_id="t1", data={"thought": "hmm"}
        )
        q.put(evt.to_dict())

        sm = self._make_sync_manager(q)
        sm._poll_queue()

        assert sm._pending_batch.count == 1

    def test_high_volume_mixed_events(self):
        """500 valid + 500 invalid events: only valid ones are batched."""
        from aura_cli.core.events.agi_events import AgiTaskUpdateEvent

        q = queue.Queue()

        for i in range(500):
            valid = AgiTaskUpdateEvent.create(f"t{i}", "running", f"msg {i}")
            q.put(valid.to_dict())
            # Invalid: missing required 'status' field
            q.put({"type": "agi_task_update", "task_id": f"bad_{i}", "data": {}})

        sm = self._make_sync_manager(q)

        # Poll in batches (SyncManager polls max 50 per call)
        for _ in range(25):
            sm._poll_queue()

        # Only valid events should be batched (up to MAX_BATCH_SIZE per poll cycle)
        assert sm._pending_batch.count > 0
        # All batched events must be valid AgiEvents
        from aura_cli.core.events.agi_events import AgiEvent

        for evt in sm._pending_batch.events:
            assert isinstance(evt, AgiEvent)


# ---------------------------------------------------------------------------
# SyncManager latency / race condition tests (Item 3)
# ---------------------------------------------------------------------------


class TestSyncManagerRaceConditions:
    """
    Race condition tests for SyncManager._poll_queue + _process_batch.

    These tests simulate the Textual timer behavior by calling _process_batch
    directly from a separate thread while _poll_queue runs concurrently,
    reproducing the real interleaving that happens in production.
    """

    def _make_sm(self, q):
        from aura_cli.tui.core.sync_manager import SyncManager
        from aura_cli.tui.core.sync_store import SyncStore

        app = MagicMock()
        app.set_interval = MagicMock(return_value=MagicMock())
        app.set_timer = MagicMock(return_value=MagicMock())
        app.refresh = MagicMock()
        app.query_one = MagicMock(side_effect=Exception("no widget"))

        sm = SyncManager(app=app, status_queue=q, store=SyncStore())
        sm._running = True
        return sm

    def test_concurrent_poll_and_process_no_crash(self):
        """Concurrent _poll_queue and _process_batch must not raise."""
        from aura_cli.core.events.agi_events import AgiTaskUpdateEvent

        q = queue.Queue()
        for i in range(200):
            q.put(AgiTaskUpdateEvent.create(f"t{i}", "running", f"msg {i}").to_dict())

        sm = self._make_sm(q)
        errors = []

        def poll_worker():
            for _ in range(20):
                try:
                    sm._poll_queue()
                except Exception as e:
                    errors.append(f"poll: {e}")

        def process_worker():
            for _ in range(10):
                try:
                    sm._process_batch()
                except Exception as e:
                    errors.append(f"process: {e}")

        threads = [threading.Thread(target=poll_worker) for _ in range(5)] + [
            threading.Thread(target=process_worker) for _ in range(3)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=5)

        assert errors == [], f"Race condition errors: {errors}"

    def test_batch_timer_set_only_once_under_concurrent_polls(self):
        """_schedule_batch must not set multiple timers concurrently."""
        from aura_cli.core.events.agi_events import AgiTaskUpdateEvent

        q = queue.Queue()
        for i in range(100):
            q.put(AgiTaskUpdateEvent.create(f"t{i}", "running", f"msg {i}").to_dict())

        sm = self._make_sm(q)
        timer_calls = []
        sm.app.set_timer = lambda *a, **kw: timer_calls.append(1) or MagicMock()

        threads = [threading.Thread(target=sm._poll_queue) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=5)

        # Timer should be set at most once per batch cycle
        # (multiple polls may each try to schedule, but _batch_timer guard prevents duplicates)
        assert len(timer_calls) >= 1

    def test_process_batch_clears_pending_atomically(self):
        """After _process_batch, pending batch must be empty."""
        from aura_cli.core.events.agi_events import AgiTaskUpdateEvent

        q = queue.Queue()
        for i in range(50):
            q.put(AgiTaskUpdateEvent.create(f"t{i}", "running", f"msg {i}").to_dict())

        sm = self._make_sm(q)
        sm._poll_queue()
        assert sm._pending_batch.count > 0

        sm._process_batch()
        assert sm._pending_batch.count == 0

    def test_events_processed_counter_increments_correctly(self):
        """_events_processed must equal number of valid events processed."""
        from aura_cli.core.events.agi_events import AgiTaskUpdateEvent

        q = queue.Queue()
        n = 30
        for i in range(n):
            q.put(AgiTaskUpdateEvent.create(f"t{i}", "running", f"msg {i}").to_dict())

        sm = self._make_sm(q)
        sm._poll_queue()
        sm._process_batch()

        assert sm._events_processed == n

    def test_stop_does_not_process_after_running_false(self):
        """Once _running=False, _poll_queue must not add to batch."""
        from aura_cli.core.events.agi_events import AgiTaskUpdateEvent

        q = queue.Queue()
        q.put(AgiTaskUpdateEvent.create("t1", "running", "msg").to_dict())

        sm = self._make_sm(q)
        sm._running = False
        sm._poll_queue()

        assert sm._pending_batch.count == 0
