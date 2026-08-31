"""Reduce canonical work items into host-neutral visual projections."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timezone
from enum import Enum

from aura_cli.application.agents.events import AgiEvent, AgiEventType
from aura_cli.application.presentation.realtime_execution import (
    RealtimeExecution,
    describe_realtime_execution,
    format_elapsed,
)
from aura_cli.application.presentation.tui_surfaces import (
    PresentationIntent,
    SurfaceRequest,
)
from aura_cli.application.presentation.work_items import (
    WorkItemAttention,
    WorkItemCapability,
    WorkItemEnvelope,
    WorkItemKind,
    WorkItemState,
    work_item_from_agent_event,
)


class ProjectionTone(str, Enum):
    MUTED = "muted"
    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"


@dataclass(frozen=True)
class ConversationProjection:
    content: str
    persistent: bool = True


@dataclass(frozen=True)
class ActivityProjection:
    key: str
    label: str
    detail: str | None
    tone: ProjectionTone
    replace: bool = True


@dataclass(frozen=True)
class AttentionProjection:
    key: str
    title: str
    message: str
    tone: ProjectionTone
    blocking: bool


@dataclass(frozen=True)
class InspectionProjection:
    key: str
    title: str
    state: WorkItemState
    detail: str | None
    evidence_summary: str | None
    paths: tuple[str, ...]
    artifact_refs: tuple[str, ...]
    exit_code: int | None
    capabilities: frozenset[WorkItemCapability]


@dataclass(frozen=True)
class WorkItemProjection:
    identity_key: str
    conversation: ConversationProjection | None
    activity: ActivityProjection | None
    attention: AttentionProjection | None
    inspection: InspectionProjection
    realtime: RealtimeExecution


def project_work_item(
    item: WorkItemEnvelope,
    *,
    now: datetime | None = None,
    heartbeat_seconds: int = 15,
    background: bool = False,
) -> WorkItemProjection:
    """Produce every visual projection from one authoritative lifecycle snapshot."""
    key = item.identity.stable_key
    tone = _tone(item.state)
    state_label = _state_label(item.state)
    task_prefix = f"[{item.identity.task_id}] " if item.identity.task_id else ""
    activity_detail = (
        item.detail
        or item.evidence.summary
        or (item.evidence.paths[0] if item.evidence.paths else None)
    )
    realtime = describe_realtime_execution(
        item,
        now=now,
        heartbeat_seconds=heartbeat_seconds,
        background=background,
    )
    detail_suffix = f" — {activity_detail}" if activity_detail else ""
    activity = ActivityProjection(
        key=key,
        label=f"{task_prefix}{item.summary} · {state_label}{detail_suffix}",
        detail=activity_detail,
        tone=tone,
        replace=realtime.replace,
    )
    return WorkItemProjection(
        identity_key=key,
        conversation=_conversation(item, state_label),
        activity=activity,
        attention=_attention(item, key, tone),
        inspection=InspectionProjection(
            key=key,
            title=item.summary,
            state=item.state,
            detail=item.detail,
            evidence_summary=item.evidence.summary,
            paths=item.evidence.paths,
            artifact_refs=item.evidence.artifact_refs,
            exit_code=item.evidence.exit_code,
            capabilities=item.capabilities,
        ),
        realtime=realtime,
    )


def surface_requests_from_projection(
    projection: WorkItemProjection, *, task_id: str = "global_chat"
) -> tuple[SurfaceRequest, ...]:
    """Translate neutral projections to semantic surface requests, not widgets."""
    requests: list[SurfaceRequest] = []
    if projection.conversation is not None:
        requests.append(
            SurfaceRequest(
                PresentationIntent.INFORMATION,
                projection.conversation.content,
                persistent=projection.conversation.persistent,
                task_id=task_id,
                key=projection.identity_key,
            )
        )
    if projection.activity is not None:
        content = projection.activity.label
        if projection.realtime.elapsed_seconds >= 1:
            content = (
                f"{content} · {format_elapsed(projection.realtime.elapsed_seconds)}"
            )
        requests.append(
            SurfaceRequest(
                PresentationIntent.PROGRESS,
                content,
                task_id=task_id,
                key=projection.activity.key,
                tone=projection.activity.tone.value,
                replace=projection.activity.replace,
                consolidate=projection.realtime.consolidate,
                elapsed_seconds=projection.realtime.elapsed_seconds,
                heartbeat_due=projection.realtime.heartbeat_due,
                background=projection.realtime.background,
            )
        )
    if projection.attention is not None:
        intent = (
            PresentationIntent.DECISION
            if projection.attention.blocking
            else PresentationIntent.ERROR
            if projection.attention.tone is ProjectionTone.ERROR
            else PresentationIntent.WARNING
        )
        requests.append(
            SurfaceRequest(
                intent,
                projection.attention.message,
                title=projection.attention.title,
                persistent=projection.conversation is not None,
                task_id=task_id,
                key=projection.attention.key,
                tone=projection.attention.tone.value,
            )
        )
    return tuple(requests)


class RealtimeProjectionReducer:
    """Preserve timing across event snapshots and emit periodic heartbeats."""

    def __init__(self, *, heartbeat_seconds: int = 15) -> None:
        self.heartbeat_seconds = heartbeat_seconds
        self._active: dict[str, WorkItemEnvelope] = {}
        self._heartbeat_buckets: dict[str, int] = {}
        self._background: dict[str, bool] = {}

    def reduce(self, event: AgiEvent) -> tuple[SurfaceRequest, ...]:
        if event.type == AgiEventType.CHAT_MESSAGE:
            return ()
        item = work_item_from_agent_event(event)
        key = item.identity.stable_key
        previous = self._active.get(key)
        if previous is not None and previous.started_at is not None:
            item = replace(item, started_at=previous.started_at)
            if item.kind is WorkItemKind.TOOL and not (
                event.data.get("tool_args") or {}
            ):
                item = replace(
                    item,
                    summary=previous.summary,
                    detail=item.detail or previous.detail,
                    evidence=replace(
                        item.evidence,
                        paths=item.evidence.paths or previous.evidence.paths,
                    ),
                )
        projection = project_work_item(
            item,
            now=datetime.fromtimestamp(event.timestamp, timezone.utc),
            heartbeat_seconds=self.heartbeat_seconds,
            background=bool(event.data.get("background", False)),
        )
        if projection.realtime.consolidate:
            self._active.pop(key, None)
            self._heartbeat_buckets.pop(key, None)
            self._background.pop(key, None)
        else:
            self._active[key] = item
            self._background[key] = bool(event.data.get("background", False))
        requests = surface_requests_from_projection(projection, task_id=event.task_id)
        if event.type == AgiEventType.APPROVAL_RESOLVED:
            requests = tuple(
                replace(request, resolves_attention=True) for request in requests
            )
        return requests

    def heartbeat(self, *, now: datetime | None = None) -> tuple[SurfaceRequest, ...]:
        current = now or datetime.now(timezone.utc)
        requests: list[SurfaceRequest] = []
        for item in self._active.values():
            realtime = describe_realtime_execution(
                item,
                now=current,
                heartbeat_seconds=self.heartbeat_seconds,
                background=self._background.get(item.identity.stable_key, False),
            )
            if not realtime.heartbeat_due:
                continue
            bucket = realtime.elapsed_seconds // self.heartbeat_seconds
            if self._heartbeat_buckets.get(realtime.key) == bucket:
                continue
            self._heartbeat_buckets[realtime.key] = bucket
            projection = replace(
                project_work_item(
                    item,
                    now=current,
                    heartbeat_seconds=self.heartbeat_seconds,
                    background=realtime.background,
                ),
                realtime=realtime,
            )
            requests.extend(
                request
                for request in surface_requests_from_projection(
                    projection, task_id=item.identity.task_id or "global_chat"
                )
                if request.intent is PresentationIntent.PROGRESS
            )
        return tuple(requests)


def _conversation(
    item: WorkItemEnvelope, state_label: str
) -> ConversationProjection | None:
    """Keep durable outcomes in chat while transient movement stays in activity."""
    if item.kind is WorkItemKind.CHECKPOINT:
        return None
    if item.state is WorkItemState.COMPLETED:
        evidence = item.evidence.summary
        content = f"{item.summary} · {state_label}"
        if evidence:
            content = f"{content}\n{evidence}"
        return ConversationProjection(content)
    if item.state in {
        WorkItemState.PARTIAL,
        WorkItemState.FAILED,
        WorkItemState.DECLINED,
        WorkItemState.CANCELLED,
        WorkItemState.INTERRUPTED,
    }:
        reason = item.detail or item.evidence.summary
        content = f"{item.summary} · {state_label}"
        return ConversationProjection(f"{content}\n{reason}" if reason else content)
    return None


def _attention(
    item: WorkItemEnvelope, key: str, tone: ProjectionTone
) -> AttentionProjection | None:
    if item.attention is WorkItemAttention.NONE:
        return None
    blocking = item.attention is WorkItemAttention.ACTION
    title = "Ação necessária" if blocking else _state_label(item.state).capitalize()
    return AttentionProjection(
        key=key,
        title=title,
        message=item.detail or item.summary,
        tone=tone,
        blocking=blocking,
    )


def _tone(state: WorkItemState) -> ProjectionTone:
    if state is WorkItemState.COMPLETED:
        return ProjectionTone.SUCCESS
    if state is WorkItemState.FAILED:
        return ProjectionTone.ERROR
    if state in {
        WorkItemState.AWAITING_USER,
        WorkItemState.PARTIAL,
        WorkItemState.DECLINED,
        WorkItemState.CANCELLED,
        WorkItemState.INTERRUPTED,
    }:
        return ProjectionTone.WARNING
    if state in {WorkItemState.QUEUED, WorkItemState.PREPARING}:
        return ProjectionTone.MUTED
    return ProjectionTone.INFO


def _state_label(state: WorkItemState) -> str:
    return {
        WorkItemState.QUEUED: "na fila",
        WorkItemState.PREPARING: "preparando",
        WorkItemState.RUNNING: "em execução",
        WorkItemState.STREAMING: "transmitindo",
        WorkItemState.WAITING_EXTERNAL: "waiting for external operation",
        WorkItemState.AWAITING_USER: "waiting for you",
        WorkItemState.COMPLETED: "completed",
        WorkItemState.PARTIAL: "conclusão parcial",
        WorkItemState.FAILED: "falhou",
        WorkItemState.DECLINED: "recusado",
        WorkItemState.CANCELLED: "cancelled",
        WorkItemState.INTERRUPTED: "interrupted",
    }[state]


__all__ = [
    "ActivityProjection",
    "AttentionProjection",
    "ConversationProjection",
    "InspectionProjection",
    "ProjectionTone",
    "RealtimeProjectionReducer",
    "WorkItemProjection",
    "project_work_item",
    "surface_requests_from_projection",
]
