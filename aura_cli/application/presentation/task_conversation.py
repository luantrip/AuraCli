"""Pure task-tree and focused-conversation presentation decisions."""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping, Sequence

from aura_cli.application.agents.events import AgiEvent, AgiEventType
from aura_cli.application.presentation.safe_payloads import (
    sanitize_event_for_presentation,
)

TaskTree = dict[str, dict[str, Any]]

_DIRECT_TASK_STATUSES = {
    AgiEventType.TASK_ERROR: "failed",
    AgiEventType.TASK_CANCELLED: "cancelled",
    AgiEventType.TASK_INTERRUPTED: "interrupted",
    AgiEventType.APPROVAL_REQUESTED: "awaiting_user",
    AgiEventType.EXTERNAL_WAIT_STARTED: "waiting_external",
    AgiEventType.EXTERNAL_WAIT_ENDED: "running",
}


def reduce_task_tree(tasks: Mapping[str, dict[str, Any]], event: AgiEvent) -> TaskTree:
    """Return the task tree produced by one AGI lifecycle event."""
    reduced: TaskTree = deepcopy(dict(tasks))
    task_id = event.task_id

    if event.type == AgiEventType.TASK_START:
        reduced[task_id] = _entry(event, "Unnamed Task", "pending")
    elif event.type == AgiEventType.TASK_UPDATE:
        _update_entry(reduced.get(task_id), event, event.data.get("status", "pending"))
    elif event.type == AgiEventType.TASK_COMPLETE:
        status = "completed" if event.data.get("success", False) else "failed"
        _update_entry(reduced.get(task_id), event, status)
    elif event.type in _DIRECT_TASK_STATUSES:
        _update_entry(reduced.get(task_id), event, _DIRECT_TASK_STATUSES[event.type])
    elif event.type == AgiEventType.APPROVAL_RESOLVED:
        status = "declined" if event.data.get("status") == "declined" else "running"
        _update_entry(reduced.get(task_id), event, status)
    elif event.type == AgiEventType.CHECKPOINT_CREATED:
        _update_entry(
            reduced.get(task_id),
            event,
            str(reduced.get(task_id, {}).get("status", "running")),
        )
    elif event.type == AgiEventType.SUBTASK_START:
        children = _children(reduced, event.parent_task_id)
        if children is not None:
            children[task_id] = _entry(event, "Unnamed Subtask", "pending")
    elif event.type == AgiEventType.SUBTASK_COMPLETE:
        status = "completed" if event.data.get("success", False) else "failed"
        _update_entry(_child(reduced, event.parent_task_id, task_id), event, status)
    elif event.type == AgiEventType.TOOL_EXECUTING:
        children = _children(reduced, event.parent_task_id)
        if children is not None:
            children[task_id] = {
                "name": f"Tool: {event.data.get('tool_name', 'Unknown')}",
                "event": sanitize_event_for_presentation(event),
                "status": "executing",
                "children": {},
            }
    elif event.type == AgiEventType.TOOL_RESULT:
        status = "completed" if event.data.get("success", False) else "failed"
        _update_entry(_child(reduced, event.parent_task_id, task_id), event, status)

    return reduced


def find_task_entry(
    tasks: Mapping[str, dict[str, Any]], task_id: str | None
) -> dict[str, Any] | None:
    """Find a task or descendant without exposing traversal to UI adapters."""
    if not task_id:
        return None
    for current_id, entry in tasks.items():
        if current_id == task_id:
            return entry
        found = find_task_entry(entry.get("children", {}), task_id)
        if found is not None:
            return found
    return None


def filter_conversation_messages(
    messages: Sequence[dict[str, Any]], focused_task_id: str | None
) -> list[dict[str, Any]]:
    """Select global and task-local messages for the current focus."""
    if not focused_task_id:
        return list(messages)
    return [
        message
        for message in messages
        if message.get("task_id") in (focused_task_id, "global_chat")
    ]


def _entry(event: AgiEvent, fallback_name: str, fallback_status: str) -> dict[str, Any]:
    return {
        "name": event.data.get("description", fallback_name),
        "event": sanitize_event_for_presentation(event),
        "status": event.data.get("status", fallback_status),
        "children": {},
    }


def _update_entry(entry: dict[str, Any] | None, event: AgiEvent, status: str) -> None:
    if entry is not None:
        entry["event"] = sanitize_event_for_presentation(event)
        entry["status"] = status


def _children(tasks: TaskTree, parent_id: str | None) -> TaskTree | None:
    parent = tasks.get(parent_id) if parent_id else None
    return parent.setdefault("children", {}) if parent is not None else None


def _child(
    tasks: TaskTree, parent_id: str | None, task_id: str
) -> dict[str, Any] | None:
    children = _children(tasks, parent_id)
    return children.get(task_id) if children is not None else None


__all__ = [
    "TaskTree",
    "filter_conversation_messages",
    "find_task_entry",
    "reduce_task_tree",
]
