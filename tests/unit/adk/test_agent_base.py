"""Unit tests for adk.agent — Agent base class, CompositeAgent, registry helpers."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, patch

from aura_cli.adk.agent import (
    Agent,
    AgentState,
    CompositeAgent,
    create_agent,
    get_agent_class,
    list_agents,
    register_agent,
)
from aura_cli.application.agents import AgentResponse

# ---------------------------------------------------------------------------
# Minimal concrete agent for testing
# ---------------------------------------------------------------------------


class _EchoAgent(Agent):
    name = "_echo_agent_test"
    description = "Echoes the task"

    async def execute(self, task: str, **kwargs) -> AgentResponse:
        self._set_state(AgentState.RUNNING)
        self._set_state(AgentState.COMPLETED)
        return AgentResponse(content=f"echo:{task}", success=True)


class _FailAgent(Agent):
    name = "_fail_agent_test"
    description = "Always fails"

    async def execute(self, task: str, **kwargs) -> AgentResponse:
        self._set_state(AgentState.ERROR)
        return AgentResponse(content="", success=False, error="deliberate failure")


# ---------------------------------------------------------------------------
# Agent lifecycle
# ---------------------------------------------------------------------------


def test_agent_initial_state_is_idle() -> None:
    agent = _EchoAgent()
    assert agent.state == AgentState.IDLE


def test_agent_repr_contains_name_and_state() -> None:
    agent = _EchoAgent()
    r = repr(agent)
    assert "_echo_agent_test" in r
    assert "idle" in r


def test_agent_initialize_sets_ready() -> None:
    agent = _EchoAgent()
    # Patch _load_tools to avoid tool catalog side-effects
    with patch.object(agent, "_load_tools", new=AsyncMock()):
        asyncio.run(agent.initialize())
    assert agent.state == AgentState.READY


def test_agent_shutdown_sets_terminated() -> None:
    agent = _EchoAgent()
    asyncio.run(agent.shutdown())
    assert agent.state == AgentState.TERMINATED


def test_agent_context_set_get_clear() -> None:
    agent = _EchoAgent()
    agent.set_context("key", "value")
    assert agent.get_context("key") == "value"
    agent.clear_context()
    assert agent.get_context("key") is None


def test_agent_get_context_default() -> None:
    agent = _EchoAgent()
    assert agent.get_context("missing", default=42) == 42


def test_agent_on_state_change_callback() -> None:
    agent = _EchoAgent()
    states: list[AgentState] = []
    agent.on_state_change(states.append)
    agent._set_state(AgentState.RUNNING)
    agent._set_state(AgentState.COMPLETED)
    assert states == [AgentState.RUNNING, AgentState.COMPLETED]


def test_agent_has_capability_false_by_default() -> None:
    from aura_cli.application.agents import AgentCapability

    agent = _EchoAgent()
    assert not agent.has_capability(AgentCapability.CODE_GENERATION)


def test_agent_think_returns_string() -> None:
    agent = _EchoAgent()
    result = asyncio.run(agent.think("something"))
    assert isinstance(result, str)
    assert len(result) > 0


def test_agent_plan_returns_list() -> None:
    agent = _EchoAgent()
    plan = asyncio.run(agent.plan("do something"))
    assert isinstance(plan, list)
    assert len(plan) >= 1


# ---------------------------------------------------------------------------
# Agent execute
# ---------------------------------------------------------------------------


def test_echo_agent_execute() -> None:
    agent = _EchoAgent()
    result = asyncio.run(agent.execute("hello"))
    assert result.success
    assert result.content == "echo:hello"


def test_fail_agent_execute() -> None:
    agent = _FailAgent()
    result = asyncio.run(agent.execute("anything"))
    assert not result.success
    assert result.error == "deliberate failure"


# ---------------------------------------------------------------------------
# register_agent / get_agent_class / create_agent / list_agents
# ---------------------------------------------------------------------------


def test_register_agent_makes_class_findable() -> None:
    @register_agent
    class _RegTest(Agent):
        name = "_reg_test_xyzzy"
        description = "Registered test agent"

        async def execute(self, task: str, **kwargs) -> AgentResponse:
            return AgentResponse(content=task, success=True)

    assert get_agent_class("_reg_test_xyzzy") is _RegTest
    assert "_reg_test_xyzzy" in list_agents()


def test_create_agent_returns_instance() -> None:
    @register_agent
    class _CreateTest(Agent):
        name = "_create_test_xyzzy"
        description = "Create test"

        async def execute(self, task: str, **kwargs) -> AgentResponse:
            return AgentResponse(content=task, success=True)

    instance = create_agent("_create_test_xyzzy")
    assert isinstance(instance, _CreateTest)


def test_create_agent_unknown_returns_none() -> None:
    assert create_agent("__definitely_not_registered__") is None


def test_get_agent_class_unknown_returns_none() -> None:
    assert get_agent_class("__nope__") is None


def test_list_agents_returns_list() -> None:
    names = list_agents()
    assert isinstance(names, list)


# ---------------------------------------------------------------------------
# CompositeAgent
# ---------------------------------------------------------------------------


def _make_echo(suffix: str) -> _EchoAgent:
    class _E(Agent):
        name = f"_echo_{suffix}"
        description = f"Echo {suffix}"

        async def execute(self, task: str, **kwargs) -> AgentResponse:
            self._set_state(AgentState.RUNNING)
            self._set_state(AgentState.COMPLETED)
            return AgentResponse(content=f"{suffix}:{task}", success=True)

    return _E()


def test_composite_agent_execute_succeeds_with_single_agent() -> None:
    echo = _make_echo("a")
    composite = CompositeAgent(agents=[echo])
    with (
        patch.object(echo, "_load_tools", new=AsyncMock()),
        patch.object(composite, "_load_tools", new=AsyncMock()),
    ):
        result = asyncio.run(composite.execute("my task"))
    assert result.success


def test_composite_agent_empty_agents_returns_failure() -> None:
    composite = CompositeAgent(agents=[])
    with patch.object(composite, "_load_tools", new=AsyncMock()):
        result = asyncio.run(composite.execute("task"))
    assert not result.success
    assert result.error


def test_composite_agent_get_agent_by_name() -> None:
    a = _make_echo("x")
    b = _make_echo("y")
    composite = CompositeAgent(agents=[a, b])
    assert composite.get_agent("_echo_x") is a
    assert composite.get_agent("_echo_y") is b
    assert composite.get_agent("__missing__") is None


def test_composite_agent_initialize_inits_sub_agents() -> None:
    a = _make_echo("p")
    composite = CompositeAgent(agents=[a])

    init_calls: list[str] = []

    original_init = a.initialize

    async def _track_init():
        init_calls.append(a.name)
        await original_init()

    a.initialize = _track_init  # type: ignore[method-assign]

    with patch.object(composite, "_load_tools", new=AsyncMock()):
        asyncio.run(composite.initialize())

    assert a.name in init_calls
