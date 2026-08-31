from datetime import datetime

import pytest

from aura_cli.application.extensions import (
    ExtensionLifecycle,
    ExtensionRegistry,
    ExtensionStatus,
    LifecycleEvent,
)


def test_extension_registry_tracks_status_and_statistics() -> None:
    registry = ExtensionRegistry()
    registry.register("one", "1.0")
    assert registry.set_status("one", ExtensionStatus.ENABLED) is True

    assert registry.get_extension("one").status is ExtensionStatus.ENABLED
    assert registry.get_statistics()["by_status"]["enabled"] == 1
    assert registry.set_status("missing", ExtensionStatus.ERROR) is False


def test_registry_uses_optional_presenter() -> None:
    presented = []
    registry = ExtensionRegistry(presenter=lambda items: presented.extend(items))
    registry.register("z", "1")
    registry.register("a", "1")

    registry.display_registry()

    assert [item.name for item in presented] == ["a", "z"]


def test_lifecycle_filters_handlers_and_bounds_history() -> None:
    lifecycle = ExtensionLifecycle(
        clock=lambda: datetime(2026, 1, 1),
        history_limit=1,
    )
    lifecycle.register_handler(LifecycleEvent.LOAD, lambda: "one", "one")
    lifecycle.register_handler(LifecycleEvent.LOAD, lambda: "two", "two")

    assert lifecycle.trigger_event(LifecycleEvent.LOAD, "two") == ["two"]
    lifecycle.trigger_event(LifecycleEvent.STOP)

    assert len(lifecycle.get_event_history()) == 1
    assert lifecycle.get_statistics()["total_handlers"] == 2


def test_lifecycle_rejects_invalid_history_limit() -> None:
    with pytest.raises(ValueError, match="positive"):
        ExtensionLifecycle(history_limit=0)
