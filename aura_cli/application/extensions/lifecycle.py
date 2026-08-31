"""Extension lifecycle orchestration."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
import logging
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)


class LifecycleEvent(Enum):
    LOAD = "load"
    ENABLE = "enable"
    DISABLE = "disable"
    UNLOAD = "unload"
    START = "start"
    STOP = "stop"
    ERROR = "error"


@dataclass
class LifecycleHandler:
    event: LifecycleEvent
    handler: Callable[[], Any]
    extension_name: str


class ExtensionLifecycle:
    """Register, trigger and audit extension lifecycle callbacks."""

    def __init__(
        self,
        *,
        clock: Callable[[], datetime] = datetime.now,
        history_limit: int = 1000,
    ) -> None:
        if history_limit < 1:
            raise ValueError("Lifecycle history limit must be positive")
        self.handlers: dict[LifecycleEvent, list[LifecycleHandler]] = {
            event: [] for event in LifecycleEvent
        }
        self.event_history: list[dict[str, Any]] = []
        self._clock = clock
        self._history_limit = history_limit

    def register_handler(
        self,
        event: LifecycleEvent,
        handler: Callable[[], Any],
        extension_name: str = "system",
    ) -> None:
        self.handlers[event].append(LifecycleHandler(event, handler, extension_name))

    def trigger_event(
        self,
        event: LifecycleEvent,
        extension_name: Optional[str] = None,
        context: Optional[dict[str, Any]] = None,
    ) -> list[Any]:
        del context
        handlers = self.handlers.get(event, [])
        if extension_name is not None:
            handlers = [
                handler
                for handler in handlers
                if handler.extension_name == extension_name
            ]
        results: list[Any] = []
        for registered in handlers:
            try:
                results.append(registered.handler())
            except Exception as exc:
                logger.error(
                    "Extension lifecycle handler %s failed: %s",
                    registered.extension_name,
                    exc,
                    exc_info=True,
                )
        self.event_history.append(
            {
                "event": event.value,
                "extension_name": extension_name or "all",
                "timestamp": self._clock().isoformat(),
                "handlers_executed": len(handlers),
            }
        )
        self.event_history = self.event_history[-self._history_limit :]
        return results

    def get_event_history(
        self, extension_name: Optional[str] = None
    ) -> list[dict[str, Any]]:
        if extension_name is None:
            return self.event_history.copy()
        return [
            event
            for event in self.event_history
            if event.get("extension_name") == extension_name
        ]

    def get_statistics(self) -> dict[str, Any]:
        return {
            "total_handlers": sum(len(items) for items in self.handlers.values()),
            "by_event": {
                event.value: len(self.handlers.get(event, []))
                for event in LifecycleEvent
            },
            "total_events": len(self.event_history),
        }
