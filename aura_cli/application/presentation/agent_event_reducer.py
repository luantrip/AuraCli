"""Reduce agent events into presentation state and framework-neutral effects."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Protocol

from aura_cli.application.agents.events import AgiEvent, AgiEventType
from aura_cli.application.presentation.safe_payloads import (
    redact_tool_args,
    safe_tool_args_json,
)


class AgentEventStore(Protocol):
    def add_task(self, task_id: str, task_data: dict[str, Any]) -> None: ...
    def get_task(self, task_id: str) -> dict[str, Any] | None: ...
    def add_message(self, message: dict[str, Any]) -> None: ...


@dataclass(frozen=True)
class ChatEffect:
    sender: str
    content: str
    task_id: str


@dataclass(frozen=True)
class AgentEventReduction:
    """Visual effects requested after the state transition is complete."""

    chat: ChatEffect | None = None
    hide_thinking: bool = False
    show_thinking_for: str | None = None


class AgentEventStateReducer:
    """Canonical state transitions for events consumed by presentation adapters."""

    _TERMINAL_STATUSES = frozenset({"completed", "failed", "cancelled", "declined"})

    def __init__(self, store: AgentEventStore, *, result_limit: int = 500) -> None:
        self.store = store
        self.result_limit = result_limit

    def reduce(self, event: AgiEvent) -> AgentEventReduction:
        handlers = {
            AgiEventType.TASK_START: self._task_start,
            AgiEventType.TASK_UPDATE: self._task_update,
            AgiEventType.TASK_COMPLETE: self._task_complete,
            AgiEventType.SUBTASK_START: self._subtask_start,
            AgiEventType.SUBTASK_COMPLETE: self._subtask_complete,
            AgiEventType.TOOL_EXECUTING: self._tool_executing,
            AgiEventType.TOOL_RESULT: self._tool_result,
            AgiEventType.CHAT_MESSAGE: self._chat_message,
            AgiEventType.PLANNING: self._planning,
            AgiEventType.THINKING: self._thinking,
            AgiEventType.TASK_ERROR: self._task_error,
            AgiEventType.TASK_CANCELLED: self._task_cancelled,
            AgiEventType.TASK_INTERRUPTED: self._task_interrupted,
            AgiEventType.APPROVAL_REQUESTED: self._approval_requested,
            AgiEventType.APPROVAL_RESOLVED: self._approval_resolved,
            AgiEventType.EXTERNAL_WAIT_STARTED: self._external_wait_started,
            AgiEventType.EXTERNAL_WAIT_ENDED: self._external_wait_ended,
            AgiEventType.CHECKPOINT_CREATED: self._checkpoint_created,
        }
        handler = handlers.get(event.type)
        return handler(event) if handler else AgentEventReduction()

    def _task_start(self, event: AgiEvent) -> AgentEventReduction:
        self.store.add_task(
            event.task_id,
            {
                "id": event.task_id,
                "name": event.data.get("description", "Unnamed Task"),
                "objective": event.data.get("objective", ""),
                "status": "running",
                "started_at": event.timestamp,
                "children": {},
                "parent_id": event.parent_task_id,
            },
        )
        return AgentEventReduction()

    def _task_update(self, event: AgiEvent) -> AgentEventReduction:
        task = self._task_copy(event.task_id)
        if task is not None:
            incoming_status = str(event.data.get("status", task.get("status")))
            if not self._can_apply_transition(task, incoming_status, event.timestamp):
                return AgentEventReduction()
            task["status"] = incoming_status
            task["updated_at"] = event.timestamp
            task["message"] = event.data.get("message", "")
            if event.data.get("details"):
                task["details"] = deepcopy(event.data["details"])
            self.store.add_task(event.task_id, task)
        return AgentEventReduction()

    def _task_complete(self, event: AgiEvent) -> AgentEventReduction:
        task = self._task_copy(event.task_id)
        if task is not None:
            target_status = (
                "completed" if event.data.get("success", False) else "failed"
            )
            if not self._can_apply_transition(task, target_status, event.timestamp):
                return AgentEventReduction(hide_thinking=True)
            task.update(
                status=target_status,
                updated_at=event.timestamp,
                completed_at=event.timestamp,
                result=event.data.get("result"),
                error=event.data.get("error"),
            )
            self.store.add_task(event.task_id, task)
        return AgentEventReduction(hide_thinking=True)

    def _task_error(self, event: AgiEvent) -> AgentEventReduction:
        return self._set_task_lifecycle(
            event,
            "failed",
            hide_thinking=True,
            error=event.data.get("reason") or event.data.get("error"),
        )

    def _task_cancelled(self, event: AgiEvent) -> AgentEventReduction:
        return self._set_task_lifecycle(
            event,
            "cancelled",
            hide_thinking=True,
            reason=event.data.get("reason"),
        )

    def _task_interrupted(self, event: AgiEvent) -> AgentEventReduction:
        return self._set_task_lifecycle(
            event,
            "interrupted",
            hide_thinking=True,
            reason=event.data.get("reason"),
            resumable=bool(event.data.get("resumable", True)),
        )

    def _approval_requested(self, event: AgiEvent) -> AgentEventReduction:
        return self._set_task_lifecycle(
            event,
            "awaiting_user",
            pending_approval={
                "request_id": event.data.get("request_id"),
                "action": event.data.get("action"),
                "message": event.data.get("message"),
            },
        )

    def _approval_resolved(self, event: AgiEvent) -> AgentEventReduction:
        declined = event.data.get("status") == "declined"
        return self._set_task_lifecycle(
            event,
            "declined" if declined else "running",
            hide_thinking=declined,
            pending_approval=None,
            approval_resolution={
                "request_id": event.data.get("request_id"),
                "action": event.data.get("action"),
            },
        )

    def _external_wait_started(self, event: AgiEvent) -> AgentEventReduction:
        return self._set_task_lifecycle(
            event,
            "waiting_external",
            wait_reason=event.data.get("reason") or event.data.get("message"),
        )

    def _external_wait_ended(self, event: AgiEvent) -> AgentEventReduction:
        return self._set_task_lifecycle(
            event,
            "running",
            wait_reason=None,
        )

    def _checkpoint_created(self, event: AgiEvent) -> AgentEventReduction:
        task = self._task_copy(event.task_id)
        if task is not None:
            checkpoints = list(task.get("checkpoints", ()))
            checkpoints.append(
                {
                    "name": event.data.get("name"),
                    "artifacts": deepcopy(event.data.get("artifacts", [])),
                    "created_at": event.timestamp,
                }
            )
            task["checkpoints"] = checkpoints
            self.store.add_task(event.task_id, task)
        return AgentEventReduction()

    def _subtask_start(self, event: AgiEvent) -> AgentEventReduction:
        parent = self._task_copy(event.parent_task_id)
        if parent is not None and event.parent_task_id:
            parent.setdefault("children", {})[event.task_id] = {
                "id": event.task_id,
                "name": event.data.get("description", "Unnamed Subtask"),
                "status": "running",
                "started_at": event.timestamp,
                "parent_id": event.parent_task_id,
            }
            self.store.add_task(event.parent_task_id, parent)
        return AgentEventReduction()

    def _subtask_complete(self, event: AgiEvent) -> AgentEventReduction:
        parent = self._task_copy(event.parent_task_id)
        children = parent.get("children", {}) if parent else {}
        if parent is not None and event.parent_task_id and event.task_id in children:
            child = children[event.task_id]
            child["status"] = (
                "completed" if event.data.get("success", False) else "failed"
            )
            child["completed_at"] = event.timestamp
            self.store.add_task(event.parent_task_id, parent)
        return AgentEventReduction()

    def _tool_executing(self, event: AgiEvent) -> AgentEventReduction:
        parent_id, execution_id = self._tool_identity(event)
        parent = self._task_copy(parent_id)
        if parent is not None and parent_id:
            parent.setdefault("children", {})[execution_id] = {
                "id": execution_id,
                "name": f"Tool: {event.data.get('tool_name', 'Unknown')}",
                "tool_name": event.data.get("tool_name"),
                "tool_args": redact_tool_args(event.data.get("tool_args")),
                "status": "executing",
                "started_at": event.timestamp,
                "parent_id": parent_id,
            }
            self.store.add_task(parent_id, parent)
        rendered_args = safe_tool_args_json(event.data.get("tool_args"))
        return AgentEventReduction(
            chat=ChatEffect(
                "Tool",
                f"⚒ Executando tool: **{event.data.get('tool_name', 'Unknown')}**"
                f"\n\n```json\n{rendered_args}\n```",
                execution_id,
            )
        )

    def _tool_result(self, event: AgiEvent) -> AgentEventReduction:
        parent_id, execution_id = self._tool_identity(event)
        parent = self._task_copy(parent_id)
        children = parent.get("children", {}) if parent else {}
        if parent is not None and parent_id and execution_id in children:
            child = children[execution_id]
            child.update(
                status="completed" if event.data.get("success", False) else "failed",
                result=event.data.get("result"),
                error=event.data.get("error"),
                execution_time=event.data.get("execution_time"),
            )
            self.store.add_task(parent_id, parent)

        result = event.data.get("result")
        rendered_result = "" if result is None else str(result)
        if len(rendered_result) > self.result_limit:
            rendered_result = rendered_result[: self.result_limit] + "\n... (truncated)"
        elapsed = event.data.get("execution_time") or 0
        elapsed_text = (
            f"({elapsed:.2f}s)" if isinstance(elapsed, (int, float)) and elapsed else ""
        )
        icon = "✔" if event.data.get("success", False) else "✖"
        content = (
            f"{icon} **{event.data.get('tool_name', 'Unknown')}** {elapsed_text}"
            f"\n\n```\n{rendered_result}\n```"
        )
        if event.data.get("error"):
            content += f"\n\n✖ **Error:** {event.data['error']}"
        return AgentEventReduction(chat=ChatEffect("Tool", content, execution_id))

    def _chat_message(self, event: AgiEvent) -> AgentEventReduction:
        message = {
            "id": f"msg_{event.timestamp}",
            "sender": event.data.get("sender", "Unknown"),
            "content": event.data.get("content", ""),
            "timestamp": event.timestamp,
            "task_id": event.task_id,
            "metadata": deepcopy(event.data.get("metadata", {})),
        }
        self.store.add_message(message)
        return AgentEventReduction(
            chat=ChatEffect(message["sender"], message["content"], event.task_id),
            hide_thinking=True,
        )

    def _planning(self, event: AgiEvent) -> AgentEventReduction:
        task = self._task_copy(event.task_id)
        if task is not None:
            task["planning"] = event.data.get("plan", "")
            self.store.add_task(event.task_id, task)
        return AgentEventReduction()

    def _thinking(self, event: AgiEvent) -> AgentEventReduction:
        task = self._task_copy(event.task_id)
        if task is not None:
            task["thinking"] = event.data.get("thought", "")
            self.store.add_task(event.task_id, task)
        return AgentEventReduction(show_thinking_for=event.data.get("sender", "Aura"))

    def _task_copy(self, task_id: str | None) -> dict[str, Any] | None:
        if not task_id:
            return None
        task = self.store.get_task(task_id)
        return deepcopy(task) if task is not None else None

    def _set_task_lifecycle(
        self,
        event: AgiEvent,
        status: str,
        *,
        hide_thinking: bool = False,
        **updates: Any,
    ) -> AgentEventReduction:
        task = self._task_copy(event.task_id)
        if task is not None:
            if not self._can_apply_transition(task, status, event.timestamp):
                return AgentEventReduction(hide_thinking=hide_thinking)
            task["status"] = status
            task["updated_at"] = event.timestamp
            task.update(updates)
            self.store.add_task(event.task_id, task)
        return AgentEventReduction(hide_thinking=hide_thinking)

    @classmethod
    def _can_apply_transition(
        cls, task: dict[str, Any], incoming_status: str, timestamp: float
    ) -> bool:
        """Reject stale events and non-terminal transitions after terminality."""
        current_status = str(task.get("status", ""))
        if current_status in cls._TERMINAL_STATUSES:
            return False
        if current_status == "interrupted" and not task.get("resumable", True):
            return False
        current_timestamp = task.get("updated_at") or task.get("completed_at")
        return not (
            isinstance(current_timestamp, (int, float))
            and timestamp < current_timestamp
        )

    @staticmethod
    def _tool_identity(event: AgiEvent) -> tuple[str | None, str]:
        execution_id = str(event.data.get("execution_id") or event.task_id)
        parent_id = event.parent_task_id
        if parent_id is None and execution_id != event.task_id:
            parent_id = event.task_id
        return parent_id, execution_id


__all__ = [
    "AgentEventReduction",
    "AgentEventStateReducer",
    "AgentEventStore",
    "ChatEffect",
]
