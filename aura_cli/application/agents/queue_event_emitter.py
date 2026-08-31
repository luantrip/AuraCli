"""Queue-backed application event emitter used by operational agents.

Emits structured events to a status_queue so that consumers (planner, validator)
work identically regardless of worker type.
"""

import time
from typing import Any, Dict, Optional
import uuid


class QueueAgiAdapter:
    """Adapter to make status_queue look like AgiEventAdapter for shared components."""

    def __init__(self, status_queue, task_id: str = "ops"):
        """Initialize the ops worker with a status queue and task identifier."""
        self.status_queue = status_queue
        self.current_task_id = task_id
        self._terminal_event_emitted = False
        self.active_tools: Dict[str, Dict[str, float]] = {}

    def emit_chat_message(
        self, sender: str, content: str, task_id: Optional[str] = None, **kwargs
    ):
        """Emit structured chat message to queue."""
        from aura_cli.application.agents.events import create_chat_message

        effective_task_id = task_id or self.current_task_id or "ops"
        event = create_chat_message(
            sender=sender, content=content, task_id=effective_task_id
        )
        self.status_queue.put(event)

    def update_task(
        self,
        status: str,
        message: str,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Emit structured task update event for supervisor-aware UI feedback."""
        from aura_cli.application.agents.events import create_task_update

        event = create_task_update(
            task_id=self.current_task_id or "ops",
            status=status,
            message=message,
        )
        if details:
            event["data"]["details"] = details
        self.status_queue.put(event)

    def complete_task(
        self,
        success: bool,
        result: Optional[str] = None,
        error: Optional[str] = None,
        stats: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Emit one task completion event (idempotent — guards against duplicate terminal events)."""
        if self._terminal_event_emitted:
            return
        self._terminal_event_emitted = True
        from aura_cli.application.agents.events import create_task_complete

        event = create_task_complete(
            task_id=self.current_task_id or "ops",
            success=success,
            result=result,
        )
        if error:
            event["data"]["error"] = error
        if stats:
            event["data"]["stats"] = stats
        self.status_queue.put(event)
        self.active_tools.clear()

    def tool_executing(
        self,
        tool_name: str,
        args: Dict[str, Any],
        execution_id: Optional[str] = None,
    ) -> str:
        """Emit a correlated tool-start event for the Ops runtime."""
        from aura_cli.application.agents.events import create_tool_executing

        execution_id = execution_id or f"tool_{uuid.uuid4().hex[:10]}"
        self.active_tools.setdefault(tool_name, {})[execution_id] = time.time()
        self.status_queue.put(
            create_tool_executing(
                task_id=self.current_task_id or "ops",
                tool_name=tool_name,
                tool_args=args,
                execution_id=execution_id,
            )
        )
        return execution_id

    def tool_result(
        self,
        tool_name: str,
        success: bool,
        result: Any,
        error: Optional[str] = None,
        execution_id: Optional[str] = None,
    ) -> None:
        """Emit a correlated tool-result event for the Ops runtime."""
        from aura_cli.application.agents.events import create_tool_result

        pending = self.active_tools.get(tool_name, {})
        if execution_id is None and pending:
            execution_id = next(iter(pending))
        execution_time = None
        if execution_id is not None and execution_id in pending:
            execution_time = time.time() - pending.pop(execution_id)
            if not pending:
                self.active_tools.pop(tool_name, None)
        event = create_tool_result(
            task_id=self.current_task_id or "ops",
            tool_name=tool_name,
            success=success,
            result=result,
            execution_id=execution_id,
        )
        if error:
            event["data"]["error"] = error
        if execution_time is not None:
            event["data"]["execution_time"] = execution_time
        self.status_queue.put(event)

    def emit_lifecycle(
        self,
        event_type,
        *,
        status: str,
        message: str,
        reason: Optional[str] = None,
        request_id: Optional[str] = None,
        action: Optional[str] = None,
        resumable: bool = False,
        details: Optional[Dict[str, Any]] = None,
        **_kwargs,
    ) -> None:
        from aura_cli.application.agents.events import create_lifecycle_event

        self.status_queue.put(
            create_lifecycle_event(
                event_type,
                self.current_task_id or "ops",
                status=status,
                message=message,
                reason=reason,
                request_id=request_id,
                action=action,
                resumable=resumable,
                details=details,
            )
        )

    def capability_decision(
        self,
        tool_name: str,
        decision: Any,
        *,
        phase: str,
        execution_id: Optional[str] = None,
    ) -> None:
        """Emit a task-correlated, argument-free capability audit event."""
        from aura_cli.application.agents.events import create_capability_decision

        risk_level = getattr(decision, "risk_level", None)
        if risk_level is not None:
            risk_level = getattr(risk_level, "value", str(risk_level))
        self.status_queue.put(
            create_capability_decision(
                task_id=self.current_task_id or "ops",
                tool_name=tool_name,
                allowed=bool(getattr(decision, "allowed", False)),
                requires_confirmation=bool(
                    getattr(decision, "requires_confirmation", False)
                ),
                risk_level=risk_level,
                reason=getattr(decision, "reason", None),
                phase=phase,
                execution_id=execution_id,
            )
        )

    def error_task(
        self, error: Any, *, details: Optional[Dict[str, Any]] = None
    ) -> None:
        if self._terminal_event_emitted:
            return
        self._terminal_event_emitted = True
        from aura_cli.application.agents.events import AgiEventType

        self.emit_lifecycle(
            AgiEventType.TASK_ERROR,
            status="failed",
            message="Task failed",
            reason=str(error),
            details=details,
        )

    def cancel_task(self, reason: str = "cancelled by user") -> None:
        if self._terminal_event_emitted:
            return
        self._terminal_event_emitted = True
        from aura_cli.application.agents.events import AgiEventType

        self.emit_lifecycle(
            AgiEventType.TASK_CANCELLED,
            status="cancelled",
            message="Task cancelled",
            reason=reason,
        )

    def interrupt_task(self, reason: str, *, resumable: bool = True) -> None:
        from aura_cli.application.agents.events import AgiEventType

        self.emit_lifecycle(
            AgiEventType.TASK_INTERRUPTED,
            status="interrupted",
            message="Task interrupted",
            reason=reason,
            resumable=resumable,
        )

    def request_approval(self, request_id: str, message: str, *, action: str) -> None:
        from aura_cli.application.agents.events import AgiEventType

        self.emit_lifecycle(
            AgiEventType.APPROVAL_REQUESTED,
            status="awaiting_user",
            message=message,
            request_id=request_id,
            action=action,
            resumable=True,
        )

    def resolve_approval(
        self, request_id: str, *, approved: bool, message: str = "Approval resolved"
    ) -> None:
        from aura_cli.application.agents.events import AgiEventType

        self.emit_lifecycle(
            AgiEventType.APPROVAL_RESOLVED,
            status="running" if approved else "declined",
            message=message,
            request_id=request_id,
            action="approved" if approved else "declined",
        )

    def checkpoint_created(self, name: str, artifact: str) -> None:
        from aura_cli.application.agents.events import AgiEventType

        self.status_queue.put(
            {
                "type": AgiEventType.CHECKPOINT_CREATED.value,
                "task_id": self.current_task_id or "ops",
                "data": {
                    "name": name,
                    "status": "completed",
                    "message": "Checkpoint created",
                    "artifacts": [artifact],
                    "resumable": True,
                },
            }
        )
