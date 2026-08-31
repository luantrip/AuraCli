"""Contract tests for the neutral tool execution boundary."""

from __future__ import annotations

import asyncio
import time

import pytest

from aura_cli.application.tools import CapabilityMatrix, ToolCapability
from aura_cli.application.tools.execution import (
    GuardDecision,
    ToolExecutionPipeline,
    ToolExecutionRequest,
)


@pytest.mark.asyncio
async def test_pipeline_returns_blocked_outcome_without_execution() -> None:
    after_calls: list[str] = []

    async def execute(_request: ToolExecutionRequest) -> tuple[str, float]:
        raise AssertionError("blocked tool must not execute")

    async def after(_request: ToolExecutionRequest, outcome: object) -> None:
        after_calls.append(type(outcome).__name__)

    pipeline = ToolExecutionPipeline(
        before=lambda _request: None,
        guard=lambda _request: GuardDecision(False, "negado"),
        execute=execute,
        after=after,
    )
    outcome = await pipeline.run(
        ToolExecutionRequest("write_file", {}, "call-1", task_id="task-1")
    )

    assert outcome.status == "blocked"
    assert outcome.blocked is True
    assert outcome.error == "negado"
    assert outcome.execution_id == "call-1"
    assert after_calls == []


@pytest.mark.asyncio
async def test_pipeline_marks_deadline_timeout_as_effect_uncertain() -> None:
    after_statuses: list[str] = []

    async def execute(_request: ToolExecutionRequest) -> tuple[str, float]:
        await asyncio.sleep(0.05)
        return "late", 0.05

    async def after(_request: ToolExecutionRequest, outcome: object) -> None:
        after_statuses.append(outcome.status)  # type: ignore[attr-defined]

    pipeline = ToolExecutionPipeline(
        before=lambda _request: None,
        guard=lambda _request: GuardDecision(True),
        execute=execute,
        after=after,
    )
    outcome = await pipeline.run(
        ToolExecutionRequest(
            "run_shell_command",
            {},
            "call-2",
            deadline=time.monotonic() + 0.001,
        )
    )

    assert outcome.status == "timeout"
    assert outcome.error == "deadline_exceeded"
    assert outcome.effect_uncertain is True
    assert outcome.execution_id == "call-2"
    assert after_statuses == ["timeout"]


def test_capability_matrix_is_deterministic_and_rejects_duplicates() -> None:
    matrix = CapabilityMatrix(
        [
            ToolCapability("write_file", effect="mutating", risk="high"),
            ToolCapability("list_directory", runtimes=frozenset({"general", "ops"})),
        ]
    )

    assert matrix.require("write_file").mutating is True
    assert [entry.name for entry in matrix.for_runtime("ops")] == ["list_directory"]
    assert matrix.as_dict()["write_file"]["risk"] == "high"

    with pytest.raises(ValueError, match="Duplicated capability names"):
        CapabilityMatrix([ToolCapability("same"), ToolCapability("same")])
