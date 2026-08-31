"""Scenario tests for worker fallback/handoff payload propagation."""

from pathlib import Path
from unittest.mock import MagicMock, patch

from aura_cli.cli.workers.agi_worker import AgiWorker
from aura_cli.cli.workers.ops_worker import OpsWorker


class TestWorkerHandoffScenarios:
    """Ensures delegated context survives success/error boundaries."""

    @patch("aura_cli.cli.workers.agi_worker.get_memory_service")
    @patch("aura_cli.cli.workers.agi_worker.get_session_state")
    def test_agi_record_final_error_keeps_delegation_payload(
        self, mock_session_state, mock_memory_service
    ):
        """AGI errors should retain handoff metadata."""
        mock_memory_service.return_value = MagicMock()
        mock_session_state.return_value = MagicMock(
            get_current_state=MagicMock(return_value=MagicMock(constitution=None))
        )
        payload = {"source": "chat", "primary_request": "investigate auth bug"}
        worker = AgiWorker(
            prompt="Investigate issue",
            model="auto",
            api_keys={},
            headless=True,
            project_root=Path.cwd(),
            delegation_payload=payload,
        )

        worker._record_final_error("Human approval required for deployment")

        assert worker.final_error is not None
        assert worker.final_error["delegation_payload"] == payload
        assert worker.final_error["fallback_reason"] == "human_approval_required"

    def test_ops_record_final_result_keeps_delegation_payload(self):
        """Ops success results should keep structured handoff payload."""
        payload = {"source": "chat", "primary_request": "check docker health"}
        worker = OpsWorker(
            prompt="Check docker",
            model="auto",
            api_keys={},
            mode="docker",
            headless=True,
            use_advanced_features=False,
            project_root=Path.cwd(),
            delegation_payload=payload,
        )

        worker._record_final_result({"status": "completed", "mode": "docker"})

        assert worker.final_result is not None
        assert worker.final_result["delegation_payload"] == payload
        assert worker.final_result["fallback_reason"] is None
