"""Tests for core/events/event_bus.py — CoreEventBus."""

import queue

import pytest

from aura_cli.core.events.event_bus import CoreEventBus, get_event_bus


@pytest.fixture(autouse=True)
def reset_bus():
    CoreEventBus.reset_instance()
    yield
    CoreEventBus.reset_instance()


class TestCoreEventBus:
    def test_get_instance_returns_singleton(self):
        b1 = CoreEventBus.get_instance()
        b2 = CoreEventBus.get_instance()
        assert b1 is b2

    def test_reset_creates_new_instance(self):
        b1 = CoreEventBus.get_instance()
        CoreEventBus.reset_instance()
        b2 = CoreEventBus.get_instance()
        assert b1 is not b2

    def test_get_queue_returns_queue(self):
        bus = get_event_bus()
        q = bus.get_queue()
        assert isinstance(q, queue.Queue)

    def test_publish_dict_puts_event_in_queue(self):
        bus = get_event_bus()
        q = bus.get_queue()
        bus.publish_dict({"type": "test", "data": "hello"})
        assert not q.empty()

    def test_subscribe_and_receive_event(self):
        bus = get_event_bus()
        received = []
        bus.subscribe("my_event", lambda data: received.append(data))
        # publish_dict dispatches to subscribers by 'type' key
        bus.publish_dict({"type": "my_event", "msg": "hello"})
        assert len(received) >= 1

    def test_multiple_subscribers(self):
        bus = get_event_bus()
        results = []
        bus.subscribe("evt", lambda d: results.append("a"))
        bus.subscribe("evt", lambda d: results.append("b"))
        bus.publish_dict({"type": "evt"})
        assert "a" in results
        assert "b" in results

    def test_get_event_bus_returns_singleton(self):
        b1 = get_event_bus()
        b2 = get_event_bus()
        assert b1 is b2
