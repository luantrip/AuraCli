"""Canonical approval center for requests, policy scopes and resolutions."""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum

from aura_cli.application.agents.events import AgiEvent


class ApprovalScope(str, Enum):
    ONCE = "once"
    SESSION = "session"
    POLICY = "policy"


class ApprovalStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    DECLINED = "declined"
    CANCELLED = "cancelled"
    TIMED_OUT = "timed_out"


@dataclass(frozen=True)
class ApprovalRequest:
    request_id: str
    task_id: str
    action: str
    message: str
    scope: ApprovalScope = ApprovalScope.ONCE
    parent_task_id: str | None = None
    session_id: str | None = None
    policy_key: str | None = None

    @property
    def key(self) -> str:
        return f"task:{self.task_id}/approval:{self.request_id}"


@dataclass(frozen=True)
class ApprovalResolution:
    request_id: str
    status: ApprovalStatus
    scope: ApprovalScope = ApprovalScope.ONCE
    reason: str | None = None


@dataclass(frozen=True)
class ApprovalCenter:
    pending: tuple[ApprovalRequest, ...] = ()
    resolved: tuple[tuple[ApprovalRequest, ApprovalResolution], ...] = ()
    session_grants: frozenset[str] = frozenset()
    policy_grants: frozenset[str] = frozenset()


def request_approval(
    center: ApprovalCenter, request: ApprovalRequest
) -> ApprovalCenter:
    pending = tuple(
        item for item in center.pending if item.request_id != request.request_id
    )
    return replace(center, pending=(*pending, request))


def resolve_approval(
    center: ApprovalCenter, resolution: ApprovalResolution
) -> ApprovalCenter:
    request = next(
        (item for item in center.pending if item.request_id == resolution.request_id),
        None,
    )
    if request is None:
        return center
    pending = tuple(
        item for item in center.pending if item.request_id != resolution.request_id
    )
    resolved = tuple(
        item for item in center.resolved if item[0].request_id != resolution.request_id
    )
    session_grants = center.session_grants
    policy_grants = center.policy_grants
    if resolution.status is ApprovalStatus.APPROVED:
        if resolution.scope is ApprovalScope.SESSION:
            session_grants = frozenset((*session_grants, request.action))
        elif resolution.scope is ApprovalScope.POLICY and request.policy_key:
            policy_grants = frozenset((*policy_grants, request.policy_key))
    return replace(
        center,
        pending=pending,
        resolved=(*resolved, (request, resolution)),
        session_grants=session_grants,
        policy_grants=policy_grants,
    )


def is_preapproved(
    center: ApprovalCenter, *, action: str, policy_key: str | None = None
) -> bool:
    return action in center.session_grants or bool(
        policy_key and policy_key in center.policy_grants
    )


def approval_request_from_event(event: AgiEvent) -> ApprovalRequest:
    data = event.data or {}
    return ApprovalRequest(
        request_id=str(data.get("request_id") or event.task_id),
        task_id=event.task_id,
        action=str(data.get("action") or "decision"),
        message=str(data.get("message") or "Ação necessária"),
        scope=ApprovalScope(str(data.get("scope") or "once")),
        parent_task_id=event.parent_task_id,
        session_id=str(data.get("session_id")) if data.get("session_id") else None,
        policy_key=str(data.get("policy_key")) if data.get("policy_key") else None,
    )


def approval_resolution_from_event(event: AgiEvent) -> ApprovalResolution:
    data = event.data or {}
    status = str(data.get("status") or "declined")
    return ApprovalResolution(
        request_id=str(data.get("request_id") or event.task_id),
        status=ApprovalStatus.APPROVED
        if status == "running"
        else ApprovalStatus.DECLINED,
        scope=ApprovalScope(str(data.get("scope") or "once")),
        reason=str(data.get("message")) if data.get("message") else None,
    )


__all__ = [
    "ApprovalCenter",
    "ApprovalRequest",
    "ApprovalResolution",
    "ApprovalScope",
    "ApprovalStatus",
    "approval_request_from_event",
    "approval_resolution_from_event",
    "is_preapproved",
    "request_approval",
    "resolve_approval",
]
