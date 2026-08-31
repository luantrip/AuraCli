from unittest.mock import Mock, patch

from aura_cli.cli.workers.base_worker import BaseWorker


class RecordingWorker(BaseWorker):
    def __init__(self, *, failure: Exception | None = None):
        super().__init__(task_id="recording")
        self.failure = failure
        self.events: list[str] = []

    def _run_impl(self) -> None:
        self.events.append("run")
        if self.failure:
            raise self.failure

    def _handle_run_exception(self, error: Exception) -> None:
        self.events.append(f"error:{error}")


@patch("aura_cli.core.tools.human_intervention_adapter.unregister_intervention_adapter")
@patch("aura_cli.core.stats.get_stats")
def test_base_worker_finalizes_success(mock_get_stats, mock_unregister) -> None:
    stats = Mock(skip_confirmations=True)
    mock_get_stats.return_value = stats
    worker = RecordingWorker()

    with patch.object(worker, "_start_watchdog") as start_watchdog:
        worker.run()

    start_watchdog.assert_called_once_with()
    assert worker.events == ["run"]
    assert stats.skip_confirmations is True
    assert worker.execution_policy.auto_confirm is True
    mock_unregister.assert_called_once_with("recording")


@patch("aura_cli.core.tools.human_intervention_adapter.unregister_intervention_adapter")
@patch("aura_cli.core.stats.get_stats")
def test_base_worker_translates_failure_then_finalizes(
    mock_get_stats, mock_unregister
) -> None:
    stats = Mock(skip_confirmations=True)
    mock_get_stats.return_value = stats
    worker = RecordingWorker(failure=RuntimeError("boom"))

    with patch.object(worker, "_start_watchdog"):
        worker.run()

    assert worker.events == ["run", "error:boom"]
    assert stats.skip_confirmations is True
    assert worker.execution_policy.allow_dangerous is False
    mock_unregister.assert_called_once_with("recording")


@patch("aura_cli.cli.utils.dashboard_helper.start_dashboard_thread")
def test_base_worker_starts_dashboard_with_concrete_prefix(start_dashboard) -> None:
    worker = RecordingWorker()
    worker.dashboard_prefix = "Aura Test"
    worker.orchestrator = Mock()
    worker.agi_event_adapter = Mock()
    worker.use_advanced_features = True

    worker._start_dashboard()

    assert start_dashboard.call_args.kwargs["worker"] is worker
    assert start_dashboard.call_args.kwargs["orchestrator"] is worker.orchestrator
    assert start_dashboard.call_args.kwargs["prefix"] == "Aura Test"
    assert start_dashboard.call_args.kwargs["task_id"] == "recording"


def test_base_worker_publishes_one_idempotent_terminal_outcome() -> None:
    worker = RecordingWorker()
    worker.headless = True

    first = worker._publish_terminal_result({"status": "completed", "result": "first"})
    second = worker._publish_terminal_result({"status": "error", "result": "late"})

    assert second is first
    assert first["outcome_version"] == 1
    assert first["terminal"] is True
    assert worker.result_queue.qsize() == 1
    assert worker.wait_terminal(timeout=0.01)["result"] == "first"


def test_base_worker_cancel_publishes_cancelled_outcome_once() -> None:
    worker = RecordingWorker()
    worker.headless = True
    worker.agi_event_adapter = Mock()

    worker.cancel("cancelled by user")
    worker.cancel("late cancellation")

    result = worker.wait_terminal(timeout=0.01)
    assert result["status"] == "cancelled"
    assert result["error_code"] == "worker_cancelled"
    assert result["cancel_reason"] == "cancelled by user"
    assert worker.result_queue.qsize() == 1
    worker.agi_event_adapter.cancel_task.assert_called_once_with("cancelled by user")


def test_base_worker_timeout_cancel_publishes_timeout_outcome() -> None:
    worker = RecordingWorker()
    worker.headless = True

    worker.cancel("timeout after 0.0s")

    result = worker.wait_terminal(timeout=0.01)
    assert result["status"] == "timeout"
    assert result["error_code"] == "worker_wait_timeout"
    assert result["cancel_reason"] == "timeout after 0.0s"
