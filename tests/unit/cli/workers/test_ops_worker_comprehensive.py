"""Comprehensive tests for OpsWorker.

Tests for Ops worker functionality including initialization, execution, and cleanup.
"""

import queue
from types import SimpleNamespace
from unittest.mock import MagicMock, Mock, patch

import pytest


class TestOpsWorkerInit:
    """Tests for OpsWorker initialization."""

    @pytest.fixture
    def worker_deps(self, tmp_path):
        """Create dependencies for OpsWorker."""
        return {
            "prompt": "Check git status",
            "model": "gpt-4",
            "api_keys": {"OPENAI_API_KEY": "test-key"},
            "mode": "git",
            "headless": True,
            "status_queue": queue.Queue(),
            "ops_tools": {},
            "project_root": tmp_path,
        }

    def test_ops_worker_creation(self, worker_deps):
        """Test OpsWorker can be created."""
        from aura_cli.cli.workers.ops_worker import OpsWorker

        worker = OpsWorker(**worker_deps)

        assert worker.prompt == worker_deps["prompt"]
        assert worker.model == worker_deps["model"]
        assert worker.mode == "git"
        assert worker.headless is True
        assert worker.daemon is True

    def test_ops_worker_general_mode(self, worker_deps):
        """Test OpsWorker in general mode."""
        from aura_cli.cli.workers.ops_worker import OpsWorker

        worker_deps["mode"] = "general"
        worker = OpsWorker(**worker_deps)

        assert worker.mode == "general"

    def test_ops_worker_docker_mode(self, worker_deps):
        """Test OpsWorker in docker mode."""
        from aura_cli.cli.workers.ops_worker import OpsWorker

        worker_deps["mode"] = "docker"
        worker = OpsWorker(**worker_deps)

        assert worker.mode == "docker"

    def test_ops_worker_task_id_generation(self, worker_deps):
        """Test OpsWorker generates task_id."""
        from aura_cli.cli.workers.ops_worker import OpsWorker

        worker = OpsWorker(**worker_deps)

        assert worker.task_id.startswith("ops_git_")


class TestOpsWorkerMethods:
    """Tests for OpsWorker methods."""

    @pytest.fixture
    def worker(self, tmp_path):
        """Create OpsWorker instance."""
        from aura_cli.cli.workers.ops_worker import OpsWorker

        return OpsWorker(
            prompt="Test prompt",
            model="gpt-4",
            api_keys={},
            mode="general",
            headless=True,
            status_queue=queue.Queue(),
            project_root=tmp_path,
            use_advanced_features=False,
        )

    def test_throttled_status_update(self, worker):
        """Test throttled status update."""
        # First update should go through
        worker._throttled_status_update("Message 1")

        # Check message was added
        assert not worker.status_queue.empty()

    def test_get_result_timeout(self, worker):
        """Test get_result with timeout."""
        result = worker.get_result(timeout=0.1)

        assert result["status"] == "timeout"
        assert result["error_code"] == "worker_wait_timeout"

    def test_get_result_with_data(self, worker):
        """Test get_result when data is available."""
        worker.result_queue.put({"status": "completed", "mode": "general"})

        result = worker.get_result(timeout=1.0)

        assert result["status"] == "completed"
        assert result["mode"] == "general"

    @patch("litellm.drop_params", False)
    def test_resolve_api_key_applies_gemini_adapter_requirement(self, worker):
        """Credential lookup should apply LiteLLM's Gemini parameter policy."""
        import litellm

        worker.api_keys = {"GOOGLE_API_KEY": "secret"}

        assert worker._resolve_api_key("gemini") == "secret"
        assert litellm.drop_params is True

    def test_resolve_api_key_publishes_missing_provider_guidance(self, worker):
        """Missing credentials should be translated at the UI adapter boundary."""
        worker.agi_event_adapter = Mock()

        assert worker._resolve_api_key("nvidia") is None
        content = worker.agi_event_adapter.emit_chat_message.call_args.kwargs["content"]
        assert "NVIDIA_API_KEY não configurada" in content
        assert "/settings" in content

    def test_cleanup(self, worker):
        """Test worker cleanup."""
        worker.dashboard_active = True
        worker.dashboard_thread = None

        worker.cleanup()

        assert worker.dashboard_active is False

    def test_get_planning_prompt(self, worker):
        """Test get_planning_prompt returns string."""
        prompt = worker._get_planning_prompt()

        assert isinstance(prompt, str)
        assert "general" in prompt  # Mode should be in prompt

    def test_get_effective_prompt_uses_delegation_payload(self, worker):
        """Delegated Ops worker should expand its runtime prompt with structured payload."""
        worker.delegation_payload = {
            "source": "general_chat",
            "primary_request": "Check git status and summarize risks",
            "recent_chat_excerpt": "user: review auth\nassistant: checking status",
        }

        prompt = worker._get_effective_prompt()

        assert "[CHAT DELEGATION HANDOFF]" in prompt
        assert "primary_request: Check git status and summarize risks" in prompt
        assert "recent_chat_excerpt:" in prompt
        assert "Task to execute:" in prompt

    def test_planning_prompt_includes_delegation_payload(self, worker):
        """Planning prompt should expose delegation payload when present."""
        worker.delegation_payload = {
            "source": "general_chat",
            "primary_request": "Investigate docker issues",
        }

        planning_prompt = worker._get_planning_prompt()

        assert "CHAT DELEGATION PAYLOAD" in planning_prompt
        assert "primary_request: Investigate docker issues" in planning_prompt

    def test_select_agent_for_task_read_file(self, worker):
        """Test agent selection for read_file task."""
        task = MagicMock()
        task.parameters = {"type": "read_file"}
        task.description = "Read a file"

        agent = worker._select_agent_for_task(task)

        assert agent == "ops_code_agent"

    def test_select_agent_for_task_git(self, worker):
        """Test agent selection for git task."""
        task = MagicMock()
        task.parameters = {"type": "git_status"}
        task.description = "Check git status"

        agent = worker._select_agent_for_task(task)

        assert agent == "ops_code_agent"

    def test_internal_window_extracts_file_artifacts(self):
        """Internal window should classify generated/edited/analyzed files from tool-like messages."""
        from aura_cli.cli.ui.internal_window import InternalProcessingWindow

        window = InternalProcessingWindow(queue.Queue(), "Aura Ops")
        window.start()
        window.capture_message(
            "user_proxy",
            "ops_agent",
            {"content": 'calling write_file with {"path": "infra/docker-compose.yml"}'},
        )
        window.capture_message(
            "user_proxy",
            "ops_agent",
            {"content": 'calling edit_file with {"path": "src/app.py"}'},
        )
        window.capture_message(
            "user_proxy",
            "ops_agent",
            {"content": 'calling read_file with {"path": "README.md"}'},
        )

        summary = window.get_summary()

        assert "infra/docker-compose.yml" in summary["generated_files"]
        assert "src/app.py" in summary["edited_files"]
        assert "README.md" in summary["analyzed_files"]
        assert "src/app.py" in summary["files_touched"]

    def test_record_structured_task_artifacts(self, worker):
        """Ops worker should classify structured workflow task parameters."""
        worker._record_structured_task_artifacts(
            {"type": "write_file", "path": "infra/docker-compose.yml"}
        )
        worker._record_structured_task_artifacts(
            {"type": "edit_file", "path": "src/app.py"}
        )
        worker._record_structured_task_artifacts(
            {"type": "read_file", "path": "README.md"}
        )

        assert worker.generated_files == ["infra/docker-compose.yml"]
        assert worker.edited_files == ["src/app.py"]
        assert worker.analyzed_files == ["README.md"]

    def test_build_instrumented_ops_tools_records_real_tool_args(self, worker):
        """Ops tool wrappers should classify artifacts from real tool kwargs."""

        def fake_edit_file(path: str, old_content: str, new_content: str) -> str:
            return f"edited {path}"

        worker.ops_tools = {"edit_file": fake_edit_file}
        wrapped = worker._build_instrumented_ops_tools()
        result = wrapped["edit_file"](
            path="src/app.py", old_content="a", new_content="b"
        )

        assert result.startswith("edited src/app.py")
        assert "WORKSPACE DIFF" in result
        assert worker.edited_files == ["src/app.py"]

    @patch("aura_cli.cli.workers.ops_worker.SubAgentPanel", None)
    def test_build_ops_workflow_translates_application_blueprint(self, worker):
        """The adapter should preserve routed agents and task dependencies."""
        worker.orchestrator = SimpleNamespace(
            agents={"ops_code_agent": Mock(), "ops_git_agent": Mock()}
        )
        task_plan = SimpleNamespace(
            tasks=[
                SimpleNamespace(
                    id="inspect",
                    description="Inspect git status",
                    parameters={"type": "git_status"},
                    dependencies=[],
                ),
                SimpleNamespace(
                    id="read",
                    description="Read configuration",
                    parameters={"type": "read_file", "path": "config.toml"},
                    dependencies=["inspect"],
                ),
            ]
        )

        workflow, panel = worker._build_ops_workflow(task_plan)

        assert panel is None
        assert workflow.steps["inspect"].agent_id == "ops_git_agent"
        assert workflow.steps["read"].dependencies == ["inspect"]
        assert worker.analyzed_files == ["config.toml"]

    @patch("aura_cli.cli.workers.ops_worker.time.time", return_value=42.5)
    def test_agent_observer_persists_selected_discovery(self, _mock_time, worker):
        """The backend observer should persist Application-selected discoveries."""
        worker.agent_memory = Mock()
        internal_window = Mock()
        message = {
            "content": "Identifiquei um problema importante no health check " + "x" * 20
        }

        worker._observe_agent_message(
            message,
            "ops_specialist",
            "aura_ops",
            "receive",
            internal_window,
        )

        internal_window.capture_message.assert_called_once_with(
            "ops_specialist", "aura_ops", message
        )
        worker.agent_memory.store.assert_called_once_with(
            agent_id="aura_ops",
            key="discovery_42",
            value="Identifiquei um problema importante no health check " + "x" * 20,
            context={
                "sender": "ops_specialist",
                "mode": "general",
                "timestamp": 42.5,
            },
            ttl=3600,
        )


class TestOpsWorkerRun:
    """Tests for OpsWorker run method."""

    @pytest.fixture
    def worker_for_run(self, tmp_path):
        """Create OpsWorker for run tests."""
        from aura_cli.cli.workers.ops_worker import OpsWorker

        return OpsWorker(
            prompt="Test",
            model="gpt-4",
            api_keys={"OPENAI_API_KEY": "test"},
            mode="general",
            headless=True,
            status_queue=queue.Queue(),
            project_root=tmp_path,
            use_advanced_features=False,
        )

    def test_run_handles_exception(self, worker_for_run):
        """Test that run handles exceptions gracefully."""
        with patch.object(
            worker_for_run, "_run_impl", side_effect=Exception("Test error")
        ):
            # Should not raise
            worker_for_run.run()

    def test_run_puts_error_in_queue(self, worker_for_run):
        """Test that run puts error in result queue on exception."""
        with patch.object(
            worker_for_run, "_run_impl", side_effect=Exception("Test error")
        ):
            worker_for_run.run()

            # Error should be in result queue
            result = worker_for_run.get_result(timeout=0.1)
            assert result.get("status") == "error"


class TestQueueAgiAdapter:
    """Tests for QueueAgiAdapter."""

    def test_adapter_creation(self):
        """Test QueueAgiAdapter creation."""
        from aura_cli.cli.workers.ops_worker import QueueAgiAdapter

        q = queue.Queue()
        adapter = QueueAgiAdapter(q, task_id="test_ops")

        assert adapter.status_queue is q
        assert adapter.current_task_id == "test_ops"

    def test_adapter_emit(self):
        """Test QueueAgiAdapter emit_chat_message sends structured event."""
        from aura_cli.cli.workers.ops_worker import QueueAgiAdapter

        q = queue.Queue()
        adapter = QueueAgiAdapter(q, task_id="test_ops")

        adapter.emit_chat_message(sender="test", content="Hello")

        event = q.get(timeout=0.1)
        assert isinstance(event, dict)
        assert event["data"]["content"] == "Hello"
        assert event["data"]["sender"] == "test"


class TestOpsWorkerAdvancedFeatures:
    """Tests for OpsWorker advanced features."""

    @pytest.fixture
    def worker_advanced(self, tmp_path):
        """Create OpsWorker with advanced features."""
        from aura_cli.cli.workers.ops_worker import OpsWorker

        return OpsWorker(
            prompt="Analyze infrastructure",
            model="gpt-4",
            api_keys={},
            mode="general",
            headless=True,
            status_queue=queue.Queue(),
            project_root=tmp_path,
            use_advanced_features=True,
        )

    def test_has_task_planner(self, worker_advanced):
        """Test that advanced worker has task planner."""
        assert worker_advanced.task_planner is not None

    def test_has_problem_decomposer(self, worker_advanced):
        """Test that advanced worker has problem decomposer."""
        assert worker_advanced.problem_decomposer is not None

    def test_has_planner(self, worker_advanced):
        """Test that advanced worker has AgiPlanner."""
        assert worker_advanced.planner is not None

    def test_plan_with_llm_delegates(self, worker_advanced):
        """Test plan_with_llm uses planner directly."""
        with patch.object(worker_advanced.planner, "plan_with_llm") as mock_plan:
            mock_plan.return_value = None

            worker_advanced.planner.plan_with_llm("Test prompt")

            mock_plan.assert_called_once()

    def test_decompose_and_plan_uses_effective_prompt_when_delegated(
        self, worker_advanced
    ):
        """Delegated workers should plan from the expanded handoff prompt."""
        worker_advanced.delegation_payload = {
            "source": "general_chat",
            "primary_request": "Check git status",
        }
        with patch.object(
            worker_advanced.planner, "decompose_and_plan"
        ) as mock_decompose:
            mock_decompose.return_value = None

            worker_advanced._decompose_and_plan(worker_advanced.prompt)

            called_prompt = mock_decompose.call_args.args[0]
            assert "[CHAT DELEGATION HANDOFF]" in called_prompt
            assert "primary_request: Check git status" in called_prompt

    def test_decompose_and_plan_delegates(self, worker_advanced):
        """Test decompose_and_plan uses planner directly."""
        with patch.object(
            worker_advanced.planner, "decompose_and_plan"
        ) as mock_decompose:
            mock_decompose.return_value = None

            worker_advanced.planner.decompose_and_plan("Test prompt")

            mock_decompose.assert_called_once()
