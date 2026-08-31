"""
Tests for OpsWorker in isolation.

This module tests the OpsWorker class by mocking its complex dependencies
to ensure the worker's orchestration logic is correct without relying on
external services, Docker, or Git.
"""

import queue
from unittest.mock import MagicMock, patch

import pytest

from aura_cli.cli.workers.ops_worker import OpsWorker


class TestOpsWorkerIsolated:
    """Test suite for OpsWorker in isolation."""

    @pytest.fixture
    def mock_dependencies(self):
        """Mock all complex dependencies."""
        # Mocking the classes where they are defined, which patches them everywhere
        with patch("aura_cli.core.agi.planning.AgiPlanner") as mock_planner_cls:
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
                            # OpsWorker imports from aura_cli.core.agents, so we patch there or the factory
                            with patch(
                                "aura_cli.core.agents.AgentBackendFactory"
                            ) as mock_backend_factory:
                                with patch(
                                    "aura_cli.core.llm.tool_schemas.create_llm_config_with_tools"
                                ) as mock_llm_config:
                                    # Setup AgentBackendFactory to return a mock backend
                                    mock_backend = MagicMock()
                                    mock_user_proxy = MagicMock()
                                    mock_assistant = MagicMock()
                                    mock_backend.create_user_proxy.return_value = (
                                        mock_user_proxy
                                    )
                                    mock_backend.create_assistant.return_value = (
                                        mock_assistant
                                    )
                                    mock_backend_factory.create.return_value = (
                                        mock_backend
                                    )

                                    yield {
                                        "planner": mock_planner_cls,
                                        "orchestrator": mock_orch_cls,
                                        "communication": mock_comm_cls,
                                        "workflow": mock_workflow_cls,
                                        "memory": mock_memory_cls,
                                        "backend_factory": mock_backend_factory,
                                        "backend": mock_backend,
                                        "user_proxy": mock_user_proxy,
                                        "assistant": mock_assistant,
                                        "llm_config": mock_llm_config,
                                    }

    def test_initialization(self, mock_dependencies):
        """Test OpsWorker initialization."""
        prompt = "Check docker status"
        model = "gemini/gemini-2.5-flash"
        api_keys = {"GOOGLE_API_KEY": "fake_key"}
        mode = "docker"

        worker = OpsWorker(
            prompt=prompt, model=model, api_keys=api_keys, mode=mode, headless=True
        )

        assert worker.prompt == prompt
        assert worker.model == model
        assert worker.mode == mode
        assert worker.api_keys == api_keys
        assert worker.headless is True
        assert isinstance(worker.status_queue, queue.Queue)
        assert isinstance(worker.result_queue, queue.Queue)

    def test_initialize_advanced_components(self, mock_dependencies):
        """Test initialization of advanced components."""
        worker = OpsWorker(
            prompt="Task",
            model="gemini",
            api_keys={},
            headless=True,
            use_advanced_features=True,
        )

        # Trigger initialization
        worker._initialize_advanced_components()

        # Check if components were instantiated
        assert worker.orchestrator is not None
        assert worker.communication_manager is not None
        assert worker.workflow_executor is not None
        assert worker.agent_memory is not None

        # Check specific calls
        mock_dependencies["orchestrator"].assert_called_once()
        mock_dependencies["communication"].assert_called_once()
        mock_dependencies["workflow"].assert_called_once()
        mock_dependencies["memory"].assert_called_once()

    def test_run_success_chat_flow(self, mock_dependencies):
        """Test successful execution using standard chat flow (no planner)."""
        worker = OpsWorker(
            prompt="List files",
            model="gemini",
            api_keys={"GOOGLE_API_KEY": "key"},
            headless=True,
            use_advanced_features=False,  # Force chat flow
        )

        # Run worker (in current thread)
        worker.run()

        # Verify LLM config creation
        mock_dependencies["llm_config"].assert_called_once()

        # Verify Agent creation
        mock_dependencies["backend_factory"].create.assert_called_once()
        mock_dependencies["backend"].create_assistant.assert_called_once()
        mock_dependencies["backend"].create_user_proxy.assert_called_once()

        # Verify chat initiation
        mock_dependencies["user_proxy"].initiate_chat.assert_called_once()

    def test_run_success_workflow_flow(self, mock_dependencies):
        """Test successful execution using workflow flow (with planner)."""
        worker = OpsWorker(
            prompt="Complex task",
            model="gemini",
            api_keys={"GOOGLE_API_KEY": "key"},
            headless=True,
            use_advanced_features=True,
        )

        # Setup planner to return a valid plan
        mock_plan = MagicMock()
        mock_plan.tasks = [MagicMock(), MagicMock()]  # 2 tasks trigger workflow
        # Make tasks look valid
        for task in mock_plan.tasks:
            task.parameters = {"path": "."}
            task.description = "Task desc"
            task.id = "task_1"

        mock_planner_instance = mock_dependencies["planner"].return_value
        mock_planner_instance.decompose_and_plan.return_value = mock_plan
        worker.planner = mock_planner_instance

        # Setup workflow executor result
        mock_workflow_exec = mock_dependencies["workflow"].return_value
        mock_workflow_exec.execute_workflow.return_value = {
            "status": "completed",
            "iterations": 1,
        }

        # Run worker
        worker.run()

        # Verify workflow execution
        mock_workflow_exec.execute_workflow.assert_called_once()

    def test_run_error_handling(self, mock_dependencies):
        """Test error handling during execution."""
        worker = OpsWorker(
            prompt="Task",
            model="gemini",
            api_keys={"GOOGLE_API_KEY": "key"},
            headless=True,
        )

        # Force error during LLM config creation
        mock_dependencies["llm_config"].side_effect = Exception("Config Error")

        # Run worker
        worker.run()

        # Verify result queue has error
        result = worker.result_queue.get(timeout=2.0)
        assert result["status"] == "error"
        assert "Config Error" in result["error"]
        assert worker.final_error is not None
        assert worker.final_error["status"] == "error"

    def test_record_final_result_tracks_snapshot(self, mock_dependencies):
        """Final result should carry snapshot path when available."""
        worker = OpsWorker(
            prompt="Task",
            model="gemini",
            api_keys={"GOOGLE_API_KEY": "key"},
            headless=True,
        )
        worker.last_snapshot_path = "/tmp/notebooks/page_002.txt"
        worker.agi_event_adapter = MagicMock()

        worker._record_final_result({"status": "completed", "mode": "general"})

        assert worker.final_result is not None
        assert worker.final_result["snapshot_path"] == "/tmp/notebooks/page_002.txt"
        worker.agi_event_adapter.complete_task.assert_called_once_with(
            True,
            result="worker finished",
            stats={"supervisor_state": "completed", "fallback_reason": None},
        )

    def test_record_final_error_classifies_fallback_reason(self, mock_dependencies):
        """Final Ops error should carry a stable fallback reason."""
        worker = OpsWorker(
            prompt="Task",
            model="gemini",
            api_keys={"GOOGLE_API_KEY": "key"},
            headless=True,
        )
        worker.agi_event_adapter = MagicMock()

        worker._record_final_error("Docker daemon unavailable on this machine")

        assert worker.final_error is not None
        assert worker.final_error["fallback_reason"] == "external_dependency"
        worker.agi_event_adapter.update_task.assert_called_once_with(
            "returned_to_chat",
            "Worker returned control to chat",
            details={
                "supervisor_state": "returned_to_chat",
                "fallback_reason": "external_dependency",
            },
        )
