"""Shared humanized operational feedback for AGI/Ops events."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, Iterable, Literal, Optional

from aura_cli.application.agents.events import AgiEvent, AgiEventType

FeedbackLevel = Literal["info", "success", "warning", "error"]
FeedbackImportance = Literal["low", "normal", "high"]
FeedbackGroup = Literal["operational", "supervisor"]


@dataclass(frozen=True)
class OperationalFeedback:
    """Structured operational feedback derived from an AGI/Ops event."""

    task_id: str
    message: str
    level: FeedbackLevel = "info"
    importance: FeedbackImportance = "normal"
    group: FeedbackGroup = "operational"
    supervisor_state: Optional[str] = None
    dedupe_key: str = ""


@dataclass(frozen=True)
class OperationalTrail:
    """Bounded immutable trail rendered by operational presentation adapters."""

    lines: tuple[str, ...] = ()
    limit: int = 200

    def append(self, message: str) -> OperationalTrail:
        normalized = message.strip()
        if not normalized:
            return self
        return OperationalTrail((*self.lines, normalized)[-self.limit :], self.limit)

    def clear(self) -> OperationalTrail:
        return OperationalTrail(limit=self.limit)

    def export_text(self) -> str:
        header = "# Aura Operational Trail"
        return "\n".join((header, "", *self.lines, ""))


def build_operational_trail(
    events: Iterable[AgiEvent], *, limit: int = 200
) -> OperationalTrail:
    trail = OperationalTrail(limit=limit)
    for event in events:
        trail = trail.append(format_operational_event(event))
    return trail


def _truncate_detail(value: Any, limit: int = 180) -> str:
    """Render a short detail string suitable for UI status lines."""
    text = str(value or "").strip()
    if not text:
        return ""
    if len(text) <= limit:
        return text
    return f"{text[: limit - 3]}..."


def _extract_path_hint(tool_args: Dict[str, Any]) -> str:
    """Extract the most useful file/path hint from tool args."""
    return str(
        tool_args.get("path")
        or tool_args.get("file_path")
        or tool_args.get("test_path")
        or tool_args.get("directory")
        or ""
    ).strip()


def _build_feedback(
    event: AgiEvent,
    message: str,
    *,
    level: FeedbackLevel = "info",
    importance: FeedbackImportance = "normal",
    group: FeedbackGroup = "operational",
    supervisor_state: Optional[str] = None,
    dedupe_key: str = "",
) -> OperationalFeedback:
    """Build a structured feedback object for downstream UI renderers."""
    return OperationalFeedback(
        task_id=event.task_id,
        message=message,
        level=level,
        importance=importance,
        group=group,
        supervisor_state=supervisor_state,
        dedupe_key=dedupe_key or f"{event.task_id}:{event.type}:{message}",
    )


def _describe_explicit_lifecycle(
    event: AgiEvent, data: Dict[str, Any], icon: str
) -> OperationalFeedback | None:
    """Describe Wave 165 lifecycle events outside the legacy event dispatcher."""
    if event.type == AgiEventType.TASK_ERROR:
        reason = _truncate_detail(data.get("reason") or data.get("error"))
        return _build_feedback(
            event,
            f"{icon} Agent failed: {reason or 'unknown error'}",
            level="error",
            importance="high",
        )
    if event.type == AgiEventType.TASK_CANCELLED:
        reason = _truncate_detail(data.get("reason"))
        return _build_feedback(
            event,
            f"{icon} Task cancelled{f': {reason}' if reason else ''}",
            level="warning",
            importance="high",
        )
    if event.type == AgiEventType.TASK_INTERRUPTED:
        reason = _truncate_detail(data.get("reason"))
        resume = " · can resume" if data.get("resumable") else ""
        return _build_feedback(
            event,
            f"{icon} Task interrupted{f': {reason}' if reason else ''}{resume}",
            level="warning",
            importance="high",
        )
    if event.type == AgiEventType.APPROVAL_REQUESTED:
        return _build_feedback(
            event,
            f"{icon} Action required: {data.get('message', 'approval requested')}",
            level="warning",
            importance="high",
            group="supervisor",
            supervisor_state="awaiting_human",
        )
    if event.type == AgiEventType.APPROVAL_RESOLVED:
        declined = data.get("status") == "declined"
        return _build_feedback(
            event,
            f"{icon} Approval {'declined' if declined else 'resolved'}",
            level="warning" if declined else "success",
        )
    if event.type == AgiEventType.EXTERNAL_WAIT_STARTED:
        return _build_feedback(
            event, f"{icon} Waiting: {data.get('message', 'external operation')}"
        )
    if event.type == AgiEventType.EXTERNAL_WAIT_ENDED:
        return _build_feedback(
            event, f"{icon} External wait resolved", level="success", importance="low"
        )
    if event.type == AgiEventType.CHECKPOINT_CREATED:
        return _build_feedback(
            event,
            f"{icon} Checkpoint created: {data.get('name', event.task_id)}",
            level="success",
        )
    return None


_EVENT_ICONS: dict[AgiEventType, str] = {
    AgiEventType.TASK_START: "🚀",
    AgiEventType.TASK_UPDATE: "🧭",
    AgiEventType.TASK_COMPLETE: "✅",
    AgiEventType.SUBTASK_START: "🧩",
    AgiEventType.SUBTASK_COMPLETE: "✔",
    AgiEventType.TOOL_EXECUTING: "🛠",
    AgiEventType.TOOL_RESULT: "📦",
    AgiEventType.PLANNING: "🗺",
    AgiEventType.THINKING: "🧠",
    AgiEventType.TASK_ERROR: "✖",
    AgiEventType.TASK_CANCELLED: "⊘",
    AgiEventType.TASK_INTERRUPTED: "‖",
    AgiEventType.APPROVAL_REQUESTED: "◆",
    AgiEventType.APPROVAL_RESOLVED: "◇",
    AgiEventType.EXTERNAL_WAIT_STARTED: "◌",
    AgiEventType.EXTERNAL_WAIT_ENDED: "●",
    AgiEventType.CHECKPOINT_CREATED: "◈",
}


def _handle_task_start(
    event: AgiEvent, data: dict, icon: str
) -> OperationalFeedback | None:
    return _build_feedback(
        event,
        f"{icon} Agent started task: {data.get('description', event.task_id)}",
        importance="high",
    )


def _handle_task_update(
    event: AgiEvent, data: dict, icon: str
) -> OperationalFeedback | None:
    status = data.get("status", "working")
    message = data.get("message", "updating task state")
    details = data.get("details", {}) or {}
    supervisor_state = str(details.get("supervisor_state") or "").strip()
    fallback_reason = str(details.get("fallback_reason") or "").strip()

    if supervisor_state == "awaiting_human":
        reason_hint = f" ({fallback_reason})" if fallback_reason else ""
        return _build_feedback(
            event,
            f"{icon} Agent is waiting for a human decision{reason_hint}",
            level="warning",
            importance="high",
            group="supervisor",
            supervisor_state="awaiting_human",
            dedupe_key=f"{event.task_id}:{event.type}:awaiting_human:{fallback_reason}",
        )

    if supervisor_state == "returned_to_chat":
        reason_hint = f" ({fallback_reason})" if fallback_reason else ""
        return _build_feedback(
            event,
            f"{icon} Agent returned control to chat{reason_hint}",
            level="warning",
            importance="high",
            group="supervisor",
            supervisor_state="returned_to_chat",
            dedupe_key=f"{event.task_id}:{event.type}:returned_to_chat:{fallback_reason}",
        )

    importance: FeedbackImportance = (
        "high" if status in {"blocked", "waiting", "error"} else "normal"
    )
    level: FeedbackLevel = "warning" if importance == "high" else "info"
    return _build_feedback(
        event,
        f"{icon} Agent is {status}: {message}",
        level=level,
        importance=importance,
    )


def _handle_task_complete(
    event: AgiEvent, data: dict, icon: str
) -> OperationalFeedback | None:
    success = data.get("success", False)
    outcome = "completed" if success else "failed"
    stats = data.get("stats", {}) or {}
    supervisor_state = str(stats.get("supervisor_state") or "").strip()
    fallback_reason = str(stats.get("fallback_reason") or "").strip()
    if not success and supervisor_state == "awaiting_human":
        return _build_feedback(
            event,
            f"{icon} Worker returned to chat awaiting human approval"
            f"{f' ({fallback_reason})' if fallback_reason else ''}",
            level="warning",
            importance="high",
            group="supervisor",
            supervisor_state="awaiting_human",
            dedupe_key=f"{event.task_id}:{event.type}:awaiting_human_complete:{fallback_reason}",
        )
    if not success and supervisor_state == "returned_to_chat":
        return _build_feedback(
            event,
            f"{icon} Worker returned to chat with a fallback"
            f"{f' ({fallback_reason})' if fallback_reason else ''}",
            level="warning",
            importance="high",
            group="supervisor",
            supervisor_state="returned_to_chat",
            dedupe_key=f"{event.task_id}:{event.type}:returned_to_chat_complete:{fallback_reason}",
        )
    detail = _truncate_detail(
        data.get("result") or data.get("error") or "task finished"
    )
    return _build_feedback(
        event,
        f"{icon} Agent {outcome}: {detail}",
        level="success" if success else "error",
        importance="high",
    )


def _handle_subtask_start(
    event: AgiEvent, data: dict, icon: str
) -> OperationalFeedback | None:
    return _build_feedback(
        event,
        f"{icon} Agent started subtask: {data.get('description', event.task_id)}",
        importance="normal",
    )


def _handle_subtask_complete(
    event: AgiEvent, data: dict, icon: str
) -> OperationalFeedback | None:
    success = data.get("success", False)
    status = data.get("status") or ("completed" if success else "failed")
    return _build_feedback(
        event,
        f"{icon} Subtask {status}: {data.get('description', event.task_id)}",
        level="success" if success else "error",
        importance="normal",
    )


def _handle_tool_executing(
    event: AgiEvent, data: dict, icon: str
) -> OperationalFeedback | None:
    tool_name = data.get("tool_name", "unknown_tool")
    tool_args = data.get("tool_args", {}) or {}
    path_hint = _extract_path_hint(tool_args)
    suffix = f" on {path_hint}" if path_hint else ""
    return _build_feedback(
        event,
        f"{icon} Agent is running {tool_name}{suffix}",
        importance="low",
        dedupe_key=f"{event.task_id}:{event.type}:{tool_name}:{path_hint}",
    )


def _handle_tool_result(
    event: AgiEvent, data: dict, icon: str
) -> OperationalFeedback | None:
    tool_name = data.get("tool_name", "tool")
    success = data.get("success", False)
    exec_time = data.get("execution_time")
    time_hint = f" ({exec_time:.1f}s)" if isinstance(exec_time, (int, float)) else ""
    status = "completed" if success else "failed"
    return _build_feedback(
        event,
        f"{icon} {tool_name} {status}{time_hint}",
        level="success" if success else "error",
        importance="normal" if success else "high",
        dedupe_key=f"{event.task_id}:{event.type}:{tool_name}:{status}",
    )


def _handle_planning(
    event: AgiEvent, data: dict, icon: str
) -> OperationalFeedback | None:
    return _build_feedback(
        event,
        f"{icon} Agent is planning next steps",
        importance="low",
    )


def _handle_thinking(
    event: AgiEvent, data: dict, icon: str
) -> OperationalFeedback | None:
    return _build_feedback(
        event,
        f"{icon} Agent is analyzing options",
        importance="low",
    )


# Dispatch table mapping each event type to its handler.
_EVENT_HANDLERS: dict[
    AgiEventType, Callable[[AgiEvent, dict, str], OperationalFeedback | None]
] = {
    AgiEventType.TASK_START: _handle_task_start,
    AgiEventType.TASK_UPDATE: _handle_task_update,
    AgiEventType.TASK_COMPLETE: _handle_task_complete,
    AgiEventType.SUBTASK_START: _handle_subtask_start,
    AgiEventType.SUBTASK_COMPLETE: _handle_subtask_complete,
    AgiEventType.TOOL_EXECUTING: _handle_tool_executing,
    AgiEventType.TOOL_RESULT: _handle_tool_result,
    AgiEventType.PLANNING: _handle_planning,
    AgiEventType.THINKING: _handle_thinking,
}


def describe_operational_event(event: AgiEvent) -> OperationalFeedback | None:
    """Convert an AGI/Ops event into structured human-readable feedback."""
    data = event.data or {}
    icon = _EVENT_ICONS.get(event.type, "•")

    explicit = _describe_explicit_lifecycle(event, data, icon)
    if explicit is not None:
        return explicit

    handler = _EVENT_HANDLERS.get(event.type)
    if handler is not None:
        return handler(event, data, icon)

    return None


def format_operational_event(event: AgiEvent) -> str:
    """Return the concise human-readable text for an operational event."""
    feedback = describe_operational_event(event)
    return feedback.message if feedback else ""
