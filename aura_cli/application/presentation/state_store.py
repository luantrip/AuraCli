"""Presentation-neutral reactive state storage.

Adapters choose the state shape and own any process-global instance.  This
module only implements path access, subscriptions, batching, and snapshots.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable, Iterator, Mapping
from contextlib import contextmanager
from copy import deepcopy
from dataclasses import dataclass, field
from datetime import datetime
import logging
from typing import Any

logger = logging.getLogger(__name__)

State = dict[str, Any]
StateListener = Callable[[str, Any], None]


@dataclass(frozen=True)
class StateSnapshot:
    """Independent copy of state captured at a point in time."""

    state: State
    timestamp: datetime = field(default_factory=datetime.now)
    description: str = ""


class ReactiveStateStore:
    """Nested state with dot-path access and synchronous notifications."""

    MAX_SNAPSHOTS = 50

    def __init__(self, initial_state: Mapping[str, Any] | None = None) -> None:
        self._initial_state: State = deepcopy(dict(initial_state or {}))
        self._state: State = deepcopy(self._initial_state)
        self._listeners: dict[str, list[StateListener]] = defaultdict(list)
        self._batch_depth = 0
        self._pending_notifications: set[str] = set()
        self._snapshots: list[StateSnapshot] = []

    def get(self, path: str, default: Any = None) -> Any:
        if not path:
            return self._state
        current: Any = self._state
        for key in path.split("."):
            if isinstance(current, dict):
                if key not in current:
                    return default
                current = current[key]
            elif isinstance(current, list):
                try:
                    current = current[int(key)]
                except (ValueError, IndexError):
                    return default
            else:
                return default
        return current

    def set(self, path: str, value: Any) -> None:
        keys = self._validated_keys(path)
        current = self._state
        for key in keys[:-1]:
            child = current.get(key)
            if not isinstance(child, dict):
                child = {}
                current[key] = child
            current = child
        current[keys[-1]] = value

        if self._batch_depth:
            self._pending_notifications.add(path)
            self._pending_notifications.update(
                ".".join(keys[:index]) for index in range(1, len(keys))
            )
        else:
            self._notify(path, value)

    def update(self, path: str, updater: Callable[[Any], Any]) -> None:
        self.set(path, updater(self.get(path)))

    def delete(self, path: str) -> bool:
        keys = self._validated_keys(path)
        current: Any = self._state
        for key in keys[:-1]:
            if not isinstance(current, dict) or key not in current:
                return False
            current = current[key]
        if not isinstance(current, dict) or keys[-1] not in current:
            return False
        del current[keys[-1]]
        if self._batch_depth:
            self._pending_notifications.add(path)
        else:
            self._notify(path, None)
        return True

    def subscribe(self, path: str, callback: StateListener) -> Callable[[], None]:
        self._listeners[path].append(callback)

        def unsubscribe() -> None:
            listeners = self._listeners[path]
            if callback in listeners:
                listeners.remove(callback)

        return unsubscribe

    @contextmanager
    def batch_update(self) -> Iterator[None]:
        self._batch_depth += 1
        try:
            yield
        finally:
            self._batch_depth -= 1
            if not self._batch_depth:
                self._flush_notifications()

    def snapshot(self, description: str = "") -> StateSnapshot:
        snapshot = StateSnapshot(deepcopy(self._state), description=description)
        self._snapshots.append(snapshot)
        if len(self._snapshots) > self.MAX_SNAPSHOTS:
            self._snapshots = self._snapshots[-self.MAX_SNAPSHOTS :]
        return snapshot

    def restore(self, snapshot: StateSnapshot) -> None:
        self._state = deepcopy(snapshot.state)
        self._notify("", self._state)

    def get_snapshots(self) -> list[StateSnapshot]:
        return self._snapshots.copy()

    def clear(self) -> None:
        self._state = deepcopy(self._initial_state)
        self._notify("", self._state)

    @property
    def state(self) -> State:
        return self._state.copy()

    @staticmethod
    def _validated_keys(path: str) -> list[str]:
        keys = path.split(".") if path else []
        if not keys or any(not key for key in keys):
            raise ValueError("state path must contain non-empty dot-separated keys")
        return keys

    def _notify(self, path: str, value: Any) -> None:
        watched_paths = [path]
        keys = path.split(".") if path else []
        watched_paths.extend(".".join(keys[:index]) for index in range(1, len(keys)))
        if path:
            watched_paths.append("")

        for watched_path in watched_paths:
            for callback in tuple(self._listeners.get(watched_path, ())):
                try:
                    callback(path, value)
                except Exception:
                    logger.exception("State listener failed for path %r", watched_path)

    def _flush_notifications(self) -> None:
        pending = sorted(self._pending_notifications, key=lambda path: -path.count("."))
        self._pending_notifications.clear()
        final_paths: list[str] = []
        for path in pending:
            if not any(child.startswith(path + ".") for child in final_paths):
                final_paths.append(path)
        for path in final_paths:
            self._notify(path, self.get(path))
