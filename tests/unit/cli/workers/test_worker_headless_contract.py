"""Headless worker lifecycle and exit-code contract regressions."""

from pathlib import Path
import queue
import time
from unittest.mock import Mock

from aura_cli.cli.main import _worker_exit_code
from aura_cli.cli.workers.base_worker import BaseWorker
from aura_cli.cli.workers.ops_worker import OpsWorker


class NoopWorker(BaseWorker):
    """Minimal worker used to exercise the shared lifecycle contract."""

    def _run_impl(self) -> None:
        return


def test_wait_terminal_returns_explicit_timeout_envelope():
    worker = NoopWorker(task_id="noop-timeout", headless=True)

    result = worker.wait_terminal(timeout=0.01)

    assert result["status"] == "timeout"
    assert result["task_id"] == "noop-timeout"
    assert result["error_code"] == "worker_wait_timeout"
    second_result = worker.get_result(timeout=0.01)
    assert second_result["status"] == "timeout"
    assert second_result["error_code"] == "worker_wait_timeout"


def test_headless_worker_that_returns_without_result_is_not_silent():
    worker = NoopWorker(task_id="noop-empty", headless=True)

    worker.run()
    result = worker.wait_terminal(timeout=0.1)

    assert result["status"] == "error"
    assert result["error_code"] == "worker_no_terminal_result"
    assert result["task_id"] == "noop-empty"


def test_watchdog_publishes_timeout_even_when_interrupt_notification_fails():
    worker = NoopWorker(task_id="watchdog-timeout", headless=True)
    worker.max_execution_time = 0.01
    worker.agi_event_adapter = Mock()
    worker.agi_event_adapter.interrupt_task.side_effect = RuntimeError("adapter down")

    worker._start_watchdog()
    time.sleep(0.05)

    result = worker.wait_terminal(timeout=0.1)
    assert result["status"] == "timeout"
    assert result["error_code"] == "worker_wait_timeout"
    worker.agi_event_adapter.interrupt_task.assert_called_once()
    worker.agi_event_adapter.cancel_task.assert_called_once()


def test_ops_missing_credential_publishes_terminal_configuration_error(tmp_path: Path):
    worker = OpsWorker(
        prompt="inspect status",
        model="gpt-4",
        api_keys={},
        mode="general",
        headless=True,
        status_queue=queue.Queue(),
        project_root=tmp_path,
        use_advanced_features=False,
    )

    worker._run_impl()
    result = worker.wait_terminal(timeout=0.1)

    assert result["status"] == "error"
    assert result["error_code"] == "configuration"
    assert worker.final_error is not None
    assert worker.final_error["error_code"] == "configuration"


def test_worker_exit_codes_are_stable():
    assert _worker_exit_code({"status": "completed"}) == 0
    assert _worker_exit_code({"status": "error", "error_code": "configuration"}) == 3
    assert _worker_exit_code({"status": "timeout"}) == 5
    assert _worker_exit_code({"status": "cancelled"}) == 6
    assert _worker_exit_code({"status": "error", "error_code": "dependency"}) == 7
