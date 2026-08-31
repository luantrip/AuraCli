"""Base worker class for Aura CLI background threads.

Extracts shared infrastructure from AgiWorker and OpsWorker:
daemon flag, shutdown event, queues, throttled status updates,
get_result, and cleanup.
"""

import contextlib
import queue
import threading
import time
from typing import Any, Dict, Optional

from aura_cli.application.agents import StatusThrottle
from aura_cli.application.agents.snapshots import assess_snapshot_schedule
from aura_cli.application.agents.worker_lifecycle import normalize_worker_outcome
from aura_cli.application.tools.execution_policy import (
    TaskExecutionPolicy,
    execution_policy_context,
)
from aura_cli.core.logger import get_logger

_base_worker_logger = get_logger(__name__)


class BaseWorker(threading.Thread):
    """Base class for background worker threads."""

    # Default max execution time (seconds). Subclasses can override.
    max_execution_time: float = 600.0
    dashboard_prefix: str = "Aura Worker"

    # Status queue max size to prevent unbounded memory growth.
    _STATUS_QUEUE_MAX_SIZE = 500

    def __init__(
        self,
        *,
        status_queue: Optional[queue.Queue[Any]] = None,
        task_id: str = "base",
        headless: bool = False,
    ):
        super().__init__()
        self.daemon = True
        self._shutdown_event = threading.Event()
        self.result_queue: queue.Queue[Any] = queue.Queue()
        self.status_queue = status_queue or queue.Queue(
            maxsize=self._STATUS_QUEUE_MAX_SIZE
        )
        self.task_id = task_id
        self.headless = headless
        self._last_status_update = 0
        self._status_update_interval = 0.5
        self._status_throttle = StatusThrottle(interval=self._status_update_interval)
        self.agi_event_adapter: Any = None
        self._notebook_service: Any = None
        self._last_notebook_snapshot = 0
        self._notebook_snapshot_interval = 10
        self.last_snapshot_path: str | None = None

        self.dashboard_thread = None
        self.dashboard_active = False
        self._watchdog_thread: Optional[threading.Thread] = None
        self.started_at = time.time()
        self.finished_at: float | None = None
        self._terminal_result: Dict[str, Any] | None = None
        self._terminal_result_lock = threading.Lock()
        self.execution_policy = TaskExecutionPolicy(
            task_id=self.task_id,
            auto_confirm=True,
            allow_dangerous=False,
            confirm_writes=False,
        )

    def _publish_terminal_result(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Publish one normalized, idempotent terminal result."""
        payload = normalize_worker_outcome(
            result,
            task_id=self.task_id,
            started_at=self.started_at,
            finished_at=time.time(),
        )

        with self._terminal_result_lock:
            if self._terminal_result is not None:
                return self._terminal_result
            self._terminal_result = payload
            self.finished_at = payload["finished_at"]
            if self.headless:
                self.result_queue.put(payload)
            return payload

    def wait_terminal(self, timeout: float = 5.0) -> Dict[str, Any]:
        """Wait for a terminal result; return an explicit timeout envelope."""
        with self._terminal_result_lock:
            if self._terminal_result is not None:
                return dict(self._terminal_result)

        try:
            result = self.result_queue.get(timeout=min(max(timeout, 0.0), 300.0))
        except queue.Empty:
            return {
                "status": "timeout",
                "task_id": self.task_id,
                "error_code": "worker_wait_timeout",
                "message": "O worker não produziu resultado terminal dentro do prazo.",
                "finished_at": self.finished_at,
            }

        with self._terminal_result_lock:
            if self._terminal_result is None and isinstance(result, dict):
                self._terminal_result = dict(result)
                self.finished_at = result.get("finished_at", self.finished_at)
        return result

    def _throttled_status_update(self, message: str):
        """Send status update with throttling to avoid saturation."""
        current_time = time.time()
        self._status_throttle.interval = self._status_update_interval
        if self._status_throttle.allow(current_time):
            adapter = getattr(self, "agi_event_adapter", None)
            try:
                if adapter is not None:
                    adapter.emit_chat_message(sender="agent", content=message)
                else:
                    # Fallback: push raw message directly to status queue
                    self.status_queue.put_nowait(
                        {"type": "chat_message", "sender": "agent", "content": message}
                    )
            except queue.Full:
                # Drop oldest message to make room, then retry
                with contextlib.suppress(queue.Empty):
                    self.status_queue.get_nowait()
                try:
                    if adapter is not None:
                        adapter.emit_chat_message(sender="agent", content=message)
                    else:
                        self.status_queue.put_nowait(
                            {
                                "type": "chat_message",
                                "sender": "agent",
                                "content": message,
                            }
                        )
                except queue.Full:
                    pass  # Drop message if still full
            self._last_status_update = current_time  # type: ignore[assignment]

    def get_result(self, timeout: float = 5.0) -> Dict[str, Any]:
        """Return a terminal result or an explicit wait-timeout envelope."""
        return self.wait_terminal(timeout)

    def _start_dashboard(self) -> None:
        """Start the shared dashboard adapter with the concrete worker prefix."""
        from aura_cli.cli.utils.dashboard_helper import start_dashboard_thread

        start_dashboard_thread(
            worker=self,
            orchestrator=getattr(self, "orchestrator", None),
            message_callback=lambda message: self.agi_event_adapter.emit_chat_message(
                sender="agent", content=message
            ),
            logger=_base_worker_logger,
            prefix=self.dashboard_prefix,
            headless=self.headless,
            use_advanced_features=getattr(self, "use_advanced_features", False),
            task_id=self.task_id,
        )

    def _start_watchdog(self) -> None:
        """Start a watchdog timer thread that triggers shutdown after max_execution_time."""

        def _watchdog_target():
            if not self._shutdown_event.wait(timeout=self.max_execution_time):
                # Timeout elapsed without normal shutdown — trigger forced shutdown
                _base_worker_logger.warning(
                    f"Watchdog triggered for worker '{self.task_id}': "
                    f"exceeded max_execution_time of {self.max_execution_time}s. "
                    f"Setting shutdown event."
                )
                adapter = getattr(self, "agi_event_adapter", None)
                if adapter is not None:
                    try:
                        adapter.interrupt_task(
                            f"watchdog timeout after {self.max_execution_time:.1f}s",
                            resumable=True,
                        )
                    except Exception as error:
                        _base_worker_logger.warning(
                            "Could not notify watchdog interruption for worker '%s': %s",
                            self.task_id,
                            error,
                        )
                self.cancel(f"timeout after {self.max_execution_time:.1f}s")

        self._watchdog_thread = threading.Thread(
            target=_watchdog_target,
            name=f"watchdog-{self.task_id}",
            daemon=True,
        )
        self._watchdog_thread.start()

    def run(self) -> None:
        """Execute the concrete worker inside the shared safety lifecycle."""
        self._start_watchdog()
        try:
            with execution_policy_context(self.execution_policy):
                self._run_impl()
        except Exception as error:
            self._handle_run_exception(error)
        finally:
            if self.headless and self._terminal_result is None:
                self._publish_terminal_result(
                    {
                        "status": "error",
                        "error_code": "worker_no_terminal_result",
                        "error": "Worker encerrou sem resultado terminal.",
                    }
                )
            self._finalize_run()

    def _run_impl(self) -> None:
        """Execute worker-specific behavior inside the shared lifecycle."""
        raise NotImplementedError

    def _handle_run_exception(self, error: Exception) -> None:
        """Translate an unhandled worker exception at the concrete boundary."""
        raise error

    def _finalize_run(self) -> None:
        """Release the intervention registration without mutating session policy."""
        from aura_cli.core.tools.human_intervention_adapter import (
            unregister_intervention_adapter,
        )

        unregister_intervention_adapter(self.task_id)

    def cleanup(self) -> None:
        """Stop dashboard thread, watchdog, and clean up resources."""
        from aura_cli.core.logger import get_logger

        logger = get_logger(__name__)
        logger.info(f"Cleaning up worker (task_id: {self.task_id})")

        self._shutdown_event.set()

        # Watchdog thread will exit on its own since _shutdown_event is set
        if self._watchdog_thread and self._watchdog_thread.is_alive():
            self._watchdog_thread.join(timeout=2.0)

        if hasattr(self, "dashboard_active") and self.dashboard_active:
            self.dashboard_active = False
        if hasattr(self, "dashboard_thread") and self.dashboard_thread:
            from aura_cli.cli.utils.thread_manager import get_thread_manager

            thread_manager = get_thread_manager()
            thread_name = (
                self.dashboard_thread.name
                if hasattr(self.dashboard_thread, "name")
                else None
            )
            if thread_name:
                thread_manager.stop_thread(thread_name, timeout=2.0)

        logger.info(f"Cleanup complete (task_id: {self.task_id})")

    def cancel(self, reason: str = "cancelled by user") -> None:
        """Request cooperative cancellation and publish one terminal outcome."""
        with self._terminal_result_lock:
            if self._terminal_result is not None:
                return

        self._shutdown_event.set()
        adapter = getattr(self, "agi_event_adapter", None)
        if adapter is not None:
            try:
                adapter.cancel_task(reason)
            except Exception as error:
                _base_worker_logger.warning(
                    "Could not notify cancellation for worker '%s': %s",
                    self.task_id,
                    error,
                )

        reason_text = str(reason).strip()
        timed_out = reason_text.lower().startswith("timeout after")
        self._publish_terminal_result(
            {
                "status": "timeout" if timed_out else "cancelled",
                "error_code": "worker_wait_timeout"
                if timed_out
                else "worker_cancelled",
                "message": (
                    "A operação excedeu o prazo e recebeu solicitação de cancelamento."
                    if timed_out
                    else "A operação foi cancelada pelo usuário."
                ),
                "cancel_reason": reason_text,
            }
        )

    def _conversation_history(self) -> list[dict[str, Any]]:
        """Read the active conversation history from the concrete context adapter."""
        context_manager = getattr(self, "context_manager", None)
        history = getattr(context_manager, "conversation_history", [])
        return history if isinstance(history, list) else []

    def _create_notebook_snapshot(self) -> Optional[str]:
        """Persist an eligible history through the configured notebook adapter."""
        history = self._conversation_history()
        if len(history) < 2:
            return None

        from aura_cli.core.constants import COMPRESSION_THRESHOLD

        page_path = self._notebook_service.create_snapshot(
            history,
            use_cognitive_refinement=True,
            refinement_threshold_tokens=COMPRESSION_THRESHOLD * 20,
        )
        self.last_snapshot_path = str(page_path)
        adapter = getattr(self, "agi_event_adapter", None)
        if adapter is not None:
            adapter.checkpoint_created("notebook snapshot", self.last_snapshot_path)
        return self.last_snapshot_path

    def _save_worker_snapshot(self) -> None:
        """Translate a snapshot result at the concrete worker boundary."""
        raise NotImplementedError

    def _check_and_save_periodic_snapshot(self) -> None:
        """Save when the shared scheduling policy observes enough new messages."""
        try:
            history = self._conversation_history()
            schedule = assess_snapshot_schedule(
                message_count=len(history),
                last_snapshot_count=self._last_notebook_snapshot,
                interval=self._notebook_snapshot_interval,
            )
            if schedule.should_save:
                self._save_worker_snapshot()
                self._last_notebook_snapshot = schedule.message_count
        except Exception as error:
            _base_worker_logger.debug(
                "Failed to check periodic worker snapshot: %s", error
            )
