"""Workflow fallback and reconciliation contracts for OpsWorker."""

from types import SimpleNamespace
from unittest.mock import MagicMock

from aura_cli.application.agents.workflow import WorkflowState
from aura_cli.cli.workers.ops_worker import OpsWorker


def make_worker(tmp_path):
    worker = OpsWorker(
        prompt="apply change",
        model="offline-test",
        api_keys={},
        mode="general",
        headless=True,
        project_root=tmp_path,
        use_advanced_features=False,
    )
    worker.agi_event_adapter = MagicMock()
    worker.workflow_executor = MagicMock()
    worker._save_worker_snapshot = MagicMock()
    return worker


def test_workflow_error_before_dispatch_keeps_chat_fallback(tmp_path):
    worker = make_worker(tmp_path)
    workflow = SimpleNamespace(
        workflow_id="wf-before",
        status=WorkflowState.PENDING,
        steps={
            "step-1": SimpleNamespace(
                status=WorkflowState.PENDING,
                task_id=None,
                attempts=0,
                error=None,
            )
        },
        results={},
    )
    worker._build_ops_workflow = MagicMock(return_value=(workflow, None))
    worker.workflow_executor.execute_workflow.side_effect = RuntimeError(
        "planning failed"
    )

    assert worker._execute_workflow_path(SimpleNamespace(), None) is False
    worker.agi_event_adapter.emit_chat_message.assert_called_once()
    assert (
        "execução padrão"
        in worker.agi_event_adapter.emit_chat_message.call_args.kwargs["content"]
    )
    worker._save_worker_snapshot.assert_not_called()


def test_workflow_error_after_dispatch_requires_reconciliation(tmp_path):
    worker = make_worker(tmp_path)
    workflow = SimpleNamespace(
        workflow_id="wf-after",
        status=WorkflowState.RUNNING,
        steps={
            "step-1": SimpleNamespace(
                status=WorkflowState.RUNNING,
                task_id="delegated-1",
                attempts=1,
                error=None,
            )
        },
        results={},
    )
    worker._build_ops_workflow = MagicMock(return_value=(workflow, None))
    worker.workflow_executor.execute_workflow.side_effect = RuntimeError(
        "executor lost connection"
    )

    assert worker._execute_workflow_path(SimpleNamespace(), None) is True
    assert worker.final_error is not None
    assert worker.final_error["status"] == "error"
    assert worker.final_error["error_code"] == "workflow_effect_uncertain"
    assert worker.final_error["retryability"] == "reconcile_before_retry"
    assert (
        worker.final_error["workflow_result"]["steps_results"]["step-1"]["task_id"]
        == "delegated-1"
    )
    worker.agi_event_adapter.update_task.assert_called_once()
    assert worker.agi_event_adapter.update_task.call_args.args[0] == (
        "reconciliation_required"
    )
    worker._save_worker_snapshot.assert_called_once()
