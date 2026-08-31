"""
Tests for thread shutdown functionality.

Tests graceful shutdown of threads managed by ThreadManager
and AppLoop shutdown behavior.
"""

import threading
import time
from unittest.mock import Mock

from aura_cli.cli.app_loop import AppLoop
from aura_cli.cli.utils.thread_manager import ThreadManager, get_thread_manager
from aura_cli.core.logger import get_logger
from tests.runtime_helpers import make_runtime_services

logger = get_logger(__name__)


class TestThreadShutdown:
    """Test thread shutdown functionality."""

    def test_thread_manager_stop_all(self):
        """Test ThreadManager.stop_all() stops all registered threads."""
        manager = ThreadManager()

        # Create some test threads
        results = []

        def worker(name):
            time.sleep(0.1)
            results.append(f"worker_{name}")

        # Register threads
        thread1 = manager.register_thread(
            "test_thread_1", lambda: worker(1), daemon=True
        )
        thread2 = manager.register_thread(
            "test_thread_2", lambda: worker(2), daemon=True
        )
        thread3 = manager.register_thread(
            "test_thread_3", lambda: worker(3), daemon=True
        )

        # Wait a bit for threads to start
        time.sleep(0.05)

        # Stop all threads
        stop_results = manager.stop_all(timeout=2.0)

        # Verify all threads were stopped
        assert len(stop_results) == 3
        assert all(stop_results.values()), (
            "All threads should have stopped successfully"
        )

        # Verify threads are no longer alive
        assert not thread1.is_alive()
        assert not thread2.is_alive()
        assert not thread3.is_alive()

    def test_thread_manager_stop_specific_thread(self):
        """Test ThreadManager.stop_thread() stops a specific thread."""
        manager = ThreadManager()

        def worker():
            time.sleep(1.0)  # Long-running worker

        thread = manager.register_thread("specific_thread", worker, daemon=True)

        # Wait for thread to start
        time.sleep(0.05)
        assert thread.is_alive()

        # Stop specific thread
        result = manager.stop_thread("specific_thread", timeout=2.0)

        assert result is True
        assert not thread.is_alive()

    def test_thread_manager_stop_nonexistent_thread(self):
        """Test stopping a non-existent thread returns False."""
        manager = ThreadManager()

        result = manager.stop_thread("nonexistent_thread", timeout=1.0)

        assert result is False

    def test_thread_manager_stop_with_timeout(self):
        """Test ThreadManager respects timeout when stopping threads."""
        manager = ThreadManager()

        def long_worker():
            time.sleep(5.0)  # Very long-running worker

        manager.register_thread("long_thread", long_worker, daemon=True)

        # Wait for thread to start
        time.sleep(0.05)

        # Try to stop with short timeout
        result = manager.stop_thread("long_thread", timeout=0.5)

        # Should return False due to timeout
        assert result is False

        # Thread should still be alive (but daemon, so will exit when main exits)
        # Note: In real scenario, daemon threads will be killed on program exit

    def test_app_loop_shutdown(self):
        """Test AppLoop.shutdown() gracefully stops all threads."""
        from pathlib import Path

        # Create mock UI and other dependencies
        mock_ui = Mock()
        mock_ui.display_info = Mock()
        mock_ui.display_error = Mock()
        mock_ui.display_warning = Mock()

        # Create AppLoop instance with all required parameters
        app_loop = AppLoop(
            ui=mock_ui,
            stats=Mock(),
            console=Mock(),
            conversation_history=[],
            context_manager=Mock(),
            available_tools={},
            initial_model="auto",
            project_root=Path.cwd(),
            runtime_services=make_runtime_services(Path.cwd()),
        )

        # Create shutdown event
        app_loop.shutdown_event = threading.Event()

        # Register some test threads via ThreadManager
        thread_manager = get_thread_manager()

        def test_worker():
            while not app_loop.shutdown_event.is_set():
                time.sleep(0.1)

        thread1 = thread_manager.register_thread(
            "app_loop_test_1", test_worker, daemon=True
        )
        thread2 = thread_manager.register_thread(
            "app_loop_test_2", test_worker, daemon=True
        )

        # Wait for threads to start
        time.sleep(0.1)
        assert thread1.is_alive()
        assert thread2.is_alive()

        # Call shutdown
        result = app_loop.shutdown(timeout=2.0)

        # Verify shutdown was successful
        assert result is True

        # Verify shutdown event was set
        assert app_loop.shutdown_event.is_set()

        # Clean up threads
        thread_manager.stop_all(timeout=1.0)

    def test_app_loop_shutdown_with_legacy_threads(self):
        """Test AppLoop.shutdown() handles legacy thread references."""
        from pathlib import Path

        mock_ui = Mock()
        mock_ui.display_info = Mock()
        mock_ui.display_error = Mock()
        mock_ui.display_warning = Mock()

        app_loop = AppLoop(
            ui=mock_ui,
            stats=Mock(),
            console=Mock(),
            conversation_history=[],
            context_manager=Mock(),
            available_tools={},
            initial_model="auto",
            project_root=Path.cwd(),
            runtime_services=make_runtime_services(Path.cwd()),
        )

        app_loop.shutdown_event = threading.Event()

        # Create legacy thread references (simulating old code)
        def legacy_worker():
            time.sleep(0.5)

        legacy_thread = threading.Thread(target=legacy_worker, daemon=True)
        legacy_thread.start()
        app_loop.agi_thread = legacy_thread

        # Wait for thread to start
        time.sleep(0.1)

        # Call shutdown
        result = app_loop.shutdown(timeout=2.0)

        # Should handle legacy threads gracefully
        assert result is True

    def test_daemon_threads_dont_block_shutdown(self):
        """Test that daemon threads don't block program shutdown."""
        manager = ThreadManager()

        def daemon_worker():
            while True:  # Infinite loop
                time.sleep(0.1)

        # Register daemon thread
        thread = manager.register_thread("daemon_test", daemon_worker, daemon=True)

        # Wait for thread to start
        time.sleep(0.05)
        assert thread.is_alive()

        # Daemon threads should not block shutdown
        # In real scenario, program would exit and daemon threads would be killed
        # Here we just verify it's marked as daemon
        assert thread.daemon is True

    def test_thread_manager_thread_wrapper_error_handling(self):
        """Test ThreadManager._thread_wrapper handles errors gracefully."""
        manager = ThreadManager()

        def failing_worker():
            raise ValueError("Test error")

        # Register thread that will fail
        thread = manager.register_thread("failing_thread", failing_worker, daemon=True)

        # Wait for thread to complete (or fail)
        time.sleep(0.2)

        # Thread should have completed (even with error)
        # The wrapper should catch the error and log it
        assert not thread.is_alive()

    def test_multiple_shutdown_calls(self):
        """Test that multiple shutdown calls are safe."""
        manager = ThreadManager()

        def worker():
            time.sleep(0.1)

        thread = manager.register_thread("multi_shutdown_test", worker, daemon=True)
        time.sleep(0.05)

        # Call shutdown multiple times
        result1 = manager.stop_all(timeout=1.0)
        result2 = manager.stop_all(timeout=1.0)
        result3 = manager.stop_all(timeout=1.0)

        # All calls should succeed (idempotent)
        assert result1 == result2 == result3
        assert not thread.is_alive()
