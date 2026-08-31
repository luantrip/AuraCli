"""Comprehensive tests for AgiWorker.

Tests for AGI worker functionality including initialization, execution, and cleanup.
"""

import queue
from unittest.mock import MagicMock, patch

import pytest


class TestAgiWorkerInit:
    """Tests for AgiWorker initialization."""

    @pytest.fixture
    def worker_deps(self, tmp_path):
        """Create dependencies for AgiWorker."""
        return {
            "prompt": "Analyze the project structure",
            "model": "gpt-4",
            "api_keys": {"OPENAI_API_KEY": "test-key"},
            "headless": True,
            "status_queue": queue.Queue(),
            "available_tools": {},
            "project_root": tmp_path,
        }

    def test_agi_worker_creation(self, worker_deps):
        """Test AgiWorker can be created."""
        from aura_cli.cli.workers.agi_worker import AgiWorker

        with patch("aura_cli.cli.workers.agi_worker.get_memory_service"):
            with patch(
                "aura_cli.cli.workers.agi_worker.get_session_state"
            ) as mock_session:
                mock_session.return_value = MagicMock(
                    get_current_state=MagicMock(
                        return_value=MagicMock(constitution=None)
                    )
                )
                worker = AgiWorker(**worker_deps)

                assert worker.prompt == worker_deps["prompt"]
                assert worker.model == worker_deps["model"]
                assert worker.headless is True
                assert worker.daemon is True

    def test_agi_worker_with_constitution(self, worker_deps):
        """Test AgiWorker with constitution."""
        from aura_cli.cli.workers.agi_worker import AgiWorker

        worker_deps["constitution"] = "Always write tests"

        with patch("aura_cli.cli.workers.agi_worker.get_memory_service"):
            with patch(
                "aura_cli.cli.workers.agi_worker.get_session_state"
            ) as mock_session:
                mock_session.return_value = MagicMock(
                    get_current_state=MagicMock(
                        return_value=MagicMock(constitution="Always write tests")
                    )
                )
                worker = AgiWorker(**worker_deps)

                assert worker.constitution == "Always write tests"

    def test_agi_worker_task_id(self, worker_deps):
        """Test AgiWorker task_id is set."""
        from aura_cli.cli.workers.agi_worker import AgiWorker

        with patch("aura_cli.cli.workers.agi_worker.get_memory_service"):
            with patch(
                "aura_cli.cli.workers.agi_worker.get_session_state"
            ) as mock_session:
                mock_session.return_value = MagicMock(
                    get_current_state=MagicMock(
                        return_value=MagicMock(constitution=None)
                    )
                )
                worker = AgiWorker(**worker_deps, task_id="custom_task")

                assert worker.task_id == "custom_task"

    def test_agi_worker_default_task_id(self, worker_deps):
        """Test AgiWorker default task_id."""
        from aura_cli.cli.workers.agi_worker import AgiWorker

        with patch("aura_cli.cli.workers.agi_worker.get_memory_service"):
            with patch(
                "aura_cli.cli.workers.agi_worker.get_session_state"
            ) as mock_session:
                mock_session.return_value = MagicMock(
                    get_current_state=MagicMock(
                        return_value=MagicMock(constitution=None)
                    )
                )
                worker = AgiWorker(**worker_deps)

                assert worker.task_id == "global_agi_task"


class TestAgiWorkerMethods:
    """Tests for AgiWorker methods."""

    @pytest.fixture
    def worker(self, tmp_path):
        """Create AgiWorker instance."""
        from aura_cli.cli.workers.agi_worker import AgiWorker

        with patch("aura_cli.cli.workers.agi_worker.get_memory_service"):
            with patch(
                "aura_cli.cli.workers.agi_worker.get_session_state"
            ) as mock_session:
                mock_session.return_value = MagicMock(
                    get_current_state=MagicMock(
                        return_value=MagicMock(constitution=None)
                    )
                )
                return AgiWorker(
                    prompt="Test prompt",
                    model="gpt-4",
                    api_keys={},
                    headless=True,
                    status_queue=queue.Queue(),
                    project_root=tmp_path,
                )


    def test_get_result_timeout(self, worker):
        """Test get_result with timeout."""
        result = worker.get_result(timeout=0.1)

        assert result["status"] == "timeout"
        assert result["error_code"] == "worker_wait_timeout"

    def test_get_result_with_data(self, worker):
        """Test get_result when data is available."""
        worker.result_queue.put({"status": "completed", "data": "test"})

        result = worker.get_result(timeout=1.0)

        assert result["status"] == "completed"
        assert result["data"] == "test"


class TestAgiWorkerRun:
    """Tests for AgiWorker run method."""

    @pytest.fixture
    def worker_for_run(self, tmp_path):
        """Create AgiWorker for run tests."""
        from aura_cli.cli.workers.agi_worker import AgiWorker

        with patch("aura_cli.cli.workers.agi_worker.get_memory_service"):
            with patch(
                "aura_cli.cli.workers.agi_worker.get_session_state"
            ) as mock_session:
                mock_session.return_value = MagicMock(
                    get_current_state=MagicMock(
                        return_value=MagicMock(constitution=None)
                    )
                )
                return AgiWorker(
                    prompt="Test",
                    model="gpt-4",
                    api_keys={"OPENAI_API_KEY": "test"},
                    headless=True,
                    status_queue=queue.Queue(),
                    project_root=tmp_path,
                    use_advanced_features=False,
                )


            # Should not raise


class TestAgiEventAdapter:
    """Tests for AgiEventAdapter."""

    def test_event_adapter_creation(self):
        """Test AgiEventAdapter creation."""
        from aura_cli.application.agents.event_emitter import AgiEventAdapter

        status_queue = queue.Queue()
        adapter = AgiEventAdapter(status_queue, "test_task")

        assert adapter is not None
        # Adapter stores queue reference
        assert adapter.status_queue is status_queue

    def test_event_adapter_emit(self):
        """Test AgiEventAdapter emit_chat_message."""
        from aura_cli.application.agents.event_emitter import AgiEventAdapter

        status_queue = queue.Queue()
        adapter = AgiEventAdapter(status_queue, "test_task")

        adapter.emit_chat_message(sender="agent", content="Test message")

        # Message should be in queue
        assert not status_queue.empty()


class TestHumanInterventionAdapter:
    """Tests for HumanInterventionAdapter."""

    def test_adapter_creation(self):
        """Test HumanInterventionAdapter creation."""
        from aura_cli.core.tools.human_intervention_adapter import (
            HumanInterventionAdapter,
        )

        status_queue = queue.Queue()
        adapter = HumanInterventionAdapter(
            status_queue=status_queue, task_id="test_task", default_timeout=60
        )

        assert adapter is not None
        assert adapter.task_id == "test_task"


class TestWorkerFactory:
    """Tests for worker factory functions."""


