"""Centralized Thread Manager for Aura CLI.

Provides unified management of all threads in the CLI application, ensuring
graceful shutdown, health monitoring, and resource cleanup.

Features:
    - Thread registration and tracking
    - Graceful shutdown with timeouts
    - Health checks and monitoring
    - Resource cleanup coordination
    - Thread pool management
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import logging
import threading
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class ThreadStatus(Enum):
    """Status of a managed thread."""

    PENDING = "pending"
    RUNNING = "running"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"


@dataclass
class ThreadInfo:
    """Information about a managed thread."""

    name: str
    thread: threading.Thread
    target: Callable
    daemon: bool = True
    status: ThreadStatus = ThreadStatus.PENDING
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    stopped_at: Optional[datetime] = None
    error: Optional[Exception] = None
    shutdown_timeout: float = 5.0
    health_check: Optional[Callable[[], bool]] = None
    last_health_check: Optional[datetime] = None
    stop_callback: Optional[Callable[[], None]] = None


class ThreadManager:
    """Centralized manager for all application threads.

    Provides thread lifecycle management, graceful shutdown, and health monitoring.
    """

    def __init__(self):
        """Initialize thread manager."""
        self._threads: Dict[str, ThreadInfo] = {}
        self._lock = threading.RLock()
        self._shutdown_event = threading.Event()
        self._shutdown_timeout = 10.0

    def register_thread(
        self,
        name: str,
        target: Callable,
        daemon: bool = True,
        shutdown_timeout: float = 5.0,
        health_check: Optional[Callable[[], bool]] = None,
        stop_callback: Optional[Callable[[], None]] = None,
        **kwargs,
    ) -> threading.Thread:
        """Register and start a new thread.

        Args:
            name: Unique name for the thread
            target: Callable to run in the thread
            daemon: Whether thread is daemon
            shutdown_timeout: Timeout for graceful shutdown
            health_check: Optional function to check thread health
            stop_callback: Optional callable used to request cooperative shutdown
            **kwargs: Additional arguments passed to Thread constructor

        Returns:
            Created and started Thread instance

        Raises:
            ValueError: If thread name already exists
        """
        with self._lock:
            if self._shutdown_event.is_set() and all(
                not info.thread.is_alive() for info in self._threads.values()
            ):
                self._shutdown_event.clear()

            if name in self._threads:
                thread_info = self._threads[name]
                # If thread is stopped, remove it and allow re-registration
                if thread_info.status == ThreadStatus.STOPPED:
                    logger.debug(
                        f"Removing stopped thread '{name}' to allow re-registration"
                    )
                    del self._threads[name]
                else:
                    raise ValueError(
                        f"Thread '{name}' already registered and is {thread_info.status.value}"
                    )

            thread = threading.Thread(
                target=self._thread_wrapper,
                args=(name, target),
                daemon=daemon,
                name=name,
                **kwargs,
            )

            thread_info = ThreadInfo(
                name=name,
                thread=thread,
                target=target,
                daemon=daemon,
                shutdown_timeout=shutdown_timeout,
                health_check=health_check,
                stop_callback=stop_callback,
            )

            thread_info.status = ThreadStatus.RUNNING
            thread_info.started_at = datetime.now()
            self._threads[name] = thread_info
            thread.start()

            logger.debug(f"Thread '{name}' registered and started")
            return thread

    def _thread_wrapper(self, name: str, target: Callable) -> None:
        """Wrapper for thread execution with error handling.

        Wraps thread execution to provide error handling, status tracking,
        and automatic cleanup. Updates thread status and logs errors.

        Args:
            name: Thread name for tracking
            target: Target callable to execute in thread

        Note:
            This method is called internally by register_thread() and should
            not be called directly.
        """
        thread_info = self._threads.get(name)
        if not thread_info:
            return

        try:
            target()
        except Exception as e:
            logger.error(f"Thread '{name}' raised exception: {e}", exc_info=True)
            with self._lock:
                thread_info.status = ThreadStatus.ERROR
                thread_info.error = e
        finally:
            with self._lock:
                if thread_info.status != ThreadStatus.ERROR:
                    thread_info.status = ThreadStatus.STOPPED
                thread_info.stopped_at = datetime.now()
                logger.debug(
                    "Thread '%s' stopped with status %s",
                    name,
                    thread_info.status.value,
                )

    def stop_thread(self, name: str, timeout: Optional[float] = None) -> bool:
        """Stop a specific thread gracefully.

        Args:
            name: Thread name to stop
            timeout: Optional timeout override

        Returns:
            True if thread stopped successfully, False otherwise
        """
        with self._lock:
            thread_info = self._threads.get(name)
            if not thread_info:
                logger.warning(f"Thread '{name}' not found")
                return False

            if thread_info.status in (ThreadStatus.STOPPED, ThreadStatus.STOPPING):
                return thread_info.status == ThreadStatus.STOPPED

            thread_info.status = ThreadStatus.STOPPING
            timeout = (
                thread_info.shutdown_timeout if timeout is None else max(timeout, 0.0)
            )

        try:
            if thread_info.stop_callback is not None:
                thread_info.stop_callback()
            thread_info.thread.join(timeout=timeout)
            with self._lock:
                if thread_info.thread.is_alive():
                    logger.warning(f"Thread '{name}' did not stop within timeout")
                    return False
                thread_info.status = ThreadStatus.STOPPED
                thread_info.stopped_at = datetime.now()
                logger.debug(f"Thread '{name}' stopped successfully")
                return True
        except Exception as e:
            logger.error(f"Error stopping thread '{name}': {e}", exc_info=True)
            return False

    def stop_all(self, timeout: Optional[float] = None) -> Dict[str, bool]:
        """Stop all registered threads gracefully.

        Args:
            timeout: Optional timeout override

        Returns:
            Dictionary mapping thread names to stop success status
        """
        self._shutdown_event.set()
        timeout = self._shutdown_timeout if timeout is None else max(timeout, 0.0)

        results: Dict[str, bool] = {}
        thread_names = list(self._threads.keys())
        if not thread_names:
            return results

        per_thread_timeout = timeout / len(thread_names)
        for name in thread_names:
            results[name] = self.stop_thread(name, timeout=per_thread_timeout)

        return results

    def get_thread(self, name: str) -> Optional[threading.Thread]:
        """Get thread instance by name.

        Args:
            name: Thread name

        Returns:
            Thread instance or None if not found
        """
        with self._lock:
            thread_info = self._threads.get(name)
            return thread_info.thread if thread_info else None

    def get_thread_info(self, name: str) -> Optional[ThreadInfo]:
        """Get thread information by name.

        Args:
            name: Thread name

        Returns:
            ThreadInfo or None if not found
        """
        with self._lock:
            return self._threads.get(name)

    def list_threads(self) -> List[str]:
        """List all registered thread names.

        Returns:
            List of thread names
        """
        with self._lock:
            return list(self._threads.keys())

    def get_thread_status(self, name: str) -> Optional[ThreadStatus]:
        """Get current status of a thread.

        Retrieves the current ThreadStatus (PENDING, RUNNING, STOPPING, STOPPED, ERROR)
        for the specified thread.

        Args:
            name: Thread name to query

        Returns:
            ThreadStatus if thread exists, None otherwise

        Example:
            >>> status = thread_manager.get_thread_status("worker_thread")
            >>> if status == ThreadStatus.RUNNING:
            ...     print("Thread is running")
        """
        with self._lock:
            thread_info = self._threads.get(name)
            return thread_info.status if thread_info else None

    def is_thread_alive(self, name: str) -> bool:
        """Check if a thread is currently alive.

        Verifies both that the thread is registered and that it is currently
        executing (not stopped).

        Args:
            name: Thread name to check

        Returns:
            True if thread exists and is alive, False otherwise

        Example:
            >>> if thread_manager.is_thread_alive("worker_thread"):
            ...     print("Worker is still running")
        """
        with self._lock:
            thread_info = self._threads.get(name)
            if not thread_info:
                return False
            return thread_info.thread.is_alive()

    def check_thread_health(self, name: str) -> Optional[bool]:
        """Check health of a thread using its health check function.

        Executes the optional health check function registered with the thread
        and updates the last health check timestamp.

        Args:
            name: Thread name to check

        Returns:
            True if healthy, False if unhealthy, None if no health check available

        Note:
            Health checks should be fast and non-blocking. If a health check
            raises an exception, it is logged and False is returned.

        Example:
            >>> health = thread_manager.check_thread_health("worker_thread")
            >>> if health is False:
            ...     print("Worker is unhealthy")
        """
        with self._lock:
            thread_info = self._threads.get(name)
            if not thread_info or not thread_info.health_check:
                return None

            try:
                result = thread_info.health_check()
                thread_info.last_health_check = datetime.now()
                return result
            except Exception as e:
                logger.error(f"Health check failed for thread '{name}': {e}")
                return False

    def check_all_health(self) -> Dict[str, Optional[bool]]:
        """Check health of all threads that have health checks.

        Iterates through all registered threads and executes their health
        check functions if available.

        Returns:
            Dictionary mapping thread names to health status (True/False/None)

        Example:
            >>> health_status = thread_manager.check_all_health()
            >>> unhealthy = [name for name, status in health_status.items() if status is False]
        """
        results = {}
        with self._lock:
            for name, thread_info in self._threads.items():
                if thread_info.health_check:
                    results[name] = self.check_thread_health(name)
        return results

    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive statistics about all managed threads.

        Calculates and returns statistics including total threads, running/stopped
        counts, uptime, and health status.

        Returns:
            Dictionary containing:
                - total_threads: Total number of registered threads
                - running_threads: Number of currently running threads
                - stopped_threads: Number of stopped threads
                - threads_by_status: Dict mapping status to count
                - average_uptime: Average uptime in seconds
                - health_status: Dict mapping thread names to health

        Example:
            >>> stats = thread_manager.get_stats()
            >>> print(f"Total threads: {stats['total_threads']}")
            >>> print(f"Running: {stats['running_threads']}")
        """
        with self._lock:
            stats = {
                "total_threads": len(self._threads),
                "running": sum(
                    1
                    for t in self._threads.values()
                    if t.status == ThreadStatus.RUNNING
                ),
                "stopped": sum(
                    1
                    for t in self._threads.values()
                    if t.status == ThreadStatus.STOPPED
                ),
                "error": sum(
                    1 for t in self._threads.values() if t.status == ThreadStatus.ERROR
                ),
                "threads": {
                    name: {
                        "status": info.status.value,
                        "daemon": info.daemon,
                        "alive": info.thread.is_alive(),
                        "created_at": info.created_at.isoformat(),
                        "started_at": info.started_at.isoformat()
                        if info.started_at
                        else None,
                        "stopped_at": info.stopped_at.isoformat()
                        if info.stopped_at
                        else None,
                    }
                    for name, info in self._threads.items()
                },
            }
            return stats

    @property
    def shutdown_event(self) -> threading.Event:
        """Get shutdown event for threads to check.

        Returns:
            Shutdown event
        """
        return self._shutdown_event

    def wait_for_shutdown(self, timeout: Optional[float] = None) -> bool:
        """Wait for shutdown event to be set.

        Blocks until the shutdown event is set or timeout expires.
        Useful for threads waiting for shutdown signal.

        Args:
            timeout: Optional timeout in seconds (None = wait indefinitely)

        Returns:
            True if shutdown event was set, False if timeout expired

        Example:
            >>> if thread_manager.wait_for_shutdown(timeout=5.0):
            ...     print("Shutdown signal received")
            ... else:
            ...     print("Timeout waiting for shutdown")
        """
        return self._shutdown_event.wait(timeout=timeout)


_thread_manager: Optional[ThreadManager] = None
_manager_lock = threading.Lock()


def get_thread_manager() -> ThreadManager:
    """Get global thread manager singleton.

    Returns:
        ThreadManager instance
    """
    global _thread_manager
    if _thread_manager is None:
        with _manager_lock:
            if _thread_manager is None:
                _thread_manager = ThreadManager()
    return _thread_manager
