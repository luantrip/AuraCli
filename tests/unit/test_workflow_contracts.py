"""Contract tests for the application agent workflow lifecycle."""

from __future__ import annotations

import asyncio

import pytest

from aura_cli.application.agents.contracts import AgentResponse
from aura_cli.application.agents.workflow import StepState, Workflow, WorkflowState


class _EchoAgent:
    def __init__(self, content: str = "ok") -> None:
        self.content = content
        self.calls: list[str] = []

    async def execute(self, task: str, **kwargs: object) -> AgentResponse:
        self.calls.append(task)
        return AgentResponse(content=self.content, success=True)


class _BlockingAgent(_EchoAgent):
    def __init__(self) -> None:
        super().__init__(content="released")
        self.started = asyncio.Event()
        self.release = asyncio.Event()

    async def execute(self, task: str, **kwargs: object) -> AgentResponse:
        self.calls.append(task)
        self.started.set()
        await self.release.wait()
        return AgentResponse(content=self.content, success=True)


@pytest.mark.asyncio
async def test_workflow_result_to_dict_is_json_safe() -> None:
    agent = _EchoAgent()
    workflow = Workflow("serialization")
    workflow.add_step(agent, "Inspect", name="inspect")

    result = await workflow.run()

    payload = result.to_dict()
    assert result.state is WorkflowState.COMPLETED
    assert payload["workflow_id"] == workflow.id
    assert payload["state"] == "completed"
    assert payload["steps"][0]["state"] == "completed"
    assert payload["steps"][0]["result"] == "ok"


@pytest.mark.asyncio
async def test_cancel_marks_pending_steps_and_prevents_follow_up_execution() -> None:
    first = _BlockingAgent()
    second = _EchoAgent(content="must not run")
    workflow = Workflow("cancellation", max_parallel=1)
    workflow.add_step(first, "First", name="first")
    workflow.add_step(second, "Second", name="second", depends_on=["first"])

    run_task = asyncio.create_task(workflow.run())
    await asyncio.wait_for(first.started.wait(), timeout=1.0)
    workflow.cancel()
    first.release.set()

    result = await asyncio.wait_for(run_task, timeout=1.0)

    assert result.state is WorkflowState.CANCELLED
    assert first.calls == ["First"]
    assert second.calls == []
    assert result.steps[0].state is StepState.CANCELLED
    assert result.steps[1].state is StepState.CANCELLED


@pytest.mark.asyncio
async def test_composite_agent_returns_serialized_workflow_metadata() -> None:
    from aura_cli.adk.agent import Agent as AdkAgent
    from aura_cli.adk.agent import CompositeAgent

    class _AdkEcho(AdkAgent):
        name = "echo_agent"

        async def execute(self, task: str, **kwargs: object) -> AgentResponse:
            return AgentResponse(content=f"echo:{task}", success=True)

    composite = CompositeAgent([_AdkEcho()])
    response = await composite.execute("hello")

    assert response.success is True
    assert response.metadata["workflow_result"]["state"] == "completed"
    assert response.content == "echo:hello"
