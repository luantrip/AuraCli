"""Canonical visual lifecycle contracts for turns, agents, and operations."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Mapping

from aura_cli.application.agents.events import AgiEvent, AgiEventType
from aura_cli.application.execution import (
    OperationRecord,
    OperationStatus,
    TurnExecution,
    TurnPhase,
)
from aura_cli.application.presentation.tool_grammar import describe_tool_activity


class WorkItemKind(str, Enum):
    TURN = "turn"
    LLM = "llm"
    TOOL = "tool"
    AGENT = "agent"
    WORKFLOW = "workflow"
    EXTERNAL = "external"
    DECISION = "decision"
    CHECKPOINT = "checkpoint"


class WorkItemState(str, Enum):
    QUEUED = "queued"
    PREPARING = "preparing"
    RUNNING = "running"
    STREAMING = "streaming"
    WAITING_EXTERNAL = "waiting_external"
    AWAITING_USER = "awaiting_user"
    COMPLETED = "completed"
    PARTIAL = "partial"
    FAILED = "failed"
    DECLINED = "declined"
    CANCELLED = "cancelled"
    INTERRUPTED = "interrupted"


class WorkItemAttention(str, Enum):
    NONE = "none"
    PASSIVE = "passive"
    ACTION = "action"
    CRITICAL = "critical"


class WorkItemCapability(str, Enum):
    INSPECT = "inspect"
    APPROVE = "approve"
    DECLINE = "decline"
    CANCEL = "cancel"
    RETRY = "retry"
    RESUME = "resume"


TERMINAL_WORK_ITEM_STATES = frozenset(
    {
        WorkItemState.COMPLETED,
        WorkItemState.PARTIAL,
        WorkItemState.FAILED,
        WorkItemState.DECLINED,
        WorkItemState.CANCELLED,
    }
)

_ALLOWED_TRANSITIONS: dict[WorkItemState, frozenset[WorkItemState]] = {
    WorkItemState.QUEUED: frozenset(
        {
            WorkItemState.PREPARING,
            WorkItemState.RUNNING,
            WorkItemState.AWAITING_USER,
            WorkItemState.CANCELLED,
            WorkItemState.FAILED,
        }
    ),
    WorkItemState.PREPARING: frozenset(
        {
            WorkItemState.RUNNING,
            WorkItemState.WAITING_EXTERNAL,
            WorkItemState.AWAITING_USER,
            WorkItemState.CANCELLED,
            WorkItemState.FAILED,
            WorkItemState.INTERRUPTED,
        }
    ),
    WorkItemState.RUNNING: frozenset(
        {
            WorkItemState.STREAMING,
            WorkItemState.WAITING_EXTERNAL,
            WorkItemState.AWAITING_USER,
            WorkItemState.COMPLETED,
            WorkItemState.PARTIAL,
            WorkItemState.FAILED,
            WorkItemState.CANCELLED,
            WorkItemState.INTERRUPTED,
        }
    ),
    WorkItemState.STREAMING: frozenset(
        {
            WorkItemState.RUNNING,
            WorkItemState.WAITING_EXTERNAL,
            WorkItemState.COMPLETED,
            WorkItemState.PARTIAL,
            WorkItemState.FAILED,
            WorkItemState.CANCELLED,
            WorkItemState.INTERRUPTED,
        }
    ),
    WorkItemState.WAITING_EXTERNAL: frozenset(
        {
            WorkItemState.RUNNING,
            WorkItemState.STREAMING,
            WorkItemState.AWAITING_USER,
            WorkItemState.COMPLETED,
            WorkItemState.PARTIAL,
            WorkItemState.FAILED,
            WorkItemState.CANCELLED,
            WorkItemState.INTERRUPTED,
        }
    ),
    WorkItemState.AWAITING_USER: frozenset(
        {
            WorkItemState.RUNNING,
            WorkItemState.DECLINED,
            WorkItemState.CANCELLED,
            WorkItemState.FAILED,
            WorkItemState.INTERRUPTED,
        }
    ),
    WorkItemState.INTERRUPTED: frozenset(
        {
            WorkItemState.QUEUED,
            WorkItemState.PREPARING,
            WorkItemState.RUNNING,
            WorkItemState.CANCELLED,
            WorkItemState.FAILED,
        }
    ),
}

_EXPLICIT_EVENT_STATES = {
    AgiEventType.TASK_ERROR: WorkItemState.FAILED,
    AgiEventType.CHECKPOINT_CREATED: WorkItemState.COMPLETED,
    AgiEventType.TASK_CANCELLED: WorkItemState.CANCELLED,
    AgiEventType.TASK_INTERRUPTED: WorkItemState.INTERRUPTED,
    AgiEventType.APPROVAL_REQUESTED: WorkItemState.AWAITING_USER,
    AgiEventType.EXTERNAL_WAIT_STARTED: WorkItemState.WAITING_EXTERNAL,
    AgiEventType.EXTERNAL_WAIT_ENDED: WorkItemState.RUNNING,
    AgiEventType.PLANNING: WorkItemState.PREPARING,
    AgiEventType.CHAT_MESSAGE: WorkItemState.COMPLETED,
}


@dataclass(frozen=True)
class WorkItemIdentity:
    """Correlation keys carried from runtime through every visual projection."""

    session_id: str | None = None
    turn_id: str | None = None
    task_id: str | None = None
    parent_task_id: str | None = None
    operation_id: str | None = None
    execution_id: str | None = None
    request_id: str | None = None
    tool_call_id: str | None = None

    def __post_init__(self) -> None:
        if not any(
            (
                self.session_id,
                self.turn_id,
                self.task_id,
                self.operation_id,
                self.execution_id,
                self.request_id,
                self.tool_call_id,
            )
        ):
            raise ValueError("work item identity requires at least one correlation key")

    @property
    def stable_key(self) -> str:
        """Return the most specific stable key available to presentation hosts."""
        parts = [
            ("session", self.session_id),
            ("turn", self.turn_id),
            ("task", self.task_id),
            ("operation", self.operation_id),
        ]
        execution_key = self.execution_id or self.request_id or self.tool_call_id
        parts.append(("execution", execution_key))
        return "/".join(f"{name}:{value}" for name, value in parts if value)


@dataclass(frozen=True)
class WorkItemEvidence:
    summary: str | None = None
    paths: tuple[str, ...] = ()
    artifact_refs: tuple[str, ...] = ()
    exit_code: int | None = None


@dataclass(frozen=True)
class WorkItemEnvelope:
    CONTRACT_VERSION = 1

    identity: WorkItemIdentity
    kind: WorkItemKind
    state: WorkItemState
    summary: str
    detail: str | None = None
    attention: WorkItemAttention = WorkItemAttention.NONE
    evidence: WorkItemEvidence = field(default_factory=WorkItemEvidence)
    capabilities: frozenset[WorkItemCapability] = field(default_factory=frozenset)
    started_at: datetime | None = None
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    finished_at: datetime | None = None
    schema_version: int = CONTRACT_VERSION

    @property
    def is_terminal(self) -> bool:
        return self.state in TERMINAL_WORK_ITEM_STATES

    def to_dict(self) -> dict[str, Any]:
        """Return a framework-neutral representation for queues and snapshots."""
        return {
            "schema_version": self.schema_version,
            "identity": {
                key: value
                for key, value in self.identity.__dict__.items()
                if value is not None
            },
            "kind": self.kind.value,
            "state": self.state.value,
            "summary": self.summary,
            "detail": self.detail,
            "attention": self.attention.value,
            "evidence": {
                "summary": self.evidence.summary,
                "paths": list(self.evidence.paths),
                "artifact_refs": list(self.evidence.artifact_refs),
                "exit_code": self.evidence.exit_code,
            },
            "capabilities": sorted(value.value for value in self.capabilities),
            "started_at": _datetime_text(self.started_at),
            "updated_at": _datetime_text(self.updated_at),
            "finished_at": _datetime_text(self.finished_at),
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> WorkItemEnvelope:
        """Restore an envelope without inferring new lifecycle state."""
        evidence = dict(value.get("evidence", {}))
        return cls(
            schema_version=int(value.get("schema_version", cls.CONTRACT_VERSION)),
            identity=WorkItemIdentity(**dict(value["identity"])),
            kind=WorkItemKind(str(value["kind"])),
            state=WorkItemState(str(value["state"])),
            summary=str(value["summary"]),
            detail=_optional_text(value.get("detail")),
            attention=WorkItemAttention(str(value.get("attention", "none"))),
            evidence=WorkItemEvidence(
                summary=_optional_text(evidence.get("summary")),
                paths=tuple(str(path) for path in evidence.get("paths", ())),
                artifact_refs=tuple(
                    str(reference) for reference in evidence.get("artifact_refs", ())
                ),
                exit_code=_optional_int(evidence.get("exit_code")),
            ),
            capabilities=frozenset(
                WorkItemCapability(str(capability))
                for capability in value.get("capabilities", ())
            ),
            started_at=_parse_datetime(value.get("started_at")),
            updated_at=_parse_datetime(value.get("updated_at"))
            or datetime.now(timezone.utc),
            finished_at=_parse_datetime(value.get("finished_at")),
        )


def transition_work_item(
    item: WorkItemEnvelope,
    state: WorkItemState,
    *,
    summary: str | None = None,
    detail: str | None = None,
    evidence: WorkItemEvidence | None = None,
    now: datetime | None = None,
) -> WorkItemEnvelope:
    """Apply one legal lifecycle transition and derive attention/capabilities."""
    if state is item.state:
        return item
    allowed = _ALLOWED_TRANSITIONS.get(item.state, frozenset())
    if state not in allowed:
        raise ValueError(
            f"illegal work item transition: {item.state.value} -> {state.value}"
        )

    timestamp = now or datetime.now(timezone.utc)
    started_at = item.started_at
    if started_at is None and state in {
        WorkItemState.RUNNING,
        WorkItemState.STREAMING,
        WorkItemState.WAITING_EXTERNAL,
        WorkItemState.AWAITING_USER,
    }:
        started_at = timestamp
    finished_at = timestamp if state in TERMINAL_WORK_ITEM_STATES else None
    return replace(
        item,
        state=state,
        summary=summary if summary is not None else item.summary,
        detail=detail if detail is not None else item.detail,
        attention=_attention_for_state(state),
        evidence=evidence if evidence is not None else item.evidence,
        capabilities=_capabilities_for_state(state),
        started_at=started_at,
        updated_at=timestamp,
        finished_at=finished_at,
    )


def work_item_from_turn(turn: TurnExecution) -> WorkItemEnvelope:
    """Project the current turn snapshot without changing its authority."""
    state = {
        TurnPhase.THINKING: WorkItemState.PREPARING,
        TurnPhase.EXECUTING: WorkItemState.RUNNING,
        TurnPhase.VERIFYING: WorkItemState.RUNNING,
        TurnPhase.RESPONDING: WorkItemState.STREAMING,
        TurnPhase.COMPLETED: WorkItemState.COMPLETED,
        TurnPhase.FAILED: WorkItemState.FAILED,
        TurnPhase.INTERRUPTED: WorkItemState.INTERRUPTED,
    }[turn.phase]
    evidence = WorkItemEvidence(
        summary=(turn.completion_evidence[-1] if turn.completion_evidence else None),
        artifact_refs=tuple(turn.completion_evidence),
    )
    return _snapshot(
        identity=WorkItemIdentity(session_id=turn.session_id, turn_id=turn.turn_id),
        kind=WorkItemKind.TURN,
        state=state,
        summary=f"Turno {turn.turn_id}",
        evidence=evidence,
        started_at=turn.started_at,
        finished_at=turn.finished_at,
    )


def work_item_from_operation(
    turn: TurnExecution, operation: OperationRecord
) -> WorkItemEnvelope:
    """Project an operation with its session, turn, call, and evidence identity."""
    state = {
        OperationStatus.PLANNED: WorkItemState.QUEUED,
        OperationStatus.AWAITING_CONFIRMATION: WorkItemState.AWAITING_USER,
        OperationStatus.RUNNING: WorkItemState.RUNNING,
        OperationStatus.SUCCEEDED: WorkItemState.COMPLETED,
        OperationStatus.FAILED: WorkItemState.FAILED,
        OperationStatus.CANCELLED: WorkItemState.CANCELLED,
    }[operation.status]
    return _snapshot(
        identity=WorkItemIdentity(
            session_id=turn.session_id,
            turn_id=turn.turn_id,
            operation_id=operation.operation_id,
            execution_id=operation.tool_call_id,
            tool_call_id=operation.tool_call_id,
        ),
        kind=WorkItemKind.TOOL,
        state=state,
        summary=operation.label,
        detail=operation.target,
        evidence=WorkItemEvidence(
            summary=operation.result_summary,
            paths=tuple(operation.evidence.paths),
            artifact_refs=(
                (operation.output_reference,) if operation.output_reference else ()
            ),
            exit_code=operation.evidence.exit_code,
        ),
        started_at=operation.started_at,
        finished_at=operation.finished_at,
    )


def work_item_from_agent_event(event: AgiEvent) -> WorkItemEnvelope:
    """Translate an agent transport event into the canonical visual lifecycle."""
    data = event.data or {}
    kind = _event_kind(event)
    state = _event_state(event)
    execution_id = (
        str(
            data.get("execution_id")
            or (data.get("request_id") if kind is WorkItemKind.DECISION else "")
            or ""
        )
        or None
    )
    request_id = _optional_text(data.get("request_id"))
    tool_call_id = _optional_text(data.get("tool_call_id"))
    if tool_call_id is None and kind is WorkItemKind.TOOL:
        tool_call_id = _optional_text(data.get("execution_id"))
    summary = _event_summary(event)
    tool_grammar = None
    if kind is WorkItemKind.TOOL:
        tool_grammar = describe_tool_activity(
            str(data.get("tool_name") or "tool"),
            data.get("tool_args") or {},
            result=data.get("result"),
        )
        summary = tool_grammar.label
    return _snapshot(
        identity=WorkItemIdentity(
            session_id=_optional_text(data.get("session_id")),
            turn_id=_optional_text(data.get("turn_id")),
            task_id=event.task_id,
            parent_task_id=event.parent_task_id,
            execution_id=execution_id,
            request_id=request_id,
            tool_call_id=tool_call_id,
        ),
        kind=kind,
        state=state,
        summary=summary,
        detail=_optional_text(
            data.get("message")
            or data.get("error")
            or (tool_grammar.target if tool_grammar else None)
        ),
        evidence=WorkItemEvidence(
            summary=_optional_text(
                tool_grammar.outcome if tool_grammar else data.get("result")
            ),
            paths=_event_paths(data),
            artifact_refs=_event_artifacts(data),
            exit_code=_optional_int(data.get("exit_code")),
        ),
        started_at=datetime.fromtimestamp(event.timestamp, timezone.utc),
        finished_at=(
            datetime.fromtimestamp(event.timestamp, timezone.utc)
            if state in TERMINAL_WORK_ITEM_STATES
            else None
        ),
    )


def _snapshot(
    *,
    identity: WorkItemIdentity,
    kind: WorkItemKind,
    state: WorkItemState,
    summary: str,
    detail: str | None = None,
    evidence: WorkItemEvidence | None = None,
    started_at: datetime | None = None,
    finished_at: datetime | None = None,
) -> WorkItemEnvelope:
    updated_at = finished_at or started_at or datetime.now(timezone.utc)
    return WorkItemEnvelope(
        identity=identity,
        kind=kind,
        state=state,
        summary=summary,
        detail=detail,
        attention=_attention_for_state(state),
        evidence=evidence or WorkItemEvidence(),
        capabilities=_capabilities_for_state(state),
        started_at=started_at,
        updated_at=updated_at,
        finished_at=finished_at,
    )


def _attention_for_state(state: WorkItemState) -> WorkItemAttention:
    if state is WorkItemState.AWAITING_USER:
        return WorkItemAttention.ACTION
    if state is WorkItemState.FAILED:
        return WorkItemAttention.CRITICAL
    if state in {WorkItemState.PARTIAL, WorkItemState.INTERRUPTED}:
        return WorkItemAttention.PASSIVE
    return WorkItemAttention.NONE


def _capabilities_for_state(
    state: WorkItemState,
) -> frozenset[WorkItemCapability]:
    capabilities = {WorkItemCapability.INSPECT}
    if state is WorkItemState.AWAITING_USER:
        capabilities.update(
            {
                WorkItemCapability.APPROVE,
                WorkItemCapability.DECLINE,
                WorkItemCapability.CANCEL,
            }
        )
    elif state in {
        WorkItemState.QUEUED,
        WorkItemState.PREPARING,
        WorkItemState.RUNNING,
        WorkItemState.STREAMING,
        WorkItemState.WAITING_EXTERNAL,
    }:
        capabilities.add(WorkItemCapability.CANCEL)
    elif state in {WorkItemState.FAILED, WorkItemState.PARTIAL}:
        capabilities.add(WorkItemCapability.RETRY)
    elif state is WorkItemState.INTERRUPTED:
        capabilities.update({WorkItemCapability.RESUME, WorkItemCapability.CANCEL})
    return frozenset(capabilities)


def _event_kind(event: AgiEvent) -> WorkItemKind:
    if event.type in {AgiEventType.TOOL_EXECUTING, AgiEventType.TOOL_RESULT}:
        return WorkItemKind.TOOL
    if event.type == AgiEventType.CHECKPOINT_CREATED:
        return WorkItemKind.CHECKPOINT
    if event.type in {
        AgiEventType.APPROVAL_REQUESTED,
        AgiEventType.APPROVAL_RESOLVED,
    }:
        return WorkItemKind.DECISION
    if event.type in {
        AgiEventType.EXTERNAL_WAIT_STARTED,
        AgiEventType.EXTERNAL_WAIT_ENDED,
    }:
        return WorkItemKind.EXTERNAL
    value = str(event.data.get("kind") or "").casefold()
    if value == "workflow":
        return WorkItemKind.WORKFLOW
    if value in {"external", "mcp"}:
        return WorkItemKind.EXTERNAL
    return WorkItemKind.AGENT


def _event_state(event: AgiEvent) -> WorkItemState:
    data = event.data or {}
    if event.type in {AgiEventType.TASK_COMPLETE, AgiEventType.SUBTASK_COMPLETE}:
        return (
            WorkItemState.COMPLETED
            if data.get("success", False)
            else WorkItemState.FAILED
        )
    if event.type == AgiEventType.TOOL_RESULT:
        return (
            WorkItemState.COMPLETED
            if data.get("success", False)
            else WorkItemState.FAILED
        )
    if event.type == AgiEventType.APPROVAL_RESOLVED:
        return (
            WorkItemState.DECLINED
            if data.get("status") == "declined"
            else WorkItemState.COMPLETED
        )
    if event.type in _EXPLICIT_EVENT_STATES:
        return _EXPLICIT_EVENT_STATES[event.type]

    status = str(data.get("status") or "").casefold()
    details = data.get("details", {}) or {}
    supervisor_state = str(details.get("supervisor_state") or "").casefold()
    if supervisor_state == "awaiting_human" or status in {
        "awaiting_confirmation",
        "awaiting_user",
    }:
        return WorkItemState.AWAITING_USER
    if status in {"waiting", "waiting_external", "blocked"}:
        return WorkItemState.WAITING_EXTERNAL
    if status == "streaming":
        return WorkItemState.STREAMING
    if status in {"interrupted", "paused"}:
        return WorkItemState.INTERRUPTED
    if status == "returned_to_chat":
        return WorkItemState.INTERRUPTED
    if status in {"cancelled", "canceled"}:
        return WorkItemState.CANCELLED
    if status in {"failed", "error"}:
        return WorkItemState.FAILED
    return WorkItemState.RUNNING


def _event_summary(event: AgiEvent) -> str:
    data = event.data or {}
    event_type = (
        event.type.value if isinstance(event.type, AgiEventType) else str(event.type)
    )
    if event.type in {AgiEventType.TOOL_EXECUTING, AgiEventType.TOOL_RESULT}:
        return str(data.get("tool_name") or "Ferramenta")
    return str(
        data.get("description")
        or data.get("message")
        or data.get("name")
        or event_type.replace("_", " ")
    )


def _event_paths(data: Mapping[str, Any]) -> tuple[str, ...]:
    values: list[str] = []
    tool_args = data.get("tool_args", {}) or {}
    if isinstance(tool_args, Mapping):
        for key in ("path", "file_path", "directory"):
            if tool_args.get(key):
                values.append(str(tool_args[key]))
    for value in data.get("paths", ()) or ():
        values.append(str(value))
    return tuple(dict.fromkeys(values))


def _event_artifacts(data: Mapping[str, Any]) -> tuple[str, ...]:
    raw = data.get("artifacts", ()) or ()
    if isinstance(raw, str):
        return (raw,)
    return tuple(str(value) for value in raw)


def _optional_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _optional_int(value: Any) -> int | None:
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _datetime_text(value: datetime | None) -> str | None:
    return value.isoformat() if value is not None else None


def _parse_datetime(value: Any) -> datetime | None:
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        return value
    return datetime.fromisoformat(str(value))


__all__ = [
    "TERMINAL_WORK_ITEM_STATES",
    "WorkItemAttention",
    "WorkItemCapability",
    "WorkItemEnvelope",
    "WorkItemEvidence",
    "WorkItemIdentity",
    "WorkItemKind",
    "WorkItemState",
    "transition_work_item",
    "work_item_from_agent_event",
    "work_item_from_operation",
    "work_item_from_turn",
]
