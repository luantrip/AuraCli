"""Behavioral tests for the neutral guarded tool pipeline."""

import pytest

from aura_cli.application.tools import (
    GuardDecision,
    ToolExecutionPipeline,
    ToolExecutionRequest,
    append_python_syntax_diagnostic,
    format_tool_result,
)


def test_formats_unavailable_nim_result_with_portable_alternatives() -> None:
    formatted = format_tool_result({"ok": False, "backend": "nim", "error": "missing"})

    assert "missing" in formatted
    assert "list_directory(path)" in formatted


def test_appends_diagnostic_to_invalid_successful_python_write() -> None:
    result = append_python_syntax_diagnostic("success", "broken.py", "def broken(")

    assert result.startswith("success")
    assert "SYNTAX ERROR detected in broken.py" in result


def test_does_not_parse_unsuccessful_write_result() -> None:
    assert (
        append_python_syntax_diagnostic("failed", "broken.py", "def broken(")
        == "failed"
    )


@pytest.mark.asyncio
async def test_pipeline_enforces_lifecycle_order() -> None:
    events: list[str] = []
    request = ToolExecutionRequest("read", {"path": "a"}, "call-1")

    pipeline = ToolExecutionPipeline(
        before=lambda _request: events.append("before"),
        guard=lambda _request: (events.append("guard"), GuardDecision(True))[1],
        execute=lambda _request: (events.append("execute"), ("ok", 0.2))[1],
        after=lambda _request, _outcome: events.append("after"),
    )

    outcome = await pipeline.run(request)

    assert events == ["before", "guard", "execute", "after"]
    assert outcome.result == "ok"
    assert outcome.elapsed == 0.2


@pytest.mark.asyncio
async def test_blocked_pipeline_never_executes_or_emits_post_hook() -> None:
    events: list[str] = []
    pipeline = ToolExecutionPipeline(
        before=lambda _request: events.append("before"),
        guard=lambda _request: GuardDecision(False, "denied"),
        execute=lambda _request: (events.append("execute"), (None, 0.0))[1],
        after=lambda _request, _outcome: events.append("after"),
    )

    outcome = await pipeline.run(ToolExecutionRequest("write", {}, "call-2"))

    assert events == ["before"]
    assert outcome.blocked is True
    assert outcome.result == "denied"
