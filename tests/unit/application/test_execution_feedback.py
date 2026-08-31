"""Tests for presentation-neutral execution feedback ports."""

import pytest

from aura_cli.application import execution_feedback
from aura_cli.application.execution_feedback import (
    LoadingCategory,
    LoadingState,
    NullLoadingHandle,
    ShellExecutionState,
    ShellExecutionView,
    configure_file_edit_presenter,
    configure_loading_feedback,
    configure_shell_presenter,
    present_file_edit,
    present_shell_feedback,
    resolve_agent_loading,
    resolve_file_loading,
    show_llm_feedback,
    show_tool_feedback,
)


def test_loading_categories_and_intent_routing_are_surface_independent() -> None:
    assert LoadingCategory.TOOL.value == "tool"
    assert resolve_file_loading("READ") == "read"
    assert resolve_file_loading("sync") == "custom"
    assert resolve_agent_loading("deep thinking") == "thinking"
    assert resolve_agent_loading("plan") == "executing"
    assert resolve_agent_loading("planning work") == "planning"


@pytest.fixture(autouse=True)
def restore_feedback_adapters():
    original = (
        execution_feedback._llm_loading_factory,
        execution_feedback._tool_loading_factory,
        execution_feedback._file_edit_presenter,
        execution_feedback._shell_presenter,
    )
    yield
    execution_feedback._llm_loading_factory = original[0]
    execution_feedback._tool_loading_factory = original[1]
    execution_feedback._file_edit_presenter = original[2]
    execution_feedback._shell_presenter = original[3]


def test_headless_feedback_returns_operational_null_handles() -> None:
    execution_feedback._llm_loading_factory = None
    execution_feedback._tool_loading_factory = None

    llm = show_llm_feedback(None, "model")
    tool = show_tool_feedback(None, "read_file", {})

    assert isinstance(llm, NullLoadingHandle)
    assert isinstance(tool, NullLoadingHandle)
    llm.update(LoadingState.THINKING, "working")
    llm.complete()
    tool.error("ignored")


def test_configured_feedback_delegates_to_host_adapter() -> None:
    calls = []
    llm_handle = object()
    tool_handle = object()
    configure_loading_feedback(
        llm_factory=lambda console, model: calls.append(("llm", model)) or llm_handle,
        tool_factory=lambda console, name, params: (
            calls.append(("tool", name, params)) or tool_handle
        ),
    )
    configure_file_edit_presenter(
        lambda path, old, new, **kwargs: calls.append(("diff", path, old, new, kwargs))
    )

    assert show_llm_feedback(None, "model") is llm_handle
    assert show_tool_feedback(None, "write_file", {"path": "x"}) is tool_handle
    present_file_edit("x", "a", "b", show_preview=True)

    assert calls == [
        ("llm", "model"),
        ("tool", "write_file", {"path": "x"}),
        ("diff", "x", "a", "b", {"show_preview": True}),
    ]


def test_shell_feedback_exposes_neutral_lifecycle_to_host() -> None:
    calls = []
    configure_shell_presenter(lambda console, execution: calls.append(execution.state))
    execution = ShellExecutionView("echo ok")

    execution.start()
    present_shell_feedback(None, execution)
    execution.finish(0)
    present_shell_feedback(None, execution)

    assert calls == [ShellExecutionState.EXECUTING, ShellExecutionState.COMPLETED]
    assert execution.exit_code == 0
    assert execution.execution_time is not None
