"""TUI adapter for the presentation-neutral reactive state store."""

from __future__ import annotations

from typing import Any

from aura_cli.application.presentation.state_store import (
    ReactiveStateStore,
    StateSnapshot,
)

DEFAULT_TUI_STATE: dict[str, Any] = {
    "tasks": {},
    "messages": [],
    "stats": {},
    "config": {},
    "ui": {
        "focused_task": None,
        "active_panel": "events",
        "theme": "nebula-dark",
    },
    "session": {"id": None, "started_at": None},
}

# Compatibility name retained for plugins and existing integrations.
StoreSnapshot = StateSnapshot


class SyncStore(ReactiveStateStore):
    """Aura TUI state shape plus convenience operations used by its widgets."""

    def __init__(self, initial_state: dict[str, Any] | None = None) -> None:
        super().__init__(DEFAULT_TUI_STATE if initial_state is None else initial_state)

    def add_task(self, task_id: str, task_data: dict[str, Any]) -> None:
        self.set(f"tasks.{task_id}", task_data)

    def get_task(self, task_id: str) -> dict[str, Any] | None:
        return self.get(f"tasks.{task_id}")

    def update_task_status(self, task_id: str, status: str) -> None:
        self.set(f"tasks.{task_id}.status", status)

    def add_message(self, message: dict[str, Any]) -> None:
        # Copy before mutation so callers holding the current list do not see an
        # unannounced state transition.
        messages = list(self.get("messages", []))
        messages.append(message)
        self.set("messages", messages)

    def get_messages(self, limit: int = 100) -> list[dict[str, Any]]:
        return self.get("messages", [])[-limit:]

    def update_stats(self, stats: dict[str, Any]) -> None:
        with self.batch_update():
            for key, value in stats.items():
                self.set(f"stats.{key}", value)

    def set_focused_task(self, task_id: str | None) -> None:
        self.set("ui.focused_task", task_id)

    def get_focused_task(self) -> str | None:
        return self.get("ui.focused_task")


_global_store: SyncStore | None = None


def get_store() -> SyncStore:
    """Return the process-wide TUI store."""
    global _global_store
    if _global_store is None:
        _global_store = SyncStore()
    return _global_store


def reset_store() -> SyncStore:
    """Replace and return the process-wide TUI store."""
    global _global_store
    _global_store = SyncStore()
    return _global_store


__all__ = [
    "DEFAULT_TUI_STATE",
    "StoreSnapshot",
    "SyncStore",
    "get_store",
    "reset_store",
]
