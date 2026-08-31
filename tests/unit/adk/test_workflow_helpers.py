"""Unit tests for adk.workflow — create_workflow helper and WorkflowBuilder API."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, patch

from aura_cli.adk.agent import Agent, AgentState
from aura_cli.adk.workflow import (
    StepState,
    Workflow,
    WorkflowBuilder,
    WorkflowState,
    create_workflow,
)
from aura_cli.application.agents import AgentResponse

# ---------------------------------------------------------------------------
# Minimal Agent subclasses for testing.
# Workflow.run() calls step.agent.execute(task) — requires objects with
# .execute(), not bare callables.
# ---------------------------------------------------------------------------


class _OkAgent(Agent):
    """Succeeds and echoes its task."""

    name = "_ok_agent_wf_test"
    description = "OK agent for workflow tests"

    async def execute(self, task: str, **kwargs) -> AgentResponse:
        self._set_state(AgentState.RUNNING)
        self._set_state(AgentState.COMPLETED)
        return AgentResponse(content=f"done:{task}", success=True)


def _ok() -> _OkAgent:
    return _OkAgent()


# ---------------------------------------------------------------------------
# create_workflow helper
# ---------------------------------------------------------------------------


def test_create_workflow_returns_workflow_instance() -> None:
    wf = create_workflow(
        name="test-wf",
        steps=[{"id": "s1", "name": "Step 1", "fn": _ok()}],
    )
    assert isinstance(wf, Workflow)


def test_create_workflow_name_preserved() -> None:
    wf = create_workflow(
        name="my-pipeline",
        steps=[{"id": "s1", "name": "S1", "fn": _ok()}],
    )
    assert wf.name == "my-pipeline"


def test_create_workflow_description_preserved() -> None:
    wf = create_workflow(
        name="wf",
        steps=[{"id": "s1", "name": "S1", "fn": _ok()}],
        description="A pipeline",
    )
    assert wf.description == "A pipeline"


def test_create_workflow_multiple_steps() -> None:
    wf = create_workflow(
        name="multi",
        steps=[
            {"id": "a", "name": "A", "fn": _ok()},
            {"id": "b", "name": "B", "fn": _ok(), "dependencies": ["a"]},
            {"id": "c", "name": "C", "fn": _ok(), "dependencies": ["b"]},
        ],
    )
    assert isinstance(wf, Workflow)


# ---------------------------------------------------------------------------
# WorkflowBuilder API
# ---------------------------------------------------------------------------


def test_workflow_builder_build_returns_workflow() -> None:
    builder = WorkflowBuilder("builder-test")
    builder.add(agent=_ok(), task="do it", name="step1")
    wf = builder.build()
    assert isinstance(wf, Workflow)


def test_workflow_run_succeeds_single_step() -> None:
    agent = _ok()
    with patch.object(agent, "_load_tools", new=AsyncMock()):
        wf = create_workflow(
            name="single",
            steps=[{"id": "only", "name": "Only", "fn": agent}],
        )
        result = asyncio.run(wf.run())
    assert result.success
    assert result.state == WorkflowState.COMPLETED


def test_workflow_run_output_captured() -> None:
    agent = _ok()
    with patch.object(agent, "_load_tools", new=AsyncMock()):
        wf = create_workflow(
            name="output-test",
            steps=[{"id": "s1", "name": "S1", "fn": agent, "task": "ping"}],
        )
        result = asyncio.run(wf.run())
    assert result.success
    assert "done:ping" in str(result.outputs.get("s1", ""))


def test_workflow_run_sequential_chain() -> None:
    a1 = _ok()
    a2 = _ok()
    with (
        patch.object(a1, "_load_tools", new=AsyncMock()),
        patch.object(a2, "_load_tools", new=AsyncMock()),
    ):
        wf = create_workflow(
            name="chain",
            steps=[
                {"id": "a", "name": "A", "fn": a1},
                {"id": "b", "name": "B", "fn": a2, "dependencies": ["a"]},
            ],
        )
        result = asyncio.run(wf.run())
    assert result.success
    assert "a" in result.outputs
    assert "b" in result.outputs


def test_workflow_builder_with_dependencies() -> None:
    a1 = _ok()
    a2 = _ok()
    builder = WorkflowBuilder("dep-test")
    builder.add(agent=a1, task="first", name="first")
    builder.add(agent=a2, task="second", name="second", depends_on=["first"])
    wf = builder.build()
    with (
        patch.object(a1, "_load_tools", new=AsyncMock()),
        patch.object(a2, "_load_tools", new=AsyncMock()),
    ):
        result = asyncio.run(wf.run())
    assert result.success


# ---------------------------------------------------------------------------
# StepState / WorkflowState enums exported correctly
# ---------------------------------------------------------------------------


def test_step_state_completed_value() -> None:
    assert StepState.COMPLETED is not None


def test_workflow_state_completed_value() -> None:
    assert WorkflowState.COMPLETED is not None
