"""Application agent events — Pydantic schema contracts for the status queue."""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class AgiEventType(str, Enum):
    """AGI event types."""

    TASK_START = "agi_task_start"
    TASK_UPDATE = "agi_task_update"
    TASK_COMPLETE = "agi_task_complete"
    TASK_ERROR = "agi_task_error"
    TOOL_EXECUTING = "tool_executing"
    TOOL_RESULT = "tool_result"
    CAPABILITY_DECISION = "capability_decision"
    SUBTASK_START = "subtask_start"
    SUBTASK_COMPLETE = "subtask_complete"
    PLANNING = "planning"
    THINKING = "thinking"
    CHAT_MESSAGE = "chat_message"
    CHECKPOINT_CREATED = "checkpoint_created"
    TASK_CANCELLED = "task_cancelled"
    TASK_INTERRUPTED = "task_interrupted"
    APPROVAL_REQUESTED = "approval_requested"
    APPROVAL_RESOLVED = "approval_resolved"
    EXTERNAL_WAIT_STARTED = "external_wait_started"
    EXTERNAL_WAIT_ENDED = "external_wait_ended"


class AgiEvent(BaseModel):
    """Base event for AGI communication transported via status_queue as dicts."""

    type: AgiEventType
    task_id: str
    timestamp: float = Field(default_factory=lambda: datetime.now().timestamp())
    data: Dict[str, Any] = Field(default_factory=dict)
    parent_task_id: Optional[str] = None

    model_config = {"use_enum_values": True}

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AgiEvent":
        return cls.model_validate(data)


class AgiTaskStartEvent(AgiEvent):
    """Event for AGI task start."""

    type: AgiEventType = AgiEventType.TASK_START

    @classmethod
    def create(
        cls,
        task_id: str,
        description: str,
        objective: str,
        parent_task_id: Optional[str] = None,
    ) -> "AgiTaskStartEvent":
        """Create task start event."""
        return cls(
            task_id=task_id,
            parent_task_id=parent_task_id,
            data={
                "description": description,
                "objective": objective,
                "status": "starting",
            },
        )


class AgiTaskUpdateEvent(AgiEvent):
    """Event for AGI task update."""

    type: AgiEventType = AgiEventType.TASK_UPDATE

    @classmethod
    def create(
        cls,
        task_id: str,
        status: str,
        message: str,
        details: Optional[Dict[str, Any]] = None,
    ) -> "AgiTaskUpdateEvent":
        """Create instance."""
        return cls(
            task_id=task_id,
            data={
                "status": status,
                "message": message,
                "details": details or {},
            },
        )


class AgiTaskCompleteEvent(AgiEvent):
    """Event for AGI task completion."""

    type: AgiEventType = AgiEventType.TASK_COMPLETE

    @classmethod
    def create(
        cls,
        task_id: str,
        success: bool,
        result: Optional[str] = None,
        error: Optional[str] = None,
        stats: Optional[Dict[str, Any]] = None,
    ) -> "AgiTaskCompleteEvent":
        """Create instance."""
        return cls(
            task_id=task_id,
            data={
                "success": success,
                "result": result,
                "error": error,
                "stats": stats or {},
                "status": "completed" if success else "failed",
            },
        )


class ToolExecutingEvent(AgiEvent):
    """Event for tool execution start."""

    type: AgiEventType = AgiEventType.TOOL_EXECUTING

    @classmethod
    def create(
        cls,
        task_id: str,
        tool_name: str,
        tool_args: Dict[str, Any],
        parent_task_id: Optional[str] = None,
        execution_id: Optional[str] = None,
    ) -> "ToolExecutingEvent":
        """Create instance."""
        return cls(
            task_id=task_id,
            parent_task_id=parent_task_id,
            data={
                "tool_name": tool_name,
                "tool_args": tool_args,
                "execution_id": execution_id or task_id,
                "status": "executing",
            },
        )


class ToolResultEvent(AgiEvent):
    """Event for tool execution result."""

    type: AgiEventType = AgiEventType.TOOL_RESULT

    @classmethod
    def create(
        cls,
        task_id: str,
        tool_name: str,
        success: bool,
        result: Any,
        error: Optional[str] = None,
        execution_time: Optional[float] = None,
        parent_task_id: Optional[str] = None,
        execution_id: Optional[str] = None,
    ) -> "ToolResultEvent":
        """Create instance."""
        return cls(
            task_id=task_id,
            parent_task_id=parent_task_id,
            data={
                "tool_name": tool_name,
                "execution_id": execution_id or task_id,
                "success": success,
                "result": result,
                "error": error,
                "execution_time": execution_time,
                "status": "completed" if success else "failed",
            },
        )


class CapabilityDecisionEvent(AgiEvent):
    """Event for an explainable capability evaluation or reservation."""

    type: AgiEventType = AgiEventType.CAPABILITY_DECISION

    @classmethod
    def create(
        cls,
        task_id: str,
        tool_name: str,
        *,
        allowed: bool,
        requires_confirmation: bool,
        risk_level: Optional[str] = None,
        reason: Optional[str] = None,
        phase: str,
        execution_id: Optional[str] = None,
    ) -> "CapabilityDecisionEvent":
        return cls(
            task_id=task_id,
            data={
                "tool_name": tool_name,
                "allowed": allowed,
                "requires_confirmation": requires_confirmation,
                "risk_level": risk_level,
                "reason": reason,
                "phase": phase,
                "execution_id": execution_id,
            },
        )


class ChatMessageEvent(AgiEvent):
    """Event for chat messages."""

    type: AgiEventType = AgiEventType.CHAT_MESSAGE

    @classmethod
    def create(
        cls,
        sender: str,
        content: str,
        task_id: str = "global_chat",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> "ChatMessageEvent":
        """Create instance."""
        return cls(
            task_id=task_id,
            data={
                "sender": sender,
                "content": content,
                "metadata": metadata or {},
            },
        )

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ChatMessageEvent":
        """Create from dictionary."""
        event_data = data.get("data", {})
        return cls(
            task_id=data.get("task_id", "global_chat"),
            timestamp=data.get("timestamp", datetime.now().timestamp()),
            data={
                "sender": event_data.get("sender", ""),
                "content": event_data.get("content", ""),
                "metadata": event_data.get("metadata", {}),
            },
        )


class LifecycleEvent(AgiEvent):
    """Explicit task lifecycle event beyond start/update/complete."""

    @classmethod
    def create(
        cls,
        event_type: AgiEventType,
        task_id: str,
        *,
        status: str,
        message: str,
        reason: Optional[str] = None,
        request_id: Optional[str] = None,
        action: Optional[str] = None,
        resumable: bool = False,
        details: Optional[Dict[str, Any]] = None,
        parent_task_id: Optional[str] = None,
        scope: str = "once",
        policy_key: Optional[str] = None,
    ) -> "LifecycleEvent":
        return cls(
            type=event_type,
            task_id=task_id,
            parent_task_id=parent_task_id,
            data={
                "status": status,
                "message": message,
                "reason": reason,
                "request_id": request_id,
                "action": action,
                "resumable": resumable,
                "details": details or {},
                "scope": scope,
                "policy_key": policy_key,
            },
        )


def create_task_start(task_id: str, description: str, objective: str) -> Dict[str, Any]:
    """Create task start event."""
    return AgiTaskStartEvent.create(task_id, description, objective).to_dict()


def create_task_update(task_id: str, status: str, message: str) -> Dict[str, Any]:
    """Create task update event."""
    return AgiTaskUpdateEvent.create(task_id, status, message).to_dict()


def create_task_complete(
    task_id: str, success: bool, result: Optional[str] = None
) -> Dict[str, Any]:
    """Create task complete event."""
    return AgiTaskCompleteEvent.create(task_id, success, result).to_dict()


def create_tool_executing(
    task_id: str,
    tool_name: str,
    tool_args: Dict[str, Any],
    *,
    parent_task_id: Optional[str] = None,
    execution_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Create tool executing event."""
    return ToolExecutingEvent.create(
        task_id,
        tool_name,
        tool_args,
        parent_task_id=parent_task_id,
        execution_id=execution_id,
    ).to_dict()


def create_tool_result(
    task_id: str,
    tool_name: str,
    success: bool,
    result: Any,
    *,
    parent_task_id: Optional[str] = None,
    execution_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Create tool result event."""
    return ToolResultEvent.create(
        task_id,
        tool_name,
        success,
        result,
        parent_task_id=parent_task_id,
        execution_id=execution_id,
    ).to_dict()


def create_capability_decision(
    task_id: str,
    tool_name: str,
    *,
    allowed: bool,
    requires_confirmation: bool,
    risk_level: Optional[str] = None,
    reason: Optional[str] = None,
    phase: str,
    execution_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Build a validated capability decision event for queue transport."""
    return CapabilityDecisionEvent.create(
        task_id,
        tool_name,
        allowed=allowed,
        requires_confirmation=requires_confirmation,
        risk_level=risk_level,
        reason=reason,
        phase=phase,
        execution_id=execution_id,
    ).to_dict()


def create_chat_message(
    sender: str, content: str, task_id: str = "global_chat"
) -> Dict[str, Any]:
    """Create chat message event."""
    return ChatMessageEvent.create(sender, content, task_id).to_dict()


def create_lifecycle_event(
    event_type: AgiEventType,
    task_id: str,
    *,
    status: str,
    message: str,
    reason: Optional[str] = None,
    request_id: Optional[str] = None,
    action: Optional[str] = None,
    resumable: bool = False,
    details: Optional[Dict[str, Any]] = None,
    parent_task_id: Optional[str] = None,
    scope: str = "once",
    policy_key: Optional[str] = None,
) -> Dict[str, Any]:
    """Build a validated explicit lifecycle event for queue transport."""
    return LifecycleEvent.create(
        event_type,
        task_id,
        status=status,
        message=message,
        reason=reason,
        request_id=request_id,
        action=action,
        resumable=resumable,
        details=details,
        parent_task_id=parent_task_id,
        scope=scope,
        policy_key=policy_key,
    ).to_dict()
