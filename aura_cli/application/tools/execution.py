"""Surface-independent orchestration of one guarded tool invocation."""

from __future__ import annotations

import ast
import asyncio
from dataclasses import dataclass
import inspect
import time
from typing import Any, Awaitable, Callable, Mapping


@dataclass(frozen=True)
class ToolExecutionRequest:
    """Immutable input to the tool execution use case."""

    name: str
    arguments: Mapping[str, Any]
    call_id: str
    task_id: str | None = None
    agent_id: str | None = None
    execution_id: str | None = None
    deadline: float | None = None

    @property
    def effective_execution_id(self) -> str:
        """Return the stable correlation id used by lifecycle emitters."""
        return self.execution_id or self.call_id


@dataclass(frozen=True)
class GuardDecision:
    """Result of policy, audit and user-confirmation guards."""

    allowed: bool
    reason: str = ""


@dataclass(frozen=True)
class ToolExecutionOutcome:
    """Result produced by the neutral execution pipeline."""

    result: Any
    elapsed: float
    blocked: bool = False
    status: str = "success"
    error: str | None = None
    effect_uncertain: bool = False
    execution_id: str | None = None


LifecyclePort = Callable[[ToolExecutionRequest], Any | Awaitable[Any]]
GuardPort = Callable[[ToolExecutionRequest], GuardDecision | Awaitable[GuardDecision]]
ExecutePort = Callable[
    [ToolExecutionRequest], tuple[Any, float] | Awaitable[tuple[Any, float]]
]
PostLifecyclePort = Callable[
    [ToolExecutionRequest, ToolExecutionOutcome], Any | Awaitable[Any]
]


async def _resolve(value: Any | Awaitable[Any]) -> Any:
    if inspect.isawaitable(value):
        return await value
    return value


class ToolExecutionPipeline:
    """Enforce lifecycle order for every productive tool operation."""

    def __init__(
        self,
        *,
        before: LifecyclePort,
        guard: GuardPort,
        execute: ExecutePort,
        after: PostLifecyclePort,
    ) -> None:
        self._before = before
        self._guard = guard
        self._execute = execute
        self._after = after

    async def run(self, request: ToolExecutionRequest) -> ToolExecutionOutcome:
        started = time.monotonic()
        await _resolve(self._before(request))
        if request.deadline is not None and time.monotonic() >= request.deadline:
            return ToolExecutionOutcome(
                result="Execution deadline expired before tool started.",
                elapsed=time.monotonic() - started,
                status="timeout",
                error="deadline_exceeded",
                execution_id=request.effective_execution_id,
            )

        decision = await _resolve(self._guard(request))
        if not decision.allowed:
            return ToolExecutionOutcome(
                result=decision.reason,
                elapsed=0.0,
                blocked=True,
                status="blocked",
                error=decision.reason,
                execution_id=request.effective_execution_id,
            )

        try:
            execution = self._execute(request)
            if request.deadline is None:
                result, elapsed = await _resolve(execution)
            else:
                remaining = max(0.0, request.deadline - time.monotonic())
                result, elapsed = await asyncio.wait_for(
                    _resolve(execution), timeout=remaining
                )
        except asyncio.TimeoutError:
            outcome = ToolExecutionOutcome(
                result="Tool execution deadline expired.",
                elapsed=time.monotonic() - started,
                status="timeout",
                error="deadline_exceeded",
                effect_uncertain=True,
                execution_id=request.effective_execution_id,
            )
            await _resolve(self._after(request, outcome))
            return outcome

        outcome = ToolExecutionOutcome(
            result=result,
            elapsed=elapsed,
            execution_id=request.effective_execution_id,
        )
        await _resolve(self._after(request, outcome))
        return outcome


def format_tool_result(result: Any) -> str:
    """Return a provider-facing representation of a tool result."""
    if not isinstance(result, dict):
        return str(result)
    if result.get("ok") is False and result.get("backend") == "nim":
        error = result.get("error", "Tool unavailable.")
        return (
            f"Nim tool unavailable in this environment: {error}."
            " Use instead: list_directory(path) to list files or"
            " tree_view(path) to view the tree structure."
        )
    return str(result)


def append_python_syntax_diagnostic(result: Any, path: str, source: str) -> Any:
    """Annotate successful Python writes whose resulting source is invalid."""
    if not isinstance(result, str) or "success" not in result.casefold():
        return result
    try:
        ast.parse(source)
    except SyntaxError as error:
        return f"{result}\n\n▲ SYNTAX ERROR detected in {path}: {error}"
    return result
