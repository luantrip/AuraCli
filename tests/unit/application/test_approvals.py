from aura_cli.application.presentation.approvals import (
    ApprovalCenter,
    ApprovalRequest,
    ApprovalResolution,
    ApprovalScope,
    ApprovalStatus,
    is_preapproved,
    request_approval,
    resolve_approval,
)


def approval(request_id: str = "r1", **kwargs) -> ApprovalRequest:
    return ApprovalRequest(request_id, "child-1", "shell", "Executar?", **kwargs)


def test_child_approval_is_visible_and_correlated_by_request() -> None:
    center = request_approval(
        ApprovalCenter(), approval(parent_task_id="parent-1", session_id="session-1")
    )
    assert center.pending[0].key == "task:child-1/approval:r1"
    assert center.pending[0].parent_task_id == "parent-1"


def test_once_resolution_does_not_create_future_grant() -> None:
    center = request_approval(ApprovalCenter(), approval())
    center = resolve_approval(center, ApprovalResolution("r1", ApprovalStatus.APPROVED))
    assert center.pending == ()
    assert not is_preapproved(center, action="shell")


def test_session_and_policy_scopes_are_distinct() -> None:
    center = request_approval(ApprovalCenter(), approval("session"))
    center = resolve_approval(
        center,
        ApprovalResolution("session", ApprovalStatus.APPROVED, ApprovalScope.SESSION),
    )
    center = request_approval(center, approval("policy", policy_key="shell:workspace"))
    center = resolve_approval(
        center,
        ApprovalResolution("policy", ApprovalStatus.APPROVED, ApprovalScope.POLICY),
    )
    assert is_preapproved(center, action="shell")
    assert is_preapproved(center, action="other", policy_key="shell:workspace")


def test_decline_is_persisted_but_never_granted() -> None:
    center = request_approval(ApprovalCenter(), approval())
    center = resolve_approval(
        center, ApprovalResolution("r1", ApprovalStatus.DECLINED, reason="Não")
    )
    assert center.resolved[0][1].status is ApprovalStatus.DECLINED
    assert not is_preapproved(center, action="shell")
