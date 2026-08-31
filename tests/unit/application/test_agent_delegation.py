"""Application-level contracts for delegated-work handoffs."""

from pathlib import Path

from aura_cli.application.agents.delegation import (
    DelegationLaunchOutcome,
    DelegationLaunchStatus,
    assess_delegation_launch,
    build_delegate_handoff,
    build_delegate_payload,
    format_delegation_launch_outcome,
    get_supervisor_state,
    prepare_delegation,
)


def test_handoff_uses_only_recent_conversational_messages() -> None:
    history = [
        {"role": "system", "content": "secret system setup"},
        {"role": "user", "content": "inspect architecture"},
        {"role": "tool", "content": "large raw result"},
        {"role": "assistant", "content": "I will inspect it"},
    ]
    handoff = build_delegate_handoff(
        "continue",
        agent_label="Ops",
        conversation_history=history,
        project_root=Path("/work"),
        final_model="local",
        constitution=None,
    )
    assert "inspect architecture" in handoff
    assert "I will inspect it" in handoff
    assert "secret system setup" not in handoff
    assert "large raw result" not in handoff


def test_payload_and_supervisor_state_are_framework_independent() -> None:
    payload = build_delegate_payload(
        " task ",
        agent_label="AGI",
        conversation_history=[],
        project_root=Path("/work"),
        final_model="model",
        constitution="active",
        mode="safe",
    )
    assert payload["primary_request"] == "task"
    assert payload["constitution_active"] is True
    assert (
        get_supervisor_state(status="running", alive=False, fallback_reason=None)
        == "in_progress"
    )


def test_prepare_ops_delegation_normalizes_mode_and_builds_consistent_outputs() -> None:
    plan = prepare_delegation(
        "deploy",
        agent_type="OPS",
        conversation_history=[],
        project_root=Path("/work"),
        final_model="local",
        constitution=None,
        mode="invalid",
    )
    assert plan.agent_type == "ops"
    assert plan.mode == "general"
    assert plan.payload["delegation_mode"] == "general"
    assert "Requested mode: general" in plan.handoff


def test_launch_assessment_and_formatting_cover_early_outcomes() -> None:
    busy = assess_delegation_launch(
        agent_type="agi", request="task", worker_active=True
    )
    missing = assess_delegation_launch(
        agent_type="ops",
        request="deploy",
        worker_active=False,
        has_credentials=False,
    )
    assert busy is not None and busy.status is DelegationLaunchStatus.BUSY
    assert "já está em execução" in format_delegation_launch_outcome(busy)
    assert missing is not None
    assert "Nenhuma API key" in format_delegation_launch_outcome(missing)


def test_started_outcome_bounds_request_excerpt() -> None:
    outcome = DelegationLaunchOutcome(
        DelegationLaunchStatus.STARTED,
        "ops",
        request="x" * 250,
        mode="git",
        task_id="task-1",
        thread_name="thread-1",
    )
    rendered = format_delegation_launch_outcome(outcome)
    assert "modo git" in rendered
    assert "x" * 201 not in rendered
    assert "task_id=task-1" in rendered
