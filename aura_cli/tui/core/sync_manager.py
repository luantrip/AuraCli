"""Reactive Sync Manager for Aura TUI.

Polls status_queue at 10 ms, batches events at 50 ms, debounces UI refresh
at 150 ms to prevent flicker. Max 100 events/batch, max 50 events/poll.
Integrates with SyncStore; exposes performance metrics via get_metrics().
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
import logging
from queue import Empty, Queue
import threading
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional

from aura_cli.application.agents.events import AgiEvent, AgiEventType
from aura_cli.application.presentation.agent_event_reducer import (
    AgentEventReduction,
    AgentEventStateReducer,
)
from aura_cli.core.events.contracts import is_valid_event
from aura_cli.tui.core.sync_store import SyncStore, get_store

if TYPE_CHECKING:
    from textual.app import App

logger = logging.getLogger(__name__)

TASK_TREE_EVENT_TYPES = frozenset(
    {
        AgiEventType.TASK_START,
        AgiEventType.TASK_UPDATE,
        AgiEventType.TASK_COMPLETE,
        AgiEventType.SUBTASK_START,
        AgiEventType.SUBTASK_COMPLETE,
        AgiEventType.PLANNING,
        AgiEventType.THINKING,
        AgiEventType.TOOL_EXECUTING,
        AgiEventType.TOOL_RESULT,
        AgiEventType.TASK_ERROR,
        AgiEventType.TASK_CANCELLED,
        AgiEventType.TASK_INTERRUPTED,
        AgiEventType.APPROVAL_REQUESTED,
        AgiEventType.APPROVAL_RESOLVED,
        AgiEventType.EXTERNAL_WAIT_STARTED,
        AgiEventType.EXTERNAL_WAIT_ENDED,
        AgiEventType.CHECKPOINT_CREATED,
    }
)


def is_valid_queue_event(event_type: Any, data: Any) -> bool:
    """Validate a queue payload through the bridge-approved contract port."""
    return bool(is_valid_event(event_type, data))


@dataclass
class BatchedEvents:
    """Container for batched events with timestamp tracking.

    Attributes:
        events: List of batched AgiEvents
        timestamp: Batch creation timestamp
    """

    events: List[AgiEvent] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)
    max_size: Optional[int] = None

    def add(self, event: AgiEvent) -> bool:
        """Add event to batch.

        Args:
            event: AgiEvent to add
        """
        if self.max_size is not None and len(self.events) >= self.max_size:
            return False
        self.events.append(event)
        return True

    def clear(self) -> None:
        """Clear batch and reset timestamp."""
        self.events.clear()
        self.timestamp = datetime.now()

    @property
    def count(self) -> int:
        """Get number of events in batch.

        Returns:
            Event count
        """
        return len(self.events)


class SyncManager:
    """Reactive synchronization manager between core logic and TUI.

    Batches status_queue events (50 ms intervals, max 100 events/batch),
    applies them to SyncStore, and triggers a single TUI refresh per batch.
    Polls every 10 ms. Metrics available via get_metrics().
    """

    BATCH_INTERVAL = 0.05  # 50ms - batch events
    POLL_INTERVAL = 0.01  # 10ms - poll queue
    MAX_BATCH_SIZE = 100
    DEBOUNCE_INTERVAL = 0.15  # 150ms - debounce rapid updates

    def __init__(
        self,
        app: App,
        status_queue: Optional[Queue] = None,
        store: Optional[SyncStore] = None,
        stats: Optional[Any] = None,
    ):
        """Initialize sync manager.

        Args:
            app: Textual App instance
            status_queue: Queue for receiving AgiEvents from core
            store: SyncStore instance (uses global if not provided)
            stats: Stats object for metrics
        """
        self.app = app
        self.queue = status_queue
        self.store = store or get_store()
        self.stats = stats

        self._running = False
        self._pending_batch = BatchedEvents(max_size=self.MAX_BATCH_SIZE)
        self._batch_timer = None
        self._poll_task: Any = None
        self._stats_timer: Any = None
        self._debounce_timer = None  # Anti-flicker debounce timer
        self._last_refresh_time: Optional[datetime] = None  # Track last UI refresh
        self._timer_lock = threading.Lock()
        self._batch_lock = threading.Lock()

        self._events_processed = 0
        self._invalid_events = 0
        self._batches_processed = 0
        self._last_batch_time: Optional[datetime] = None
        self._state_reducer = AgentEventStateReducer(self.store)

        self._event_handlers: Dict[AgiEventType, Callable] = dict.fromkeys(
            (
                AgiEventType.TASK_START,
                AgiEventType.TASK_UPDATE,
                AgiEventType.TASK_COMPLETE,
                AgiEventType.SUBTASK_START,
                AgiEventType.SUBTASK_COMPLETE,
                AgiEventType.TOOL_EXECUTING,
                AgiEventType.TOOL_RESULT,
                AgiEventType.CHAT_MESSAGE,
                AgiEventType.PLANNING,
                AgiEventType.THINKING,
                AgiEventType.TASK_ERROR,
                AgiEventType.TASK_CANCELLED,
                AgiEventType.TASK_INTERRUPTED,
                AgiEventType.APPROVAL_REQUESTED,
                AgiEventType.APPROVAL_RESOLVED,
                AgiEventType.EXTERNAL_WAIT_STARTED,
                AgiEventType.EXTERNAL_WAIT_ENDED,
                AgiEventType.CHECKPOINT_CREATED,
            ),
            self._handle_agent_event,
        )

    def start(self) -> None:
        """Start sync manager with polling and stats updates."""
        if self._running:
            return

        self._running = True

        if self.queue:
            self._poll_task = self.app.set_interval(
                self.POLL_INTERVAL, self._poll_queue
            )

        if self.stats:
            self._stats_timer = self.app.set_interval(1.0, self._update_stats)

        logger.info("SyncManager started")

    def stop(self) -> None:
        """Stop sync manager and cleanup timers."""
        self._running = False

        if self._poll_task:
            self._poll_task.stop()
            self._poll_task = None

        if self._stats_timer:
            self._stats_timer.stop()
            self._stats_timer = None

        with self._timer_lock:
            if self._batch_timer:
                self._batch_timer.stop()
                self._batch_timer = None

            if self._debounce_timer:
                self._debounce_timer.stop()
                self._debounce_timer = None

        self._pending_batch.clear()

        logger.info("SyncManager stopped")

    def _poll_queue(self) -> None:
        """Poll status queue for new events."""
        if not self.queue or not self._running:
            return

        events_received = 0
        max_per_poll = 50

        with self._batch_lock:
            while (
                events_received < max_per_poll
                and self._pending_batch.count < self.MAX_BATCH_SIZE
            ):
                try:
                    event_dict = self.queue.get_nowait()
                    events_received += 1
                    event_type = event_dict.get("type", "")
                    event_data = event_dict.get("data", {})
                    if not event_type or not is_valid_queue_event(
                        event_type, event_data
                    ):
                        self._invalid_events += 1
                        logger.warning(
                            "SyncManager: event '%s' failed contract validation, skipping",
                            event_type or "<missing type>",
                        )
                        continue
                    self._pending_batch.add(AgiEvent.from_dict(event_dict))
                except Empty:
                    break
                except Exception as error:
                    self._invalid_events += 1
                    logger.error("Error processing event from queue: %s", error)
                    continue

        if self._pending_batch.count > 0 and self._batch_timer is None:
            self._schedule_batch()

    def _schedule_batch(self) -> None:
        """Schedule batch processing."""
        if not self._running:
            return
        with self._timer_lock:
            if self._batch_timer is None:
                self._batch_timer = self.app.set_timer(  # type: ignore[assignment]
                    self.BATCH_INTERVAL, self._process_batch
                )

    def _schedule_debounced_refresh(self) -> None:
        """Schedule debounced UI refresh to prevent flicker."""
        with self._timer_lock:
            if self._debounce_timer:
                self._debounce_timer.stop()
                self._debounce_timer = None

            now = datetime.now()
            if self._last_refresh_time:
                elapsed = (now - self._last_refresh_time).total_seconds()
                if elapsed < self.DEBOUNCE_INTERVAL:
                    self._debounce_timer = self.app.set_timer(  # type: ignore[assignment]
                        self.DEBOUNCE_INTERVAL - elapsed, self._do_refresh
                    )
                    return

            self._do_refresh()

    def _do_refresh(self) -> None:
        """Execute UI refresh and update timestamp."""
        self._debounce_timer = None
        self._last_refresh_time = datetime.now()
        self.app.refresh()

    def _safe_call_from_thread(self, callback, *args, **kwargs) -> bool:
        """Safely call function from thread with error handling."""
        if not self._running or not self.app:
            return False
        try:
            self.app.call_from_thread(callback, *args, **kwargs)
            return True
        except (RuntimeError, AttributeError):
            return False
        except Exception as e:
            logger.debug(f"call_from_thread failed: {e}")
            return False

    def _process_batch(self) -> None:
        """Process all pending events in batch."""
        self._batch_timer = None

        if not self._running:
            return

        if self._pending_batch.count == 0:
            return

        with self._batch_lock:
            events = self._pending_batch.events.copy()
            self._pending_batch.clear()

        with self.store.batch_update():
            for event in events:
                handler = self._event_handlers.get(event.type)
                if handler:
                    try:
                        handler(event)
                    except Exception as error:
                        logger.error("Error handling %s: %s", event.type, error)
                self._emit_to_event_stream(event)

        self._events_processed += len(events)
        self._batches_processed += 1
        self._last_batch_time = datetime.now()

        # Debounced refresh to prevent flicker
        self._schedule_debounced_refresh()

    def _emit_to_event_stream(self, event: AgiEvent) -> None:
        """Emit event to event stream panel.

        Args:
            event: AgiEvent to emit
        """
        try:
            event_stream = self.app.query_one("#event_stream_panel")
            event_stream.write_event(event.to_dict())  # type: ignore[attr-defined]
        except Exception as error:
            logger.debug("Event stream unavailable during sync: %s", error)

    def _handle_agent_event(self, event: AgiEvent) -> None:
        """Apply state reduction and deliver the single task-tree projection."""
        if event.type in TASK_TREE_EVENT_TYPES:
            update_task_tree = getattr(self.app, "update_task_tree", None)
            if callable(update_task_tree):
                self._safe_call_from_thread(update_task_tree, event)
        self._deliver_reduction(self._state_reducer.reduce(event))

    def _deliver_reduction(self, reduction: AgentEventReduction) -> None:
        if reduction.hide_thinking or reduction.show_thinking_for:
            try:
                chat: Any = self.app.query_one("AuraChatLog")
                if reduction.hide_thinking:
                    self._safe_call_from_thread(chat.hide_thinking)
                if reduction.show_thinking_for:
                    self._safe_call_from_thread(
                        chat.show_thinking, reduction.show_thinking_for
                    )
            except Exception as error:
                logger.debug("Could not update thinking indicator: %s", error)

        if reduction.chat:
            try:
                self._safe_call_from_thread(
                    self.app.post_message_to_chat,  # type: ignore[attr-defined]
                    reduction.chat.sender,
                    reduction.chat.content,
                    task_id=reduction.chat.task_id,
                )
            except Exception as error:
                logger.debug("Could not deliver reduced chat effect: %s", error)

    def _update_stats(self) -> None:
        """Update stats in store and sidebar."""
        if not self.stats:
            return

        stats_data = {
            "status": self.stats.current_status,
            "files_read": len(getattr(self.stats, "_files_read_list", [])),
            "files_edited": len(getattr(self.stats, "_files_edited_list", [])),
            "files_created": len(getattr(self.stats, "_files_created_list", [])),
            "llm_calls": getattr(self.stats, "llm_calls", 0),
            "tool_calls": getattr(self.stats, "tool_calls", 0),
            "total_tokens": getattr(self.stats, "total_tokens", 0),
            "total_execution_time": f"{getattr(self.stats, 'total_execution_time', 0):.2f}s",
            "sync_events_processed": self._events_processed,
            "sync_batches_processed": self._batches_processed,
        }

        self.store.update_stats(stats_data)

        try:
            sidebar = self.app.query_one("AuraStatusSidebar")
            sidebar.update_stats(stats_data)  # type: ignore[attr-defined]
        except Exception as error:
            logger.debug("Sidebar unavailable during stats update: %s", error)

    def process_event(self, event: AgiEvent) -> None:
        """Process single event immediately (bypass queue).

        Args:
            event: AgiEvent to process
        """
        handler = self._event_handlers.get(event.type)
        if handler:
            handler(event)
            self._emit_to_event_stream(event)
            self.app.refresh()

    def get_metrics(self) -> Dict[str, Any]:
        """Get sync manager metrics.

        Returns:
            Dictionary containing performance metrics
        """
        return {
            "events_processed": self._events_processed,
            "batches_processed": self._batches_processed,
            "last_batch_time": (
                self._last_batch_time.isoformat() if self._last_batch_time else None
            ),
            "pending_events": self._pending_batch.count,
            "invalid_events": self._invalid_events,
            "running": self._running,
        }

    @property
    def is_running(self) -> bool:
        """Check if sync manager is running.

        Returns:
            True if running
        """
        return self._running
