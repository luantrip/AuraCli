"""Thread-safe event transport for workers, handlers and interface adapters.

``CoreEventBus`` supports filtered publish/subscribe, bounded queue consumption,
event history and backpressure. The queue is a first-class transport consumed by
worker and UI adapters, while Application owns the toolkit-neutral event schemas.

Usage:
    >>> from aura_cli.core.events import get_event_bus
    >>> bus = get_event_bus()
    >>> bus.publish(AgiTaskStartEvent.create(...))
    >>> unsubscribe = bus.subscribe(AgiEventType.TASK_COMPLETE, on_complete)
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
import logging
import queue
import threading
from typing import Any, Callable, Dict, List, Optional

from aura_cli.core.events.agi_events import AgiEvent, AgiEventType

logger = logging.getLogger(__name__)


@dataclass
class EventRecord:
    """Record of a published event for debugging."""

    event_type: str
    event_data: Dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.now)
    delivered_to: int = 0


class CoreEventBus:
    """
    Centralized event bus for all Aura CLI component communication.

    Provides thread-safe event publishing, subscription and queue consumption.

    Features:
        - Thread-safe publish/subscribe pattern
        - Event type filtering
        - Queue access for polling adapters
        - Bounded queue with backpressure
        - Event history for debugging

    Attributes:
        max_queue_size: Maximum events in queue before backpressure
        enable_history: Whether to record event history
        max_history: Maximum events to keep in history
    """

    _instance: Optional[CoreEventBus] = None
    _lock = threading.RLock()

    from aura_cli.core.constants import (
        MAX_EVENT_HISTORY,
        MAX_EVENT_QUEUE_SIZE,
    )

    MAX_QUEUE_SIZE = MAX_EVENT_QUEUE_SIZE
    MAX_HISTORY = MAX_EVENT_HISTORY

    def __init__(
        self,
        max_queue_size: int = MAX_QUEUE_SIZE,
        enable_history: bool = False,
    ):
        """
        Initialize the event bus.

        Args:
            max_queue_size: Maximum queue size before blocking/dropping
            enable_history: Enable event history recording
        """
        self._queue: queue.Queue = queue.Queue(maxsize=max_queue_size)
        self._subscribers: Dict[str, List[Callable[[Dict[str, Any]], None]]] = (
            defaultdict(list)
        )
        self._wildcard_subscribers: List[Callable[[str, Dict[str, Any]], None]] = []
        self._subscriber_lock = threading.RLock()

        self._history: List[EventRecord] = []
        self._enable_history = enable_history
        self._history_lock = threading.Lock()

        self._paused = False
        self._dropped_count = 0

        logger.debug(
            f"CoreEventBus initialized (max_size={max_queue_size}, history={enable_history})"
        )

    @classmethod
    def get_instance(cls) -> CoreEventBus:
        """
        Get the singleton instance.

        Returns:
            CoreEventBus singleton
        """
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        """Reset the singleton instance (for testing)."""
        with cls._lock:
            if cls._instance is not None:
                cls._instance.clear()
            cls._instance = None

    def publish(self, event: AgiEvent) -> bool:
        """
        Publish an event to the bus.

        The event is added to the queue and delivered to all matching
        subscribers synchronously.

        Args:
            event: AgiEvent to publish

        Returns:
            True if event was queued successfully
        """
        if self._paused:
            logger.debug(f"Event dropped (paused): {event.type}")
            return False

        event_dict = event.to_dict()
        event_type = event_dict.get("type", "unknown")

        queued = self._enqueue(event_dict)

        delivered = self._notify_subscribers(event_type, event_dict)

        if self._enable_history:
            self._record_event(event_type, event_dict, delivered)

        return queued

    def publish_dict(self, event_dict: Dict[str, Any]) -> bool:
        """
        Publish an event dictionary directly.

        For compatibility with code that creates events as dictionaries.

        Args:
            event_dict: Event dictionary with 'type' field

        Returns:
            True if event was queued successfully
        """
        if self._paused:
            return False

        event_type = event_dict.get("type", "unknown")

        queued = self._enqueue(event_dict)
        delivered = self._notify_subscribers(event_type, event_dict)

        if self._enable_history:
            self._record_event(event_type, event_dict, delivered)

        return queued

    def _enqueue(self, event_dict: Dict[str, Any]) -> bool:
        """Add event to queue with backpressure handling."""
        try:
            self._queue.put_nowait(event_dict)
            return True
        except queue.Full:
            self._dropped_count += 1
            logger.warning(
                f"Event queue full, dropping event (total dropped: {self._dropped_count})"
            )
            return False

    def _notify_subscribers(self, event_type: str, event_dict: Dict[str, Any]) -> int:
        """Notify all matching subscribers."""
        delivered = 0

        with self._subscriber_lock:
            for callback in self._subscribers.get(event_type, []):
                try:
                    callback(event_dict)
                    delivered += 1
                except Exception as e:
                    logger.error(f"Subscriber error for '{event_type}': {e}")

            for wildcard_callback in self._wildcard_subscribers:
                try:
                    wildcard_callback(event_type, event_dict)
                    delivered += 1
                except Exception as e:
                    logger.error(f"Wildcard subscriber error: {e}")

        return delivered

    def subscribe(
        self, event_type: AgiEventType, callback: Callable[[Dict[str, Any]], None]
    ) -> Callable[[], None]:
        """
        Subscribe to a specific event type.

        Args:
            event_type: Event type to subscribe to
            callback: Function to call when event is published

        Returns:
            Unsubscribe function
        """
        type_value = (
            event_type.value
            if isinstance(event_type, AgiEventType)
            else str(event_type)
        )

        with self._subscriber_lock:
            self._subscribers[type_value].append(callback)

        def unsubscribe():
            """Remove a subscriber from the event bus."""
            with self._subscriber_lock:
                if callback in self._subscribers[type_value]:
                    self._subscribers[type_value].remove(callback)

        return unsubscribe

    def subscribe_all(
        self, callback: Callable[[str, Dict[str, Any]], None]
    ) -> Callable[[], None]:
        """
        Subscribe to all events (useful for logging/debugging).

        Args:
            callback: Function receiving (event_type, event_dict)

        Returns:
            Unsubscribe function
        """
        with self._subscriber_lock:
            self._wildcard_subscribers.append(callback)

        def unsubscribe():
            """Remove a subscriber from the event bus."""
            with self._subscriber_lock:
                if callback in self._wildcard_subscribers:
                    self._wildcard_subscribers.remove(callback)

        return unsubscribe

    def subscribe_multiple(
        self,
        event_types: List[AgiEventType],
        callback: Callable[[Dict[str, Any]], None],
    ) -> Callable[[], None]:
        """
        Subscribe to multiple event types.

        Args:
            event_types: List of event types to subscribe to
            callback: Function to call for any matching event

        Returns:
            Unsubscribe function that removes all subscriptions
        """
        unsubscribes = []
        for event_type in event_types:
            unsub = self.subscribe(event_type, callback)
            unsubscribes.append(unsub)

        def unsubscribe_all():
            """Remove all subscribers from the event bus."""
            for unsub in unsubscribes:
                unsub()

        return unsubscribe_all

    def get_queue(self) -> queue.Queue:
        """Return the bounded queue consumed by polling adapters.

        Returns:
            The internal queue instance
        """
        return self._queue

    def get_nowait(self) -> Optional[Dict[str, Any]]:
        """
        Get next event without blocking.

        Returns:
            Event dictionary or None if queue is empty
        """
        try:
            return self._queue.get_nowait()
        except queue.Empty:
            return None

    def get(self, timeout: float = 1.0) -> Optional[Dict[str, Any]]:
        """
        Get next event with timeout.

        Args:
            timeout: Maximum seconds to wait

        Returns:
            Event dictionary or None if timeout
        """
        try:
            return self._queue.get(timeout=timeout)
        except queue.Empty:
            return None

    def qsize(self) -> int:
        """Get approximate queue size."""
        return self._queue.qsize()

    def empty(self) -> bool:
        """Check if queue is empty."""
        return self._queue.empty()

    def pause(self) -> None:
        """Pause event publishing (events will be dropped)."""
        self._paused = True
        logger.debug("Event bus paused")

    def resume(self) -> None:
        """Resume event publishing."""
        self._paused = False
        logger.debug("Event bus resumed")

    def is_paused(self) -> bool:
        """Check if bus is paused."""
        return self._paused

    def clear(self) -> None:
        """Clear all pending events and subscribers."""
        while not self._queue.empty():
            try:
                self._queue.get_nowait()
            except queue.Empty:
                break

        with self._subscriber_lock:
            self._subscribers.clear()
            self._wildcard_subscribers.clear()

        with self._history_lock:
            self._history.clear()

        self._dropped_count = 0
        logger.debug("Event bus cleared")

    def _record_event(
        self, event_type: str, event_dict: Dict[str, Any], delivered: int
    ) -> None:
        """Record event in history."""
        with self._history_lock:
            record = EventRecord(
                event_type=event_type,
                event_data=event_dict.copy(),
                delivered_to=delivered,
            )
            self._history.append(record)

            if len(self._history) > self.MAX_HISTORY:
                self._history = self._history[-self.MAX_HISTORY :]

    def get_history(
        self, event_type: Optional[str] = None, limit: int = 100
    ) -> List[EventRecord]:
        """
        Get event history for debugging.

        Args:
            event_type: Filter by event type (None for all)
            limit: Maximum records to return

        Returns:
            List of EventRecord objects
        """
        with self._history_lock:
            if event_type:
                filtered = [e for e in self._history if e.event_type == event_type]
            else:
                filtered = self._history.copy()

            return filtered[-limit:]

    def get_stats(self) -> Dict[str, Any]:
        """
        Get event bus statistics.

        Returns:
            Dictionary with statistics
        """
        with self._subscriber_lock:
            subscriber_counts = {
                event_type: len(callbacks)
                for event_type, callbacks in self._subscribers.items()
            }

        return {
            "queue_size": self.qsize(),
            "max_queue_size": self.MAX_QUEUE_SIZE,
            "paused": self._paused,
            "dropped_count": self._dropped_count,
            "subscriber_counts": subscriber_counts,
            "wildcard_subscribers": len(self._wildcard_subscribers),
            "history_size": len(self._history) if self._enable_history else "disabled",
        }


def get_event_bus() -> CoreEventBus:
    """
    Get the global event bus instance via DI container.

    Returns:
        CoreEventBus singleton
    """
    try:
        from aura_cli.core.di import Services, get_container

        container = get_container()
        if container.has(Services.EVENT_BUS):
            return container.resolve(Services.EVENT_BUS)
    except Exception as _e:
        logger.debug("DI container unavailable for EventBus, using singleton: %s", _e)
    return CoreEventBus.get_instance()


def publish_event(event: AgiEvent) -> bool:
    """
    Publish an event to the global bus.

    Args:
        event: Event to publish

    Returns:
        True if published successfully
    """
    return get_event_bus().publish(event)


def subscribe_event(
    event_type: AgiEventType, callback: Callable[[Dict[str, Any]], None]
) -> Callable[[], None]:
    """
    Subscribe to an event type on the global bus.

    Args:
        event_type: Event type to subscribe to
        callback: Callback function

    Returns:
        Unsubscribe function
    """
    return get_event_bus().subscribe(event_type, callback)


def get_status_queue() -> queue.Queue:
    """Return the process-wide event queue used by worker adapters.

    Returns:
        Queue instance from the global event bus
    """
    return get_event_bus().get_queue()
