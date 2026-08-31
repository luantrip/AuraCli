"""UIEventManager - Handles background event listening.

This module manages the AGI event listener thread and processes events
from the status queue, updating the UI via the RenderCoordinator.
"""

from queue import Empty
from threading import Thread
import time
from typing import Any, Dict, List, Optional

from aura_cli.application.agents.events import (
    AgiEvent,
    AgiEventType,
)
from aura_cli.application.presentation.activity_feed import (
    ActivityFeed,
    reduce_activity,
)
from aura_cli.application.presentation.approvals import (
    ApprovalCenter,
    approval_request_from_event,
    approval_resolution_from_event,
    request_approval,
    resolve_approval,
)
from aura_cli.application.presentation.attention_delivery import (
    AttentionDeliveryState,
    AttentionPreferences,
    decide_attention_delivery,
)
from aura_cli.application.presentation.safe_payloads import redact_tool_args
from aura_cli.application.presentation.tui_surfaces import (
    PresentationIntent,
    SurfaceKind,
    decide_surface,
)
from aura_cli.application.presentation.work_item_projection import (
    ProjectionTone,
    RealtimeProjectionReducer,
    project_work_item,
)
from aura_cli.application.presentation.work_items import work_item_from_agent_event
from aura_cli.cli.ui.components.agi_task_window import AgiTaskWindow
from aura_cli.cli.ui.components.message_bubble import MessageBubble
from aura_cli.cli.ui.rendering import RenderCoordinator
from aura_cli.cli.utils.thread_manager import get_thread_manager
from aura_cli.core.events.contracts import is_valid_event
from aura_cli.core.logger import get_logger

logger = get_logger(__name__)


class UIEventManager:
    """AGI event listener manager."""

    def __init__(self, status_queue, render_coordinator: RenderCoordinator):
        """Initialize the event manager with a status queue and render coordinator."""
        self.status_queue = status_queue
        self.render = render_coordinator
        self._event_listener_thread: Optional[Thread] = None
        self._stop_listening = False
        self._active_agi_tasks: Dict[str, AgiTaskWindow] = {}
        self._rendered_terminal_tasks: set[str] = set()
        self._chat_messages: List[MessageBubble] = []
        self._last_operational_key: str = ""
        self._last_operational_render_at: float = 0.0
        self._last_supervisor_notifications: Dict[str, str] = {}
        self._supervisor_states: Dict[str, str] = {}
        self.activity_feed = ActivityFeed()
        self._projection_reducer = RealtimeProjectionReducer()
        self.approval_center = ApprovalCenter()
        self.attention_delivery_state = AttentionDeliveryState()
        self.attention_preferences = AttentionPreferences()

    def _set_supervisor_notification(
        self,
        task_id: str,
        message: str,
        *,
        awaiting_human: bool = False,
        supervisor_state: Optional[str] = None,
    ) -> None:
        """Surface a short supervisor-state summary in the status bar."""
        stats = getattr(self.render, "stats", None)
        if not stats or not hasattr(stats, "set_notification"):
            return
        signature = f"{task_id}:{supervisor_state or ''}:{message}:{awaiting_human}"
        if self._last_supervisor_notifications.get(task_id) == signature:
            return
        self._last_supervisor_notifications[task_id] = signature
        prefix = "[bold yellow]SUPERVISOR[/bold yellow]"
        state_label = f"[{str(supervisor_state).upper()}] " if supervisor_state else ""
        body = f"[{task_id}] {state_label}{message}"
        duration = 12.0 if awaiting_human else 6.0
        stats.set_notification(f"{prefix} {body}", duration_seconds=duration)

    def _update_supervisor_state(self, task_id: str, supervisor_state: str) -> bool:
        """Track supervisor-state transitions per task."""
        previous = self._supervisor_states.get(task_id)
        if previous == supervisor_state:
            return False
        self._supervisor_states[task_id] = supervisor_state
        return True

    def get_supervisor_state(self, task_id: str) -> Optional[str]:
        """Return the current tracked supervisor state for a task."""
        return self._supervisor_states.get(task_id)

    def start_listener(self):
        """
        Inicia thread que escuta eventos AGI da status_queue.
        """
        if not self.status_queue:
            logger.warning("status_queue não disponível, listener AGI não iniciado")
            return

        if self._event_listener_thread and self._event_listener_thread.is_alive():
            logger.warning("Listener AGI já está rodando")
            return

        self._stop_listening = False

        def event_listener_wrapper():
            """Wrapper for event listener loop."""
            try:
                self._event_listener_loop()
            except (KeyboardInterrupt, SystemExit):
                raise
            except Exception as e:
                logger.error(f"Event listener thread error: {e}", exc_info=True)

        thread_manager = get_thread_manager()
        thread_name = f"ui_event_listener_{id(self)}"
        self._event_listener_thread = thread_manager.register_thread(
            name=thread_name,
            target=event_listener_wrapper,
            daemon=True,
            shutdown_timeout=5.0,
        )
        logger.info("Thread de listener AGI iniciada")

    def stop_listener(self):
        """Stop the event listener thread."""
        if self._event_listener_thread:
            thread_manager = get_thread_manager()
            thread_name = (
                self._event_listener_thread.name
                if hasattr(self._event_listener_thread, "name")
                else None
            )
            if thread_name:
                logger.info("Parando listener de eventos AGI...")
                self._stop_listening = True
                thread_manager.stop_thread(thread_name, timeout=2.0)
                logger.info("Listener de eventos AGI parado")
            elif self._event_listener_thread.is_alive():
                logger.info("Parando listener de eventos AGI...")
                self._stop_listening = True
                self._event_listener_thread.join(timeout=2.0)
                logger.info("Listener de eventos AGI parado")

    def _event_listener_loop(self):
        """Loop principal do listener."""
        logger.info("Listener de eventos AGI iniciado")
        while not self._stop_listening:
            try:
                event_dict = self.status_queue.get(timeout=0.1)
                self._process_agi_event(event_dict)
            except Empty:
                self._render_realtime_heartbeats()
                continue
            except (AttributeError, KeyError, TypeError) as e:
                logger.error(
                    f"Error processing AGI event (attribute/key/type): {e}",
                    exc_info=True,
                )
            except Exception as e:
                logger.error(
                    f"Unexpected error processing AGI event: {e}", exc_info=True
                )

        logger.info("Listener de eventos AGI parado")

    def _process_agi_event(self, event_dict: Dict[str, Any]):
        """Process an AGI event payload."""
        try:
            if self._process_intervention_request(event_dict):
                return

            if not isinstance(event_dict, dict):
                logger.warning("Evento AGI descartado: payload não é um objeto")
                return
            event_type = event_dict.get("type")
            if event_type == AgiEventType.TASK_COMPLETE and not is_valid_event(
                event_type, event_dict.get("data", {})
            ):
                logger.warning(
                    "Evento AGI descartado por falha de contrato: %s",
                    event_type or "<missing type>",
                )
                return

            event = AgiEvent.from_dict(event_dict)

            if event.type == AgiEventType.APPROVAL_REQUESTED:
                self.approval_center = request_approval(
                    self.approval_center, approval_request_from_event(event)
                )
            elif event.type == AgiEventType.APPROVAL_RESOLVED:
                self.approval_center = resolve_approval(
                    self.approval_center, approval_resolution_from_event(event)
                )

            self._dispatch_event(event)

            self._render_surface_requests(event)

            # Render all active content after processing event
            self._render_all_content()

        except (AttributeError, KeyError, TypeError) as e:
            logger.error(
                f"Error processing AGI event (attribute/key/type): {e}", exc_info=True
            )
        except Exception as e:
            logger.error(f"Unexpected error processing AGI event: {e}", exc_info=True)

    def _process_intervention_request(self, event_dict: Dict[str, Any]) -> bool:
        """Present a worker intervention request and report whether it was consumed."""
        if event_dict.get("type") != "human_intervention_request":
            return False
        task_id = str(event_dict.get("task_id") or "task")
        self._update_supervisor_state(task_id, "awaiting_human")
        self._set_supervisor_notification(
            task_id,
            "awaiting human decision",
            awaiting_human=True,
            supervisor_state="awaiting_human",
        )
        self.render.render_warning(
            f"[{task_id}] [SUPERVISOR:AWAITING_HUMAN] "
            "Agent is waiting for a human decision"
        )
        from aura_cli.cli.helpers import _handle_intervention_request

        _handle_intervention_request(event_dict)
        return True

    def _dispatch_event(self, event: AgiEvent) -> None:
        """Route a normalized lifecycle event to its local projection handler."""
        handlers = {
            AgiEventType.TASK_START: self._handle_task_start,
            AgiEventType.TASK_UPDATE: self._handle_task_update,
            AgiEventType.TASK_COMPLETE: self._handle_task_complete,
            AgiEventType.TASK_CANCELLED: self._handle_task_cancelled,
            AgiEventType.TOOL_EXECUTING: self._handle_tool_executing,
            AgiEventType.TOOL_RESULT: self._handle_tool_result,
            AgiEventType.SUBTASK_START: self._handle_subtask_start,
            AgiEventType.SUBTASK_COMPLETE: self._handle_subtask_complete,
            AgiEventType.CHAT_MESSAGE: self._handle_chat_message,
        }
        handler = handlers.get(event.type)
        if handler is not None:
            handler(event)
            return
        if event.type == AgiEventType.TASK_ERROR:
            failed = event.model_copy(
                update={
                    "data": {
                        **event.data,
                        "success": False,
                        "error": event.data.get("reason") or event.data.get("error"),
                    }
                }
            )
            self._handle_task_complete(failed)
            return
        if event.type in {
            AgiEventType.TASK_INTERRUPTED,
            AgiEventType.APPROVAL_REQUESTED,
            AgiEventType.APPROVAL_RESOLVED,
            AgiEventType.EXTERNAL_WAIT_STARTED,
            AgiEventType.EXTERNAL_WAIT_ENDED,
            AgiEventType.CHECKPOINT_CREATED,
        }:
            self._handle_task_update(event)

    def _handle_task_cancelled(self, event: AgiEvent):
        """Project cancellation as a terminal task-window state."""
        task_id = event.task_id
        reason = event.data.get("cancel_reason") or event.data.get("reason")
        self._update_supervisor_state(task_id, "returned_to_chat")
        if task_id in self._active_agi_tasks:
            self._active_agi_tasks[task_id].cancel(
                str(reason) if reason else event.data.get("message")
            )
            logger.debug("Task %s cancelled", task_id)

    def _handle_task_start(self, event: AgiEvent):
        """Handle a task-start event."""
        task_id = event.task_id
        data = event.data
        self._update_supervisor_state(task_id, "delegated")

        window = AgiTaskWindow(
            task_id=task_id,
            description=data.get("description", "Tarefa AGI"),
            objective=data.get("objective", ""),
            parent_task_id=event.parent_task_id,
        )

        self._active_agi_tasks[task_id] = window
        logger.debug(f"AGI window created for task {task_id}")

    def _handle_task_update(self, event: AgiEvent):
        """Handle a task-update event."""
        task_id = event.task_id
        details = event.data.get("details", {}) or {}
        supervisor_state = details.get("supervisor_state")
        fallback_reason = details.get("fallback_reason")
        if supervisor_state:
            self._update_supervisor_state(task_id, str(supervisor_state))
        elif event.data.get("status") not in {"returned_to_chat", "awaiting_human"}:
            self._update_supervisor_state(task_id, "in_progress")

        if task_id in self._active_agi_tasks:
            window = self._active_agi_tasks[task_id]
            data = event.data
            window.update_status(
                status=data.get("status", "running"),
                message=data.get("message"),
                supervisor_state=str(supervisor_state) if supervisor_state else None,
                fallback_reason=str(fallback_reason) if fallback_reason else None,
            )
            logger.debug(f"Task {task_id} updated: {data.get('status')}")

    def _handle_task_complete(self, event: AgiEvent):
        """Handle a task-complete event."""
        task_id = event.task_id
        stats = event.data.get("stats", {}) or {}
        supervisor_state = stats.get("supervisor_state")
        fallback_reason = stats.get("fallback_reason")
        if event.data.get("success", False):
            self._update_supervisor_state(task_id, "completed")
        elif supervisor_state:
            self._update_supervisor_state(task_id, str(supervisor_state))
        else:
            self._update_supervisor_state(task_id, "returned_to_chat")

        if task_id in self._active_agi_tasks:
            window = self._active_agi_tasks[task_id]
            data = event.data
            window.complete(
                success=data.get("success", False),
                result=data.get("result"),
                error=data.get("error"),
                supervisor_state=str(supervisor_state) if supervisor_state else None,
                fallback_reason=str(fallback_reason) if fallback_reason else None,
            )
            logger.debug(f"Task {task_id} completed: success={data.get('success')}")

    def _handle_tool_executing(self, event: AgiEvent):
        """Handle a tool-executing event."""
        task_id = event.task_id

        if task_id in self._active_agi_tasks:
            window = self._active_agi_tasks[task_id]
            data = event.data
            window.add_tool_execution(
                tool_name=data.get("tool_name", "unknown"),
                args=redact_tool_args(data.get("tool_args")),
            )
            logger.debug(
                f"Ferramenta {data.get('tool_name')} iniciada na tarefa {task_id}"
            )

    def _handle_tool_result(self, event: AgiEvent):
        """Complete a tool execution with its result."""
        task_id = event.task_id
        data = event.data

        if task_id in self._active_agi_tasks:
            window = self._active_agi_tasks[task_id]
            tool_name = data.get("tool_name", "unknown")
            result = data.get("result")
            success = data.get("success", False)

            # Update tool status in window
            if hasattr(window, "complete_tool_execution"):
                window.complete_tool_execution(
                    tool_name=tool_name,
                    result=result,
                    success=success,
                )
            logger.debug(
                f"Ferramenta {tool_name} concluída na tarefa {task_id}: success={success}"
            )

    def _handle_subtask_start(self, event: AgiEvent):
        """Handle a subtask-start event."""
        task_id = event.task_id
        parent_id = event.parent_task_id
        data = event.data

        if parent_id and parent_id in self._active_agi_tasks:
            parent_window = self._active_agi_tasks[parent_id]
            if hasattr(parent_window, "add_subtask"):
                parent_window.add_subtask(
                    subtask_id=task_id,
                    description=data.get("description", "Subtarefa"),
                )
            logger.debug(f"Subtask {task_id} started in {parent_id}")

    def _handle_subtask_complete(self, event: AgiEvent):
        """Handle a subtask-complete event."""
        task_id = event.task_id
        parent_id = event.parent_task_id
        data = event.data

        if parent_id and parent_id in self._active_agi_tasks:
            parent_window = self._active_agi_tasks[parent_id]
            if hasattr(parent_window, "complete_subtask"):
                parent_window.complete_subtask(
                    subtask_id=task_id,
                    success=data.get("success", False),
                    result=data.get("result"),
                )
            logger.debug(f"Subtask {task_id} completed in {parent_id}")

    def _handle_chat_message(self, event: AgiEvent):
        """Handle a chat-message event."""
        data = event.data
        role = data.get("role", "assistant")
        content = data.get("content", "")

        if content:
            from datetime import datetime

            bubble = MessageBubble(
                sender=role,
                content=content,
                timestamp=datetime.fromtimestamp(event.timestamp)
                if event.timestamp
                else None,
            )
            self._chat_messages.append(bubble)
            logger.debug(f"Mensagem de chat adicionada: {role}")

    def _render_surface_requests(self, event: AgiEvent):
        """Materialize canonical projection requests in the Rich adapter."""
        if event.type == AgiEventType.CHAT_MESSAGE:
            return

        projection = project_work_item(work_item_from_agent_event(event))
        requests = self._projection_reducer.reduce(event)
        activity_request = next(
            (
                request
                for request in requests
                if decide_surface(request).primary is SurfaceKind.ACTIVITY
            ),
            None,
        )
        if activity_request is None:
            return
        self.activity_feed = reduce_activity(self.activity_feed, activity_request)
        attention_request = next(
            (
                request
                for request in requests
                if request.intent
                in {PresentationIntent.DECISION, PresentationIntent.ERROR}
            ),
            activity_request,
        )
        self.attention_delivery_state, delivery = decide_attention_delivery(
            self.attention_delivery_state,
            attention_request,
            focused_task_id=None,
            app_focused=not attention_request.background,
            preferences=self.attention_preferences,
        )
        if delivery is not None:
            self._set_supervisor_notification(
                event.task_id,
                delivery.message,
                awaiting_human=event.type == AgiEventType.APPROVAL_REQUESTED,
                supervisor_state=str(event.data.get("status") or "attention"),
            )

        now = time.monotonic()
        render_key = (
            f"{activity_request.key or projection.identity_key}:"
            f"{projection.inspection.state.value}"
        )
        if (
            render_key == self._last_operational_key
            and (now - self._last_operational_render_at) < 0.75
        ):
            return

        attention = projection.attention
        if attention is not None:
            awaiting_human = attention.blocking
            supervisor_state = (
                "awaiting_human" if awaiting_human else event.data.get("status")
            )
            if supervisor_state:
                self._update_supervisor_state(event.task_id, str(supervisor_state))
            self._set_supervisor_notification(
                event.task_id,
                attention.message,
                awaiting_human=awaiting_human,
                supervisor_state=str(supervisor_state) if supervisor_state else None,
            )

        tone = ProjectionTone(activity_request.tone or ProjectionTone.INFO.value)
        render_method = {
            ProjectionTone.SUCCESS: self.render.render_success,
            ProjectionTone.WARNING: self.render.render_warning,
            ProjectionTone.ERROR: self.render.render_error,
            ProjectionTone.INFO: self.render.render_info,
            ProjectionTone.MUTED: self.render.render_info,
        }[tone]
        render_method(activity_request.content)

        self._last_operational_key = render_key
        self._last_operational_render_at = now

    def _render_realtime_heartbeats(self) -> None:
        """Refresh long-running rows at the canonical heartbeat cadence."""
        for request in self._projection_reducer.heartbeat():
            self.activity_feed = reduce_activity(self.activity_feed, request)
            self.render.render_info(request.content)

    def _render_all_content(self):
        """
        Render all active AGI task windows and chat messages.

        This method consolidates rendering of all UI components after
        event processing to ensure consistent visual state.
        """
        try:
            # Keep terminal task windows visible once so their final state is observable.
            for task_id, window in self._active_agi_tasks.items():
                is_terminal = getattr(window, "status", None) in {"completed", "failed"}
                if (
                    hasattr(window, "render")
                    and (not is_terminal or task_id not in self._rendered_terminal_tasks)
                ):
                    from aura_cli.cli.ui.composition import (
                        render_task_composite_surface,
                    )

                    self.render.render_component(render_task_composite_surface(window))
                    if is_terminal:
                        self._rendered_terminal_tasks.add(task_id)

            # Render any pending chat messages
            for bubble in self._chat_messages:
                if hasattr(bubble, "render") and not getattr(bubble, "rendered", False):
                    self.render.render_component(bubble)
                    bubble.rendered = True

        except Exception as e:
            logger.debug(f"Error rendering content: {e}")

    def get_active_tasks(self) -> Dict[str, AgiTaskWindow]:
        """Return dictionary of currently active AGI tasks."""
        return self._active_agi_tasks.copy()

    def get_chat_history(self) -> list:
        """Return list of chat message bubbles."""
        return self._chat_messages.copy()

    def clear_completed_tasks(self):
        """Remove completed tasks from active tracking."""
        completed = [
            task_id
            for task_id, window in self._active_agi_tasks.items()
            if hasattr(window, "is_complete") and window.is_complete()
        ]
        for task_id in completed:
            del self._active_agi_tasks[task_id]
            self._rendered_terminal_tasks.discard(task_id)
        logger.debug(f"Removed {len(completed)} completed tasks")
