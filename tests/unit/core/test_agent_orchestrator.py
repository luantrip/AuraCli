"""Testes para core/agents/agent_orchestrator.py — TEST-NEW-01."""

from unittest.mock import MagicMock

from aura_cli.core.agents.agent_base import AgentContext, AgentStatus
from aura_cli.core.agents.agent_orchestrator import (
    AgentOrchestrator,
    OrchestrationStrategy,
)


def _make_mock_agent(agent_id="agent-1", agent_type="test"):
    agent = MagicMock()
    agent.agent_id = agent_id
    agent.agent_type = agent_type
    agent.name = agent_id
    agent.status = AgentStatus.IDLE
    agent.is_available.return_value = True
    # config for agent_id resolution
    agent.config = MagicMock()
    agent.config.name = agent_id
    return agent


class TestOrchestrationStrategy:
    def test_default_values(self):
        s = OrchestrationStrategy()
        assert s.max_concurrent >= 1
        assert isinstance(s.parallel, bool)

    def test_custom_max_concurrent(self):
        s = OrchestrationStrategy(max_concurrent=5)
        assert s.max_concurrent == 5

    def test_parallel_default_true(self):
        s = OrchestrationStrategy()
        assert s.parallel is True


class TestAgentOrchestratorInit:
    def test_default_init(self):
        orch = AgentOrchestrator()
        assert orch.agents == {}
        assert orch.running is False

    def test_custom_context(self):
        ctx = AgentContext()
        orch = AgentOrchestrator(context=ctx)
        assert orch.context is ctx

    def test_custom_strategy(self):
        strat = OrchestrationStrategy(max_concurrent=3)
        orch = AgentOrchestrator(strategy=strat)
        assert orch.strategy.max_concurrent == 3

    def test_initial_stats_zero(self):
        orch = AgentOrchestrator()
        assert orch.total_tasks_distributed == 0
        assert orch.total_tasks_completed == 0


class TestRegisterUnregister:
    def test_register_agent(self):
        orch = AgentOrchestrator()
        agent = _make_mock_agent("a1", "code")
        orch.register_agent(agent)
        assert "a1" in orch.agents

    def test_register_duplicate_replaces(self):
        orch = AgentOrchestrator()
        agent1 = _make_mock_agent("a1")
        agent2 = _make_mock_agent("a1")
        orch.register_agent(agent1)
        orch.register_agent(agent2)
        assert orch.agents["a1"] is agent2

    def test_unregister_agent(self):
        orch = AgentOrchestrator()
        agent = _make_mock_agent("a1")
        orch.register_agent(agent)
        orch.unregister_agent("a1")
        assert "a1" not in orch.agents

    def test_unregister_nonexistent_no_crash(self):
        orch = AgentOrchestrator()
        orch.unregister_agent("nonexistent")  # should not raise

    def test_get_agent(self):
        orch = AgentOrchestrator()
        agent = _make_mock_agent("a1")
        orch.register_agent(agent)
        assert orch.get_agent("a1") is agent

    def test_get_agent_missing_returns_none(self):
        orch = AgentOrchestrator()
        assert orch.get_agent("missing") is None

    def test_get_agents_by_type(self):
        orch = AgentOrchestrator()
        # agent_type is determined by __class__.__name__, so use same class
        a1 = _make_mock_agent("a1")
        a2 = _make_mock_agent("a2")
        orch.register_agent(a1)
        orch.register_agent(a2)
        # Both are MagicMock, so type is "MagicMock"
        agents = orch.get_agents_by_type("MagicMock")
        assert len(agents) == 2

    def test_get_agents_by_type_empty(self):
        orch = AgentOrchestrator()
        assert orch.get_agents_by_type("nonexistent") == []


class TestGetStatus:
    def test_status_returns_dict(self):
        orch = AgentOrchestrator()
        status = orch.get_status()
        assert isinstance(status, dict)

    def test_status_has_running_key(self):
        orch = AgentOrchestrator()
        status = orch.get_status()
        assert "running" in status or "status" in status or "total_agents" in status


class TestResetAll:
    def test_reset_calls_agent_reset(self):
        orch = AgentOrchestrator()
        agent = _make_mock_agent("a1")
        orch.register_agent(agent)
        orch.reset_all()
        agent.reset.assert_called_once()

    def test_reset_clears_stats(self):
        orch = AgentOrchestrator()
        orch.total_tasks_distributed = 5
        orch.total_tasks_completed = 3
        orch.reset_all()
        assert orch.total_tasks_distributed == 0
        assert orch.total_tasks_completed == 0
