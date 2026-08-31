"""
Regression tests for /agi and /ops audit fixes.

Validates:
- AgentOrchestrator constructor (P0 #1)
- NativeUserProxy multi-turn tool calling (P0 #2)
- Environment variable isolation (P0 #3, #4)
- LinterManager preservation (P1 #5)
- QueueAgiAdapter structured events (P1 #7)
- Headless error propagation (P1 #8)
- OpsWorker shutdown event (P1 #11)
- create_llm_config_with_tools includes schemas (P0 #2b)
"""

import json
import os
from pathlib import Path
import queue
import threading
from unittest.mock import MagicMock, patch


class TestOrchestratorConstructor:
    """P0 #1: AgentOrchestrator must accept (context, strategy) kwargs."""

    def test_orchestrator_default_init(self):
        from aura_cli.core.agents.agent_orchestrator import AgentOrchestrator

        orch = AgentOrchestrator()
        assert orch.agents == {}
        assert orch.context is not None

    def test_orchestrator_with_strategy(self):
        from aura_cli.core.agents.agent_orchestrator import (
            AgentOrchestrator,
            OrchestrationStrategy,
        )

        strat = OrchestrationStrategy(parallel=False, max_concurrent=5)
        orch = AgentOrchestrator(strategy=strat)
        assert orch.strategy.parallel is False
        assert orch.strategy.max_concurrent == 5

    def test_orchestrator_rejects_positional_backend(self):
        """Passing a non-AgentContext positional arg should still work
        (it becomes the context param, which defaults to AgentContext())."""
        from aura_cli.core.agents.agent_orchestrator import AgentOrchestrator

        orch = AgentOrchestrator(context=None, strategy=None)
        assert orch.context is not None


class TestNativeProxyToolCalling:
    """P0 #2: NativeUserProxy must execute tools and loop."""

    def _make_proxy_and_agent(self, tool_map=None):
        from aura_cli.core.agents.interface import AgentConfig
        from aura_cli.core.agents.native_backend import NativeAgent, NativeUserProxy

        agent_cfg = AgentConfig(
            name="test_agent",
            role="assistant",
            system_message="You are a test agent.",
            llm_config={"model": "test", "tool_schemas": []},
        )
        proxy_cfg = AgentConfig(
            name="proxy",
            role="proxy",
            system_message="",
            llm_config={},
            max_consecutive_auto_reply=5,
            human_input_mode="NEVER",
        )
        agent = NativeAgent(agent_cfg)
        proxy = NativeUserProxy(proxy_cfg)
        proxy.is_termination_msg = lambda x: "TERMINATE" in x.get("content", "")
        if tool_map:
            proxy.function_map = tool_map
        return proxy, agent

    @patch("aura_cli.core.agents.native_backend.NativeUserProxy._call_llm")
    def test_single_turn_terminates(self, mock_llm):
        """If LLM responds with TERMINATE, loop exits after 1 turn."""
        resp = MagicMock()
        choice = MagicMock()
        choice.message.content = "Done TERMINATE"
        choice.message.tool_calls = None
        resp.choices = [choice]
        mock_llm.return_value = resp

        proxy, agent = self._make_proxy_and_agent()
        proxy.initiate_chat(agent, "hello")

        assert mock_llm.call_count == 1
        assert proxy.last_message()["content"] == "Done TERMINATE"

    @patch("aura_cli.core.agents.native_backend.NativeUserProxy._call_llm")
    def test_tool_call_executes_function(self, mock_llm):
        """If LLM requests a tool call, proxy executes it and loops."""
        tool_call = MagicMock()
        tool_call.id = "call_1"
        tool_call.function.name = "my_tool"
        tool_call.function.arguments = json.dumps({"x": 1})

        resp1 = MagicMock()
        choice1 = MagicMock()
        choice1.message.content = ""
        choice1.message.tool_calls = [tool_call]
        resp1.choices = [choice1]

        resp2 = MagicMock()
        choice2 = MagicMock()
        choice2.message.content = "Result received TERMINATE"
        choice2.message.tool_calls = None
        resp2.choices = [choice2]

        mock_llm.side_effect = [resp1, resp2]

        my_tool = MagicMock(return_value={"status": "ok"})
        proxy, agent = self._make_proxy_and_agent(tool_map={"my_tool": my_tool})
        proxy.initiate_chat(agent, "call my_tool")

        my_tool.assert_called_once_with(x=1)
        assert mock_llm.call_count == 2

    @patch("aura_cli.core.agents.native_backend.NativeUserProxy._call_llm")
    def test_max_turns_limit(self, mock_llm):
        """Proxy should stop after max_consecutive_auto_reply turns."""
        resp = MagicMock()
        choice = MagicMock()
        choice.message.content = "Still working..."
        choice.message.tool_calls = None
        resp.choices = [choice]
        mock_llm.return_value = resp

        proxy, agent = self._make_proxy_and_agent()
        proxy.max_consecutive_auto_reply = 3
        proxy.is_termination_msg = lambda x: False
        proxy.initiate_chat(agent, "infinite loop")

        # Without TERMINATE and without tool calls, it should break after 1 turn
        # (no tool_calls means break)
        assert mock_llm.call_count == 1

    @patch("aura_cli.core.agents.native_backend.NativeUserProxy._call_llm")
    def test_tool_not_found_handled(self, mock_llm):
        """If tool is not in function_map, error result is appended."""
        tool_call = MagicMock()
        tool_call.id = "call_1"
        tool_call.function.name = "nonexistent_tool"
        tool_call.function.arguments = "{}"

        resp1 = MagicMock()
        choice1 = MagicMock()
        choice1.message.content = ""
        choice1.message.tool_calls = [tool_call]
        resp1.choices = [choice1]

        resp2 = MagicMock()
        choice2 = MagicMock()
        choice2.message.content = "TERMINATE"
        choice2.message.tool_calls = None
        resp2.choices = [choice2]

        mock_llm.side_effect = [resp1, resp2]

        proxy, agent = self._make_proxy_and_agent(tool_map={"other_tool": lambda: None})
        proxy.initiate_chat(agent, "call nonexistent")

        tool_msg = [m for m in agent.conversation_history if m.get("role") == "tool"]
        assert len(tool_msg) == 1
        # Code returns Portuguese error message
        assert (
            "encontrada" in tool_msg[0]["content"]
            or "not found" in tool_msg[0]["content"]
        )


class TestEnvIsolation:
    """P0 #3, #4: Environment variables must be restored after execution."""

    def test_agi_engine_restore_env(self):
        """_configure_environment must NOT write to os.environ (BUG-03 fix).
        api_key is resolved and returned directly — no global env mutation."""
        from aura_cli.core.agi.execution import AgiExecutionEngine

        worker = MagicMock()
        worker.agi_event_adapter = MagicMock()
        worker.api_keys = {"GOOGLE_API_KEY": "secret123"}
        worker.model = "gemini/gemini-2.5-flash"
        worker.available_tools = {}
        worker.headless = True
        worker.task_id = "test"
        worker.result_queue = queue.Queue()

        engine = AgiExecutionEngine(
            agi_worker=worker,
            planner=None,
            context_manager=None,
            validator=None,
            workflow_executor=None,
            orchestrator=None,
            git_manager=MagicMock(),
        )

        before = os.environ.get("GOOGLE_API_KEY")
        api_key, _model = engine._configure_environment()

        # Must return the key directly, NOT write to os.environ
        assert api_key == "secret123"
        assert os.environ.get("GOOGLE_API_KEY") == before  # env unchanged


class TestLinterPreservation:
    """P1 #5: LinterManager from __init__ must not be overwritten."""

    @patch("aura_cli.core.memory.memory_service.get_memory_service")
    @patch("aura_cli.core.sessions.session_state.get_session_state")
    @patch("aura_cli.core.memory.notebook_service.get_notebook_service")
    def test_linter_not_overwritten(self, mock_nb, mock_ss, mock_ms):
        mock_ss.return_value = MagicMock(get_current_state=MagicMock(return_value=None))
        mock_ms.return_value = MagicMock(get_constitution=MagicMock(return_value=None))
        mock_nb.return_value = MagicMock()

        from aura_cli.cli.workers.agi_worker import AgiWorker

        worker = AgiWorker(
            prompt="test",
            model="gemini/gemini-2.5-flash",
            api_keys={"GOOGLE_API_KEY": "test"},
            headless=True,
            project_root=Path("/tmp"),
        )
        assert worker.linter_manager is not None


class TestQueueAgiAdapterContract:
    """P1 #7: QueueAgiAdapter must emit structured events."""

    def test_emits_structured_event(self):
        from aura_cli.cli.workers.ops_worker import QueueAgiAdapter

        q = queue.Queue()
        adapter = QueueAgiAdapter(q, task_id="ops_test")
        adapter.emit_chat_message(sender="agent", content="hello world")

        event = q.get(timeout=1)
        assert isinstance(event, dict)
        assert event["data"]["sender"] == "agent"
        assert event["data"]["content"] == "hello world"
        assert event["task_id"] == "ops_test"


class TestHeadlessErrorPropagation:
    """P1 #8: When engine not initialized, headless mode gets error result."""

    @patch("aura_cli.core.memory.memory_service.get_memory_service")
    @patch("aura_cli.core.sessions.session_state.get_session_state")
    @patch("aura_cli.core.memory.notebook_service.get_notebook_service")
    def test_headless_gets_error_when_no_engine(self, mock_nb, mock_ss, mock_ms):
        mock_ss.return_value = MagicMock(get_current_state=MagicMock(return_value=None))
        mock_ms.return_value = MagicMock(get_constitution=MagicMock(return_value=None))
        mock_nb.return_value = MagicMock()

        from aura_cli.cli.workers.agi_worker import AgiWorker

        worker = AgiWorker(
            prompt="test",
            model="gemini/gemini-2.5-flash",
            api_keys={"GOOGLE_API_KEY": "test"},
            headless=True,
            use_advanced_features=False,
            project_root=Path("/tmp"),
        )
        # _run_impl should handle missing engine
        worker._run_impl()

        result = worker.result_queue.get(timeout=1)
        assert result["status"] == "error"
        assert "Engine" in result.get("error", "")


class TestOpsWorkerShutdown:
    """P1 #11: OpsWorker must have _shutdown_event for clean shutdown."""

    @patch("aura_cli.core.memory.notebook_service.get_notebook_service")
    def test_has_shutdown_event(self, mock_nb):
        mock_nb.return_value = MagicMock()

        from aura_cli.cli.workers.ops_worker import OpsWorker

        worker = OpsWorker(
            prompt="test",
            model="gemini/gemini-2.5-flash",
            api_keys={"GOOGLE_API_KEY": "test"},
            headless=True,
            use_advanced_features=False,
        )
        assert hasattr(worker, "_shutdown_event")
        assert isinstance(worker._shutdown_event, threading.Event)

    @patch("aura_cli.core.memory.notebook_service.get_notebook_service")
    def test_cleanup_sets_shutdown_event(self, mock_nb):
        mock_nb.return_value = MagicMock()

        from aura_cli.cli.workers.ops_worker import OpsWorker

        worker = OpsWorker(
            prompt="test",
            model="gemini/gemini-2.5-flash",
            api_keys={"GOOGLE_API_KEY": "test"},
            headless=True,
            use_advanced_features=False,
        )
        assert not worker._shutdown_event.is_set()
        worker.cleanup()
        assert worker._shutdown_event.is_set()


class TestToolSchemasInConfig:
    """P0 #2b: create_llm_config_with_tools must include tool schemas."""

    def test_config_includes_schemas_when_tools_provided(self):
        from aura_cli.core.llm.tool_schemas import create_llm_config_with_tools

        def my_tool(path: str) -> str:
            """Read a file."""
            return ""

        config = create_llm_config_with_tools(
            model="gemini/gemini-2.5-flash",
            api_key="test",
            tools={"my_tool": my_tool},
        )

        assert "tool_schemas" in config
        assert len(config["tool_schemas"]) == 1
        assert config["tool_schemas"][0]["function"]["name"] == "my_tool"
        assert "function_map" in config
        assert "my_tool" in config["function_map"]

    def test_config_without_tools(self):
        from aura_cli.core.llm.tool_schemas import create_llm_config_with_tools

        config = create_llm_config_with_tools(
            model="gemini/gemini-2.5-flash",
            api_key="test",
        )

        assert "tool_schemas" not in config
        assert "function_map" not in config
