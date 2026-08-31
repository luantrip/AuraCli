"""Application-level contract tests for typed presentation events."""

from pydantic import BaseModel

from aura_cli.application.presentation.event_bus import TypedEventBus


class CountPayload(BaseModel):
    count: int


def test_schema_validation_precedes_delivery() -> None:
    bus = TypedEventBus()
    bus.define("counted", CountPayload)
    received: list[dict[str, object]] = []
    bus.subscribe("counted", received.append)

    assert bus.publish("counted", {"count": "3"}) is True
    assert received == [{"count": 3}]
    assert bus.publish("counted", {"count": "invalid"}) is False
    assert len(received) == 1


def test_once_unsubscribes_before_recursive_publication() -> None:
    bus = TypedEventBus()
    received: list[int] = []

    def publish_again(payload: dict[str, object]) -> None:
        received.append(1)
        bus.publish("recursive", payload)

    bus.once("recursive", publish_again)
    bus.publish("recursive", {})
    assert received == [1]


def test_failed_validation_is_retained_for_diagnostics() -> None:
    bus = TypedEventBus()
    bus.define("counted", CountPayload)
    bus.publish("counted", {"count": "invalid"})

    record = bus.get_history()[0]
    assert record.event_type == "counted"
    assert record.validated is False
