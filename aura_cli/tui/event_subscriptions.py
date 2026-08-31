"""Owned event-bus subscriptions for one Textual application instance."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, Protocol


class SubscriptionBus(Protocol):
    def subscribe(
        self, event_type: str, callback: Callable[[Any], None]
    ) -> Callable[[], None]: ...


class TUIEventHost(Protocol):
    def _on_toast_event(self, payload: Any) -> None: ...
    def _on_command_event(self, payload: Any) -> None: ...
    def _on_navigate_event(self, payload: Any) -> None: ...


def bind_tui_events(
    bus: SubscriptionBus, host: TUIEventHost
) -> list[Callable[[], None]]:
    """Bind the application event channels and return their owned releases."""
    return [
        bus.subscribe("tui.toast.show", host._on_toast_event),
        bus.subscribe("tui.command.execute", host._on_command_event),
        bus.subscribe("tui.navigate", host._on_navigate_event),
    ]


def release_subscriptions(unsubscribers: list[Callable[[], None]]) -> None:
    """Release all owned subscriptions exactly once."""
    owned = list(unsubscribers)
    unsubscribers.clear()
    for unsubscribe in owned:
        unsubscribe()
