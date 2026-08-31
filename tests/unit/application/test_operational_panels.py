"""Tests for neutral operational panel state."""

from aura_cli.application.presentation.operational_panels import (
    DelegatedTaskState,
    ToolExecutionState,
    delegated_tasks_complete,
    summarize_tool_executions,
)


def test_delegated_task_transitions_and_completion() -> None:
    done = DelegatedTaskState("done")
    failed = DelegatedTaskState("failed")
    done.mark_running(2)
    done.mark_done(3, 1.5)
    failed.mark_failed("boom")

    assert delegated_tasks_complete([done, failed]) is True
    assert done.tool_count == 3
    assert failed.error == "boom"


def test_tool_execution_preserves_explicit_zero_duration_and_summary() -> None:
    success = ToolExecutionState("read", {})
    failure = ToolExecutionState("write", {})
    success.mark_success("ok", duration=0.0, clock=lambda: 99)
    failure.mark_error("boom", duration=2.0)

    assert success.duration == 0.0
    assert summarize_tool_executions([success, failure]) == {
        "success": 1,
        "error": 1,
        "duration": 2.0,
    }
