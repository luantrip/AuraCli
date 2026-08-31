import pytest

from aura_cli.application.presentation.external_tools import (
    ExternalToolPhase,
    begin_external_tool,
    transition_external_tool,
)


def test_full_external_tool_return_protocol_preserves_artifacts_cwd_and_focus() -> None:
    session = begin_external_tool("external-1", "Paint", "/workspace")
    session = transition_external_tool(session, ExternalToolPhase.LAUNCHING)
    session = transition_external_tool(session, ExternalToolPhase.ATTACHED)
    session = transition_external_tool(
        session,
        ExternalToolPhase.RETURNING,
        cwd="/workspace/art",
        artifacts=("art/output.ans",),
    )
    session = transition_external_tool(
        session,
        ExternalToolPhase.COMPLETED,
        exit_code=0,
        focus_returned=True,
    )
    assert session.cwd_changed
    assert session.artifacts == ("art/output.ans",)
    assert session.focus_returned


def test_failure_and_interruption_are_explicit_terminal_returns() -> None:
    failed = begin_external_tool("e1", "Files", "/workspace")
    failed = transition_external_tool(failed, ExternalToolPhase.FAILED, error="missing")
    assert failed.phase is ExternalToolPhase.FAILED
    assert failed.error == "missing"

    interrupted = begin_external_tool("e2", "Monitor", "/workspace")
    interrupted = transition_external_tool(interrupted, ExternalToolPhase.LAUNCHING)
    interrupted = transition_external_tool(interrupted, ExternalToolPhase.ATTACHED)
    interrupted = transition_external_tool(interrupted, ExternalToolPhase.INTERRUPTED)
    assert interrupted.phase is ExternalToolPhase.INTERRUPTED


def test_external_tool_protocol_rejects_skipped_attach() -> None:
    session = begin_external_tool("e1", "Paint", "/workspace")
    with pytest.raises(ValueError, match="suspending -> returning"):
        transition_external_tool(session, ExternalToolPhase.RETURNING)
