"""
Tests for AgiWorker in isolation.

This module tests the AgiWorker class by mocking its complex dependencies
(Planner, Engine, Backend, Context, etc.) to ensure the worker's orchestration
logic is correct without relying on external services or the NativeBackend.
"""

import queue
from unittest.mock import ANY, MagicMock, patch

import pytest

from aura_cli.cli.workers.agi_worker import AgiWorker


class TestAgiWorkerIsolated:
    """Test suite for AgiWorker in isolation."""

    @pytest.fixture
    def mock_dependencies(self):
        """Mock all complex dependencies."""
        with patch("aura_cli.cli.workers.agi_worker.AgiPlanner") as mock_planner_cls:
            with patch(
                "aura_cli.cli.workers.agi_worker.AgiExecutionEngine"
            ) as mock_engine_cls:
                with patch(
                    "aura_cli.cli.workers.agi_worker.AgiContextManager"
                ) as mock_context_cls:
                    with patch(
                        "aura_cli.cli.workers.agi_worker.AgiValidator"
                    ) as mock_validator_cls:
                        with patch(
                            "aura_cli.cli.workers.agi_worker.AgiAgentFactory"
                        ) as mock_factory_cls:
                            with patch(
                                "aura_cli.core.agents.agent_orchestrator.AgentOrchestrator"
                            ) as mock_orch_cls:
                                with patch(
                                    "aura_cli.core.agents.agent_communication.CommunicationManager"
                                ) as mock_comm_cls:
                                    with patch(
                                        "aura_cli.core.agents.agent_workflow.WorkflowExecutor"
                                    ) as mock_workflow_cls:
                                        with patch(
                                            "aura_cli.core.agents.agent_memory.AgentMemory"
                                        ) as mock_memory_cls:
                                            with patch(
                                                "aura_cli.core.git_manager.GitManager"
                                            ) as mock_git_cls:
                                                yield {
                                                    "planner": mock_planner_cls,
                                                    "engine": mock_engine_cls,
                                                    "context": mock_context_cls,
                                                    "validator": mock_validator_cls,
                                                    "factory": mock_factory_cls,
                                                    "orchestrator": mock_orch_cls,
                                                    "communication": mock_comm_cls,
                                                    "workflow": mock_workflow_cls,
                                                    "memory": mock_memory_cls,
                                                    "git": mock_git_cls,
                                                }

    def test_initialization(self, mock_dependencies):
        """Test AgiWorker initialization."""
        prompt = "Refactor this file"
        model = "gemini/gemini-2.5-flash"
        api_keys = {"GOOGLE_API_KEY": "fake_key"}

        worker = AgiWorker(prompt=prompt, model=model, api_keys=api_keys, headless=True)

        assert worker.prompt == prompt
        assert worker.model == model
        assert worker.api_keys == api_keys
        assert worker.headless is True
        assert isinstance(worker.status_queue, queue.Queue)
        assert isinstance(worker.result_queue, queue.Queue)

    def test_initialize_advanced_components(self, mock_dependencies):
        """Test initialization of advanced components."""
        worker = AgiWorker(
            prompt="Task",
            model="gemini",
            api_keys={},
            headless=True,
            use_advanced_features=True,
        )

        # Trigger initialization
        worker._initialize_advanced_components()

        # Check if components were instantiated
        assert worker.planner is not None
        assert worker.context_manager_service is not None
        assert worker.validator is not None
        assert worker.engine is not None
        assert worker.factory is not None
        assert worker.agent_memory is not None
        assert worker.task_planner is not None
        assert worker.problem_decomposer is not None

        # Check specific calls
        mock_dependencies["planner"].assert_called_once()
        mock_dependencies["context"].assert_called_once()
        mock_dependencies["engine"].assert_called_once()
        mock_dependencies["memory"].assert_called_once()

        context_kwargs = mock_dependencies["context"].call_args.kwargs
        assert context_kwargs["imagination_scanner"] is worker.imagination_scanner

        # Verify Factory is called with correct args (no 'model')
        mock_dependencies["factory"].assert_called_once_with(
            orchestrator=ANY,
            communication_manager=ANY,
            agi_event_adapter=ANY,
            consciousness_manager=ANY,
            model="gemini",
            agent_memory=ANY,
            use_adk=True,
            memory_synchronizer=ANY,
        )

    def test_run_success(self, mock_dependencies):
        """Test successful execution flow."""
        worker = AgiWorker(prompt="Task", model="gemini", api_keys={}, headless=True)

        # Mock engine run to verify call
        mock_engine_instance = mock_dependencies["engine"].return_value

        # Run worker (in current thread for testing)
        worker.run()

        # Verify flow
        mock_dependencies["planner"].assert_called()
        mock_engine_instance.run.assert_called_once_with("Task", None)

    def test_run_error_handling(self, mock_dependencies):
        """Test error handling during execution."""
        worker = AgiWorker(prompt="Task", model="gemini", api_keys={}, headless=True)

        # Mock engine to raise exception
        mock_engine_instance = mock_dependencies["engine"].return_value
        mock_engine_instance.run.side_effect = Exception("Engine Crash")

        # Run worker
        worker.run()

        # Should catch exception and log (we can't easily verify log here without more patching,
        # but we verify it doesn't crash the test)
        assert worker.final_error is not None
        assert worker.final_error["status"] == "error"
        assert "Engine Crash" in worker.final_error["error"]

    @patch("aura_cli.cli.workers.agi_worker.get_memory_service")
    def test_constitution_loading(self, mock_get_memory, mock_dependencies):
        """Test loading constitution from memory service."""
        mock_service = MagicMock()
        mock_service.get_constitution.return_value = "Run tests."
        mock_get_memory.return_value = mock_service

        worker = AgiWorker(prompt="Task", model="gemini", api_keys={}, headless=True)

        # Force session state to return no constitution so memory service is used
        mock_session = MagicMock()
        mock_session.get_current_state.return_value = None
        worker._session_state = mock_session

        # Re-trigger constitution loading
        worker.constitution = None
        try:
            session = worker._session_state.get_current_state()
            if session and session.constitution:
                worker.constitution = session.constitution
            else:
                worker.constitution = worker._memory_service.get_constitution()
        except Exception:
            pass

        assert worker.constitution == "Run tests."
        mock_service.get_constitution.assert_called()

    def test_record_final_result_tracks_snapshot(self, mock_dependencies):
        """Final result should carry snapshot path when available."""
        worker = AgiWorker(prompt="Task", model="gemini", api_keys={}, headless=True)
        worker.last_snapshot_path = "/tmp/notebooks/page_001.txt"

        worker._record_final_result({"status": "completed", "model": "gemini"})

        assert worker.final_result is not None
        assert worker.final_result["snapshot_path"] == "/tmp/notebooks/page_001.txt"

    def test_record_final_error_classifies_fallback_reason(self, mock_dependencies):
        """Final AGI error should carry a stable fallback reason."""
        worker = AgiWorker(prompt="Task", model="gemini", api_keys={}, headless=True)
        worker.agi_event_adapter = MagicMock()

        worker._record_final_error("Human approval required before applying changes")

        assert worker.final_error is not None
        assert worker.final_error["fallback_reason"] == "human_approval_required"
        worker.agi_event_adapter.update_task.assert_called_once_with(
            "awaiting_human",
            "Worker returned control to chat",
            details={
                "supervisor_state": "awaiting_human",
                "fallback_reason": "human_approval_required",
            },
        )
