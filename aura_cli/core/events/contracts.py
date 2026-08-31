"""
Unified Event Contract — shared schema between CoreEventBus and TUIEventBus.

This module defines the single source of truth for event payloads.
Both the core thread-based bus and the TUI async bus validate against
these Pydantic models, eliminating the "event abyss" risk.

Architecture:
    CoreEventBus  ──┐
                    ├──► EventContract (Pydantic) ◄── SyncManager ──► TUIEventBus
    Workers ────────┘

Usage:
    >>> from aura_cli.core.events.contracts import TaskStartPayload, validate_event
    >>> payload = validate_event("agi_task_start", raw_dict)
"""

from __future__ import annotations

from typing import Any, Dict, Optional, Type

from pydantic import BaseModel, Field

from aura_cli.core.events.agi_events import AgiEventType

# Payload schemas — one per AgiEventType


class TaskStartPayload(BaseModel):
    """Payload for task start events."""

    description: str
    objective: str
    status: str = "starting"


class TaskUpdatePayload(BaseModel):
    """Payload for task progress update events."""

    status: str
    message: str
    details: Dict[str, Any] = Field(default_factory=dict)


class TaskCompletePayload(BaseModel):
    """Payload for task completion events."""

    success: bool
    result: Optional[str] = None
    error: Optional[str] = None
    stats: Dict[str, Any] = Field(default_factory=dict)
    status: str = "completed"


class ToolExecutingPayload(BaseModel):
    """Payload for tool execution start events."""

    tool_name: str
    tool_args: Dict[str, Any] = Field(default_factory=dict)
    execution_id: Optional[str] = None
    status: str = "executing"


class CapabilityDecisionPayload(BaseModel):
    """Payload for explainable capability evaluations and commits."""

    tool_name: str
    allowed: bool
    requires_confirmation: bool = False
    risk_level: Optional[str] = None
    reason: Optional[str] = None
    phase: str
    execution_id: Optional[str] = None


class ToolResultPayload(BaseModel):
    """Payload for tool execution result events."""

    tool_name: str
    execution_id: Optional[str] = None
    success: bool
    result: Any = None
    error: Optional[str] = None
    execution_time: Optional[float] = None
    status: str = "completed"


class ChatMessagePayload(BaseModel):
    """Payload for chat message events."""

    sender: str
    content: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


class SubtaskPayload(BaseModel):
    """Payload for subtask events."""

    subtask_id: str
    description: str
    status: str = "starting"


class PlanningPayload(BaseModel):
    """Payload for planning phase events."""

    plan: str
    steps: list = Field(default_factory=list)


class ThinkingPayload(BaseModel):
    """Payload for LLM thinking events."""

    thought: str


class LifecyclePayload(BaseModel):
    """Payload for explicit cancellation, interruption, approval, and waits."""

    status: str
    message: str
    reason: Optional[str] = None
    request_id: Optional[str] = None
    action: Optional[str] = None
    resumable: bool = False
    details: Dict[str, Any] = Field(default_factory=dict)


class CheckpointPayload(BaseModel):
    """Payload for a recoverable checkpoint artifact."""

    name: str
    status: str = "completed"
    message: str = "Checkpoint created"
    artifacts: list[str] = Field(default_factory=list)
    resumable: bool = True


# Registry: AgiEventType → payload schema

_PAYLOAD_REGISTRY: Dict[str, Type[BaseModel]] = {
    AgiEventType.TASK_START: TaskStartPayload,
    AgiEventType.TASK_UPDATE: TaskUpdatePayload,
    AgiEventType.TASK_COMPLETE: TaskCompletePayload,
    AgiEventType.TASK_ERROR: LifecyclePayload,
    AgiEventType.TOOL_EXECUTING: ToolExecutingPayload,
    AgiEventType.TOOL_RESULT: ToolResultPayload,
    AgiEventType.CAPABILITY_DECISION: CapabilityDecisionPayload,
    AgiEventType.SUBTASK_START: SubtaskPayload,
    AgiEventType.SUBTASK_COMPLETE: SubtaskPayload,
    AgiEventType.PLANNING: PlanningPayload,
    AgiEventType.THINKING: ThinkingPayload,
    AgiEventType.CHAT_MESSAGE: ChatMessagePayload,
    AgiEventType.CHECKPOINT_CREATED: CheckpointPayload,
    AgiEventType.TASK_CANCELLED: LifecyclePayload,
    AgiEventType.TASK_INTERRUPTED: LifecyclePayload,
    AgiEventType.APPROVAL_REQUESTED: LifecyclePayload,
    AgiEventType.APPROVAL_RESOLVED: LifecyclePayload,
    AgiEventType.EXTERNAL_WAIT_STARTED: LifecyclePayload,
    AgiEventType.EXTERNAL_WAIT_ENDED: LifecyclePayload,
}


def get_payload_schema(event_type: str) -> Optional[Type[BaseModel]]:
    """Return the Pydantic schema for a given event type string, or None."""
    return _PAYLOAD_REGISTRY.get(event_type)


def validate_event(event_type: str, data: Dict[str, Any]) -> Optional[BaseModel]:
    """
    Validate event data against its registered schema.

    Args:
        event_type: AgiEventType value string (e.g. "agi_task_start")
        data: Raw payload dict

    Returns:
        Validated Pydantic model instance, or None if no schema registered.

    Raises:
        pydantic.ValidationError: If data does not match the schema.
    """
    schema = get_payload_schema(event_type)
    if schema is None:
        return None
    return schema.model_validate(data)


def is_valid_event(event_type: str, data: Dict[str, Any]) -> bool:
    """Return True only when a registered schema validates the payload."""
    try:
        return validate_event(event_type, data) is not None
    except Exception:
        return False
