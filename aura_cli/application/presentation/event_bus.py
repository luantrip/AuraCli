"""Typed synchronous events independent of CLI or TUI frameworks."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
import logging
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, ValidationError

logger = logging.getLogger(__name__)

PayloadModel = TypeVar("PayloadModel", bound=BaseModel)
Payload = dict[str, Any]
EventHandler = Callable[[Payload], None]
WildcardEventHandler = Callable[[str, Payload], None]


@dataclass(frozen=True)
class EventDefinition(Generic[PayloadModel]):
    """Name, validation schema, and documentation for an event."""

    event_type: str
    schema: type[PayloadModel]
    description: str = ""

    def create(self, **kwargs: Any) -> PayloadModel:
        return self.schema(**kwargs)


@dataclass(frozen=True)
class EventRecord:
    """Historical record of a publication attempt."""

    event_type: str
    payload: Payload
    timestamp: datetime = field(default_factory=datetime.now)
    validated: bool = True


class TypedEventBus:
    """In-process event bus with schema validation and bounded history."""

    MAX_HISTORY = 1000

    def __init__(self, enable_history: bool = True) -> None:
        self._subscribers: dict[str, list[EventHandler]] = defaultdict(list)
        self._wildcard_subscribers: list[WildcardEventHandler] = []
        self._event_schemas: dict[str, type[BaseModel]] = {}
        self._event_definitions: dict[str, EventDefinition[Any]] = {}
        self._history: list[EventRecord] = []
        self._enable_history = enable_history
        self._paused = False

    def define(
        self,
        event_type: str,
        schema: type[PayloadModel],
        description: str = "",
    ) -> EventDefinition[PayloadModel]:
        if event_type in self._event_schemas:
            logger.warning("Event type %r already defined; overwriting", event_type)
        definition = EventDefinition(event_type, schema, description)
        self._event_schemas[event_type] = schema
        self._event_definitions[event_type] = definition
        return definition

    def publish(self, event_type: str, payload: Payload) -> bool:
        if self._paused:
            return False

        delivered_payload = payload
        validated = True
        schema = self._event_schemas.get(event_type)
        if schema is not None:
            try:
                delivered_payload = schema(**payload).model_dump()
            except ValidationError as error:
                logger.warning("Event validation failed for %r: %s", event_type, error)
                validated = False

        if self._enable_history:
            self._record_event(event_type, delivered_payload, validated)
        if not validated:
            return False

        for callback in tuple(self._subscribers.get(event_type, ())):
            self._call_handler(callback, delivered_payload, event_type)
        for wildcard_callback in tuple(self._wildcard_subscribers):
            try:
                wildcard_callback(event_type, delivered_payload)
            except Exception:
                logger.exception("Wildcard event handler failed for %r", event_type)
        return True

    def publish_typed(
        self,
        definition: EventDefinition[PayloadModel],
        payload: PayloadModel,
    ) -> bool:
        return self.publish(definition.event_type, payload.model_dump())

    def subscribe(self, event_type: str, callback: EventHandler) -> Callable[[], None]:
        self._subscribers[event_type].append(callback)

        def unsubscribe() -> None:
            subscribers = self._subscribers[event_type]
            if callback in subscribers:
                subscribers.remove(callback)

        return unsubscribe

    def subscribe_all(self, callback: WildcardEventHandler) -> Callable[[], None]:
        self._wildcard_subscribers.append(callback)

        def unsubscribe() -> None:
            if callback in self._wildcard_subscribers:
                self._wildcard_subscribers.remove(callback)

        return unsubscribe

    def once(self, event_type: str, callback: EventHandler) -> Callable[[], None]:
        unsubscribe: Callable[[], None]

        def wrapper(payload: Payload) -> None:
            # Unsubscribe first so recursive publication remains once-only.
            unsubscribe()
            callback(payload)

        unsubscribe = self.subscribe(event_type, wrapper)
        return unsubscribe

    def pause(self) -> None:
        self._paused = True

    def resume(self) -> None:
        self._paused = False

    def clear_subscribers(self, event_type: str | None = None) -> None:
        if event_type is None:
            self._subscribers.clear()
            self._wildcard_subscribers.clear()
        else:
            self._subscribers[event_type].clear()

    def get_history(
        self, event_type: str | None = None, limit: int = 100
    ) -> list[EventRecord]:
        records = self._history
        if event_type is not None:
            records = [record for record in records if record.event_type == event_type]
        return records[-limit:] if limit > 0 else []

    def clear_history(self) -> None:
        self._history.clear()

    def get_defined_events(self) -> dict[str, EventDefinition[Any]]:
        return self._event_definitions.copy()

    def _record_event(self, event_type: str, payload: Payload, validated: bool) -> None:
        self._history.append(EventRecord(event_type, payload, validated=validated))
        if len(self._history) > self.MAX_HISTORY:
            del self._history[: -self.MAX_HISTORY]

    @staticmethod
    def _call_handler(
        callback: EventHandler, payload: Payload, event_type: str
    ) -> None:
        try:
            callback(payload)
        except Exception:
            logger.exception("Event handler failed for %r", event_type)
