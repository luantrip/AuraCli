"""Contract tests for the global thread lifecycle manager."""

from __future__ import annotations

import threading

from aura_cli.cli.utils.thread_manager import ThreadManager, ThreadStatus


def test_thread_error_remains_observable_after_wrapper_finishes() -> None:
    manager = ThreadManager()

    def failing_target() -> None:
        raise RuntimeError("boom")

    manager.register_thread("failing", failing_target)
    thread = manager.get_thread("failing")
    assert thread is not None
    thread.join(timeout=1.0)

    info = manager.get_thread_info("failing")
    assert info is not None
    assert info.status is ThreadStatus.ERROR
    assert isinstance(info.error, RuntimeError)
    assert manager.get_thread_status("failing") is ThreadStatus.ERROR


def test_register_after_shutdown_clears_stale_shutdown_event() -> None:
    manager = ThreadManager()
    manager.stop_all(timeout=0.1)
    assert manager.shutdown_event.is_set()

    finished = threading.Event()

    def target() -> None:
        finished.set()

    manager.register_thread("after-shutdown", target)
    thread = manager.get_thread("after-shutdown")
    assert thread is not None
    thread.join(timeout=1.0)

    assert finished.is_set()
    assert not manager.shutdown_event.is_set()
