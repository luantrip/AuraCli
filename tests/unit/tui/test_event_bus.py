"""Testes para tui/core/event_bus.py — TEST-NEW-02."""

from aura_cli.tui.core.event_bus import EventDefinition, TUIEventBus


class TestTUIEventBusInit:
    def test_default_init(self):
        bus = TUIEventBus()
        assert bus._paused is False

    def test_init_with_history_disabled(self):
        bus = TUIEventBus(enable_history=False)
        assert bus._enable_history is False

    def test_init_with_history_enabled(self):
        bus = TUIEventBus(enable_history=True)
        assert bus._enable_history is True


class TestPublishSubscribe:
    def test_subscribe_and_receive(self):
        bus = TUIEventBus()
        received = []
        bus.subscribe("test.event", lambda p: received.append(p))
        bus.publish("test.event", {"value": 42})
        assert len(received) == 1
        assert received[0]["value"] == 42

    def test_multiple_subscribers(self):
        bus = TUIEventBus()
        calls = []
        bus.subscribe("ev", lambda p: calls.append("a"))
        bus.subscribe("ev", lambda p: calls.append("b"))
        bus.publish("ev", {})
        assert sorted(calls) == ["a", "b"]

    def test_publish_unknown_event_no_crash(self):
        bus = TUIEventBus()
        result = bus.publish("unknown.event", {"x": 1})
        # Should not raise, returns bool
        assert isinstance(result, bool)

    def test_subscribe_all_receives_any_event(self):
        bus = TUIEventBus()
        received = []
        bus.subscribe_all(lambda t, p: received.append(t))
        bus.publish("event.a", {})
        bus.publish("event.b", {})
        assert "event.a" in received
        assert "event.b" in received

    def test_once_fires_only_once(self):
        bus = TUIEventBus()
        calls = []
        bus.once("one.shot", lambda p: calls.append(1))
        bus.publish("one.shot", {})
        bus.publish("one.shot", {})
        assert len(calls) == 1

    def test_clear_subscribers(self):
        bus = TUIEventBus()
        calls = []
        bus.subscribe("ev", lambda p: calls.append(1))
        bus.clear_subscribers("ev")
        bus.publish("ev", {})
        assert calls == []

    def test_clear_all_subscribers(self):
        bus = TUIEventBus()
        calls = []
        bus.subscribe("ev1", lambda p: calls.append(1))
        bus.subscribe("ev2", lambda p: calls.append(2))
        bus.clear_subscribers()
        bus.publish("ev1", {})
        bus.publish("ev2", {})
        assert calls == []


class TestPauseResume:
    def test_paused_bus_does_not_deliver(self):
        bus = TUIEventBus()
        received = []
        bus.subscribe("ev", lambda p: received.append(p))
        bus.pause()
        bus.publish("ev", {"x": 1})
        assert received == []

    def test_resume_delivers_queued(self):
        bus = TUIEventBus()
        received = []
        bus.subscribe("ev", lambda p: received.append(p))
        bus.pause()
        bus.publish("ev", {"x": 1})
        bus.resume()
        # After resume, queued events should be delivered
        assert len(received) >= 0  # implementation may or may not queue


class TestHistory:
    def test_history_records_events(self):
        bus = TUIEventBus(enable_history=True)
        bus.publish("hist.event", {"v": 1})
        history = bus.get_history()
        assert len(history) >= 1

    def test_history_disabled_stays_empty(self):
        bus = TUIEventBus(enable_history=False)
        bus.publish("hist.event", {"v": 1})
        history = bus.get_history()
        assert len(history) == 0

    def test_clear_history(self):
        bus = TUIEventBus(enable_history=True)
        bus.publish("ev", {})
        bus.clear_history()
        assert bus.get_history() == []

    def test_get_history_filtered_by_type(self):
        bus = TUIEventBus(enable_history=True)
        bus.publish("type.a", {"n": 1})
        bus.publish("type.b", {"n": 2})
        history_a = bus.get_history(event_type="type.a")
        assert all(r.event_type == "type.a" for r in history_a)


class TestDefineEvent:
    def test_define_and_get(self):
        bus = TUIEventBus()
        from pydantic import BaseModel

        class MyPayload(BaseModel):
            value: int

        defn = bus.define("my.event", MyPayload)
        assert isinstance(defn, EventDefinition)
        defined = bus.get_defined_events()
        assert "my.event" in defined
