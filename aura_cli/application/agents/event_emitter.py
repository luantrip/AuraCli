"""Stateful producer of toolkit-neutral agent lifecycle events.

The emitter correlates tasks and tool executions, builds validated event payloads
and publishes them through a queue-like port. Worker and UI adapters may consume
the same contract without importing one another.
"""

import logging
from queue import Queue
from typing import Any, Dict, Optional
import uuid

from aura_cli.application.agents.events import (
    AgiEventType,
    create_capability_decision,
    create_chat_message,
    create_lifecycle_event,
    create_task_complete,
    create_task_start,
    create_task_update,
    create_tool_executing,
    create_tool_result,
)

logger = logging.getLogger(__name__)


def _safe_put(queue: Queue, event: Dict) -> None:
    """Publish an event already validated by its Pydantic constructor."""
    queue.put(event)


class AgiEventAdapter:
    """Emit correlated AGI lifecycle events to a queue-like sink."""

    def __init__(self, status_queue: Queue, task_id: Optional[str] = None):
        self.status_queue = status_queue
        self.current_task_id: Optional[str] = task_id
        self.active_tools: Dict[str, Dict[str, float]] = {}
        logger.debug(f"AgiEventAdapter initialized with task_id={task_id}")

    def start_task(self, description: str, objective: str) -> str:
        """Emit task start event and return the generated task_id."""
        self.current_task_id = f"agi_{uuid.uuid4().hex[:8]}"
        event = create_task_start(
            task_id=self.current_task_id, description=description, objective=objective
        )
        _safe_put(self.status_queue, event)
        logger.info(f"AGI task started: {self.current_task_id}")
        return self.current_task_id

    def update_task(self, status: str, message: str, details: Optional[Dict] = None):
        """Emit task update event."""
        if not self.current_task_id:
            logger.warning("Attempt to update task without active task_id")
            return
        event = create_task_update(
            task_id=self.current_task_id, status=status, message=message
        )
        if details:
            event["data"]["details"] = details
        _safe_put(self.status_queue, event)
        logger.debug(f"Task {self.current_task_id} updated: {status}")

    def complete_task(
        self,
        success: bool,
        result: Optional[str] = None,
        error: Optional[str] = None,
        stats: Optional[Dict[str, Any]] = None,
    ):
        """Emit task completion event."""
        if not self.current_task_id:
            logger.warning("Attempt to complete task without active task_id")
            return
        event = create_task_complete(
            task_id=self.current_task_id, success=success, result=result
        )
        if error:
            event["data"]["error"] = error
        if stats:
            event["data"]["stats"] = stats
        _safe_put(self.status_queue, event)
        logger.info(f"Task {self.current_task_id} completed: success={success}")
        self.current_task_id = None
        self.active_tools.clear()

    def emit_lifecycle(
        self,
        event_type: AgiEventType,
        *,
        status: str,
        message: str,
        reason: Optional[str] = None,
        request_id: Optional[str] = None,
        action: Optional[str] = None,
        resumable: bool = False,
        details: Optional[Dict[str, Any]] = None,
        terminal: bool = False,
        scope: str = "once",
        policy_key: Optional[str] = None,
    ) -> None:
        """Emit an explicit correlated lifecycle state for the active task."""
        if not self.current_task_id:
            logger.warning("Tentativa de emitir lifecycle sem task_id ativo")
            return
        event = create_lifecycle_event(
            event_type,
            self.current_task_id,
            status=status,
            message=message,
            reason=reason,
            request_id=request_id,
            action=action,
            resumable=resumable,
            details=details,
            scope=scope,
            policy_key=policy_key,
        )
        _safe_put(self.status_queue, event)
        if terminal:
            self.current_task_id = None
            self.active_tools.clear()

    def error_task(
        self, error: Any, *, details: Optional[Dict[str, Any]] = None
    ) -> None:
        self.emit_lifecycle(
            AgiEventType.TASK_ERROR,
            status="failed",
            message="Task failed",
            reason=str(error),
            details=details,
            terminal=True,
        )

    def cancel_task(self, reason: str = "cancelled by user") -> None:
        self.emit_lifecycle(
            AgiEventType.TASK_CANCELLED,
            status="cancelled",
            message="Task cancelled",
            reason=reason,
            terminal=True,
        )

    def interrupt_task(self, reason: str, *, resumable: bool = True) -> None:
        self.emit_lifecycle(
            AgiEventType.TASK_INTERRUPTED,
            status="interrupted",
            message="Task interrupted",
            reason=reason,
            resumable=resumable,
        )

    def start_external_wait(
        self, message: str, *, reason: Optional[str] = None
    ) -> None:
        self.emit_lifecycle(
            AgiEventType.EXTERNAL_WAIT_STARTED,
            status="waiting_external",
            message=message,
            reason=reason,
            resumable=True,
        )

    def end_external_wait(self, message: str = "External wait resolved") -> None:
        self.emit_lifecycle(
            AgiEventType.EXTERNAL_WAIT_ENDED,
            status="running",
            message=message,
        )

    def request_approval(
        self,
        request_id: str,
        message: str,
        *,
        action: str,
        scope: str = "once",
        policy_key: str | None = None,
    ) -> None:
        self.emit_lifecycle(
            AgiEventType.APPROVAL_REQUESTED,
            status="awaiting_user",
            message=message,
            request_id=request_id,
            action=action,
            scope=scope,
            policy_key=policy_key,
            resumable=True,
        )

    def resolve_approval(
        self,
        request_id: str,
        *,
        approved: bool,
        message: str = "Approval resolved",
        scope: str = "once",
    ) -> None:
        self.emit_lifecycle(
            AgiEventType.APPROVAL_RESOLVED,
            status="running" if approved else "declined",
            message=message,
            request_id=request_id,
            action="approved" if approved else "declined",
            scope=scope,
            terminal=not approved,
        )

    def checkpoint_created(self, name: str, artifact: str) -> None:
        if not self.current_task_id:
            return
        _safe_put(
            self.status_queue,
            {
                "type": AgiEventType.CHECKPOINT_CREATED.value,
                "task_id": self.current_task_id,
                "data": {
                    "name": name,
                    "status": "completed",
                    "message": "Checkpoint created",
                    "artifacts": [artifact],
                    "resumable": True,
                },
            },
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
        if not self.current_task_id:
            logger.warning("Tentativa de auditar capability sem task_id ativo")
            return
        risk_level = getattr(decision, "risk_level", None)
        if risk_level is not None:
            risk_level = getattr(risk_level, "value", str(risk_level))
        event = create_capability_decision(
            task_id=self.current_task_id,
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
        _safe_put(self.status_queue, event)

    def tool_executing(
        self,
        tool_name: str,
        args: Dict[str, Any],
        execution_id: Optional[str] = None,
    ) -> str | None:
        """Emit tool execution start event and return the execution_id."""
        if not self.current_task_id:
            logger.warning(
                f"Tentativa de executar ferramenta {tool_name} sem task_id ativo"
            )
            return None

        import time

        execution_id = execution_id or f"tool_{uuid.uuid4().hex[:10]}"
        self.active_tools.setdefault(tool_name, {})[execution_id] = time.time()

        event = create_tool_executing(
            task_id=self.current_task_id,
            tool_name=tool_name,
            tool_args=args,
            execution_id=execution_id,
        )

        _safe_put(self.status_queue, event)
        logger.debug(
            f"Ferramenta {tool_name} iniciada na tarefa {self.current_task_id}"
        )
        return execution_id

    def tool_result(
        self,
        tool_name: str,
        success: bool,
        result: Any,
        error: Optional[str] = None,
        execution_id: Optional[str] = None,
    ):
        """Emit tool execution result event."""
        if not self.current_task_id:
            logger.warning(
                f"Tentativa de reportar resultado de {tool_name} sem task_id ativo"
            )
            return

        import time

        execution_time = None
        pending = self.active_tools.get(tool_name, {})
        if execution_id is None and pending:
            execution_id = next(iter(pending))
        if execution_id is not None and execution_id in pending:
            started_at = pending.pop(execution_id)
            execution_time = time.time() - started_at
            if not pending:
                self.active_tools.pop(tool_name, None)

        event = create_tool_result(
            task_id=self.current_task_id,
            tool_name=tool_name,
            success=success,
            result=result,
            execution_id=execution_id,
        )

        if error:
            event["data"]["error"] = error
        if execution_time:
            event["data"]["execution_time"] = execution_time

        _safe_put(self.status_queue, event)
        logger.debug(
            f"Ferramenta {tool_name} concluída: success={success}, time={execution_time:.2f}s"
            if execution_time
            else f"Ferramenta {tool_name} concluída: success={success}"
        )

    def get_current_task_id(self) -> Optional[str]:
        """Return the current task ID."""
        return self.current_task_id

    def is_task_active(self) -> bool:
        """Return True if a task is currently active."""
        return self.current_task_id is not None

    def emit_chat_message(
        self, sender: str, content: str, task_id: Optional[str] = None
    ):
        """Emit a chat message event."""
        effective_task_id = task_id or self.current_task_id or "global_chat"
        event = create_chat_message(
            sender=sender, content=content, task_id=effective_task_id
        )
        _safe_put(self.status_queue, event)
        logger.debug(
            f"Chat message emitida: sender={sender}, task_id={effective_task_id}"
        )
