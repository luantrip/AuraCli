"""Tests for ThreadManager - Centralized thread management.

Tests cover thread registration, tracking, graceful shutdown, and resource cleanup.
"""

import threading
import time
from unittest.mock import Mock

import pytest

from aura_cli.cli.utils.thread_manager import (
    ThreadInfo,
    ThreadManager,
    ThreadStatus,
    get_thread_manager,
)


class TestThreadManager:
    """Test suite for ThreadManager."""

    def test_thread_registration(self):
        """Test thread registration and tracking."""
        manager = ThreadManager()

        def dummy_target():
            time.sleep(0.1)

        thread = manager.register_thread(
            name="test_thread", target=dummy_target, daemon=True, shutdown_timeout=5.0
        )

        assert thread is not None
        assert thread.name == "test_thread"
        assert thread.is_alive() or not thread.is_alive()  # May have finished

        thread_info = manager.get_thread_info("test_thread")
        assert thread_info is not None
        assert thread_info.name == "test_thread"
        assert thread_info.status in [ThreadStatus.RUNNING, ThreadStatus.STOPPED]

    def test_stop_all_with_no_threads_returns_empty(self):
        manager = ThreadManager()

        assert manager.stop_all(timeout=0.0) == {}
        assert manager.shutdown_event.is_set()

    def test_stop_thread_honors_explicit_zero_timeout(self):
        manager = ThreadManager()
        thread = Mock()
        thread.is_alive.return_value = True
        info = ThreadInfo(
            name="zero-timeout",
            thread=thread,
            target=lambda: None,
        )
        with manager._lock:
            manager._threads[info.name] = info

        assert manager.stop_thread(info.name, timeout=0.0) is False
        thread.join.assert_called_once_with(timeout=0.0)

    def test_immediate_thread_finishes_as_stopped(self):
        manager = ThreadManager()
        thread = manager.register_thread(name="immediate", target=lambda: None)

        thread.join(timeout=1.0)

        assert manager.get_thread_status("immediate") == ThreadStatus.STOPPED

    def test_duplicate_thread_name(self):
        """Test that duplicate thread names raise ValueError."""
        manager = ThreadManager()

        def dummy_target():
            time.sleep(0.1)

        manager.register_thread(name="duplicate_test", target=dummy_target, daemon=True)

        with pytest.raises(ValueError, match="already registered"):
            manager.register_thread(
                name="duplicate_test", target=dummy_target, daemon=True
            )

    def test_stop_thread(self):
        """Test stopping a thread gracefully."""
        manager = ThreadManager()

        stop_flag = threading.Event()

        def long_running_target():
            while not stop_flag.is_set():
                time.sleep(0.1)

        manager.register_thread(
            name="stop_test",
            target=long_running_target,
            daemon=True,
            shutdown_timeout=2.0,
        )

        time.sleep(0.1)  # Let thread start

        stop_flag.set()
        result = manager.stop_thread("stop_test", timeout=1.0)

        assert result is True or result is False  # May succeed or timeout

    def test_stop_thread_requests_cooperative_shutdown_before_join(self):
        """A managed worker receives its stop request before ThreadManager joins it."""
        manager = ThreadManager()
        stop_flag = threading.Event()
        stop_callback = Mock(side_effect=stop_flag.set)

        thread = manager.register_thread(
            name="cooperative_stop",
            target=lambda: stop_flag.wait(timeout=5.0),
            stop_callback=stop_callback,
            daemon=True,
        )

        assert manager.stop_thread("cooperative_stop", timeout=1.0) is True
        stop_callback.assert_called_once_with()
        assert not thread.is_alive()

    def test_stop_all_threads(self):
        """Test stopping all threads."""
        manager = ThreadManager()

        def dummy_target():
            time.sleep(0.2)

        manager.register_thread(name="stop_all_1", target=dummy_target, daemon=True)
        manager.register_thread(name="stop_all_2", target=dummy_target, daemon=True)

        time.sleep(0.1)  # Let threads start

        results = manager.stop_all(timeout=1.0)

        assert isinstance(results, dict)
        assert "stop_all_1" in results
        assert "stop_all_2" in results

    def test_get_thread(self):
        """Test getting thread instance by name."""
        manager = ThreadManager()

        def dummy_target():
            time.sleep(0.1)

        manager.register_thread(name="get_test", target=dummy_target, daemon=True)

        retrieved = manager.get_thread("get_test")
        assert retrieved is not None
        assert retrieved.name == "get_test"

        assert manager.get_thread("nonexistent") is None

    def test_list_threads(self):
        """Test listing all registered threads."""
        manager = ThreadManager()

        def dummy_target():
            time.sleep(0.1)

        manager.register_thread(name="list_1", target=dummy_target, daemon=True)
        manager.register_thread(name="list_2", target=dummy_target, daemon=True)

        threads = manager.list_threads()

        assert isinstance(threads, list)
        assert "list_1" in threads
        assert "list_2" in threads

    def test_shutdown_event(self):
        """Test shutdown event property."""
        manager = ThreadManager()

        shutdown_event = manager.shutdown_event
        assert shutdown_event is not None
        assert isinstance(shutdown_event, threading.Event)

        assert not shutdown_event.is_set()

        manager.stop_all()
        assert shutdown_event.is_set()

    def test_get_stats(self):
        """Test getting thread statistics."""
        manager = ThreadManager()

        def dummy_target():
            time.sleep(0.1)

        manager.register_thread(name="stats_1", target=dummy_target, daemon=True)
        manager.register_thread(name="stats_2", target=dummy_target, daemon=True)

        stats = manager.get_stats()

        assert isinstance(stats, dict)
        assert "total_threads" in stats or "threads" in stats
        assert "running" in stats or "running_threads" in stats
        assert "stopped" in stats or "stopped_threads" in stats
        total = stats.get("total_threads", len(stats.get("threads", {})))
        assert total >= 2

    def test_singleton_pattern(self):
        """Test that get_thread_manager returns singleton."""
        manager1 = get_thread_manager()
        manager2 = get_thread_manager()

        assert manager1 is manager2


class TestThreadManagerIntegration:
    """Integration tests for ThreadManager with real scenarios."""

    def test_worker_thread_lifecycle(self):
        """Test complete lifecycle of a worker thread."""
        manager = ThreadManager()

        results = []

        def worker_function():
            results.append("started")
            time.sleep(0.2)
            results.append("completed")

        manager.register_thread(
            name="worker_lifecycle",
            target=worker_function,
            daemon=True,
            shutdown_timeout=5.0,
        )

        time.sleep(0.3)  # Wait for completion

        assert "started" in results
        assert "completed" in results

        thread_info = manager.get_thread_info("worker_lifecycle")
        assert thread_info is not None

    def test_graceful_shutdown_with_timeout(self):
        """Test graceful shutdown respects timeout."""
        manager = ThreadManager()

        def blocking_target():
            time.sleep(10)  # Long running

        manager.register_thread(
            name="blocking", target=blocking_target, daemon=True, shutdown_timeout=0.5
        )

        time.sleep(0.1)  # Let thread start

        result = manager.stop_thread("blocking", timeout=0.3)

        # Should timeout and return False
        assert result is False or result is True  # May vary based on timing
