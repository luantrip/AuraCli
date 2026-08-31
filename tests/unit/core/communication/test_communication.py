"""Tests for core.communication.streaming (StreamManager, StreamType)."""

from aura_cli.core.communication.streaming import StreamManager, StreamType


class TestStreamManager:
    """Tests for StreamManager."""

    def test_manager_initialization(self):
        manager = StreamManager()
        assert len(manager.streams) == 0

    def test_create_stream(self):
        manager = StreamManager()
        stream = manager.create_stream("test_stream", StreamType.TEXT, max_size=100)
        assert stream.stream_id == "test_stream"
        assert stream.stream_type == StreamType.TEXT
        assert stream.max_size == 100
        assert "test_stream" in manager.streams

    def test_publish_subscribe(self):
        manager = StreamManager()
        manager.create_stream("test_stream", StreamType.TEXT)
        received = []

        def callback(data):
            received.append(data)

        manager.subscribe("test_stream", callback)
        manager.publish("test_stream", "test data")
        assert len(received) == 1
        assert received[0] == "test data"

    def test_buffer_limit(self):
        manager = StreamManager()
        stream = manager.create_stream("test", StreamType.TEXT, max_size=3)
        for i in range(5):
            manager.publish("test", f"data{i}")
        assert len(stream.buffer) <= 3
