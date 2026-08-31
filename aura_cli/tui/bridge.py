"""Textual UI Bridge — connects CLI core logic to the Textual interface."""

import contextlib
import logging
from queue import Empty
from typing import TYPE_CHECKING, Any, Callable, Dict, Optional

from aura_cli.application.agents.events import AgiEventType
from aura_cli.application.presentation.approvals import (
    ApprovalCenter,
    approval_request_from_event,
    approval_resolution_from_event,
    request_approval,
    resolve_approval,
)
from aura_cli.application.presentation.safe_payloads import (
    sanitize_event_dict_for_presentation,
)
from aura_cli.application.presentation.tui_surfaces import (
    PresentationIntent,
    SurfaceRequest,
)
from aura_cli.application.presentation.work_item_projection import (
    RealtimeProjectionReducer,
)
from aura_cli.application.tools.capability_broker import CapabilityDecision
from aura_cli.tui.constants import ERROR, INFO, SUCCESS, WARNING
from aura_cli.tui.core.sync_manager import (
    TASK_TREE_EVENT_TYPES,
    is_valid_queue_event,
)

if TYPE_CHECKING:
    from aura_cli.tui.core.sync_manager import SyncManager

logger = logging.getLogger(__name__)


class TextualUIManager:
    """UIManager adapter for Textual TUI mode.

    Replaces the Rich UIManager when running in TUI mode, routing all
    prints and displays to Textual widgets via thread-safe operations.
    Backed by SyncManager (50 ms event batching) and SyncStore.
    """

    def __init__(
        self,
        tui_app,
        status_queue=None,
        stats=None,
        intervention_adapter_resolver: Optional[Callable[[str], Any]] = None,
    ):
        """Initialize bridge with TUI app and optional components.

        Args:
            tui_app: AuraTUI application instance
            status_queue: Optional queue for status events
            stats: Optional stats tracker instance
        """
        self.app = tui_app
        self.is_tui = True
        self._status_queue = status_queue
        self.stats = stats
        self._intervention_adapter_resolver = intervention_adapter_resolver
        self.console = None
        self._sync_manager: Optional[SyncManager] = None
        self._projection_reducer = RealtimeProjectionReducer()
        self.approval_center = ApprovalCenter()
        self._init_pending = True  # Flag for lazy initialization
        self._heartbeat_timer_started = False
        self._fallback_timers: list[Any] = []
        self._terminal_intervention_responses: list[Dict[str, Any]] = []

    def _safe_call_from_thread(self, callback, *args, **kwargs) -> bool:
        """Safely call function from thread with error handling."""
        if not self.app or not self.app.is_running:
            return False
        try:
            self.app.call_from_thread(callback, *args, **kwargs)
            return True
        except (RuntimeError, AttributeError):
            return False
        except Exception as e:
            logger.debug(f"_safe_call_from_thread failed: {e}")
            return False

    def _present(
        self,
        intent: PresentationIntent,
        content: str,
        *,
        title: str | None = None,
        persistent: bool = False,
        task_id: str = "global_chat",
    ) -> bool:
        """Send semantic output through the shared surface policy."""
        return self._safe_call_from_thread(
            self.app.present_surface,
            SurfaceRequest(
                intent,
                content,
                title=title,
                persistent=persistent,
                task_id=task_id,
            ),
        )

    def _init_sync_manager(self):
        """Initialize SyncManager for reactive event handling.

        This should be called after the app is running (has an event loop).
        """
        try:
            from aura_cli.tui.core.sync_manager import SyncManager

            self._sync_manager = SyncManager(
                app=self.app, status_queue=self._status_queue, stats=self.stats
            )
            self._sync_manager.start()
            self._start_heartbeat_timer()
            self._init_pending = False
            logger.info("SyncManager initialized and started")
        except Exception as e:
            logger.warning(
                f"Failed to initialize SyncManager, falling back to queue polling: {e}"
            )
            self._init_fallback_polling()
            self._init_pending = False

    def ensure_initialized(self) -> bool:
        """
        Ensure SyncManager is initialized for reactive event handling.

        This method should be called from on_mount() in the TUI app to ensure
        proper initialization after the event loop is available.

        Returns:
            True if initialization succeeded or was already done
        """
        if not self._init_pending:
            return self._sync_manager is not None

        # Check if app has event loop available
        if hasattr(self.app, "_loop") and self.app._loop:
            self._init_sync_manager()
            return self._sync_manager is not None

        # Try initialization anyway - some setups may work without explicit loop
        try:
            self._init_sync_manager()
            return self._sync_manager is not None
        except Exception as e:
            logger.warning(
                f"Could not initialize SyncManager in ensure_initialized: {e}"
            )
            return False

    def is_initialized(self) -> bool:
        """
        Check if SyncManager has been initialized.

        Returns:
            True if SyncManager is active
        """
        return not self._init_pending and self._sync_manager is not None

    def _init_fallback_polling(self):
        """Initialize queue polling when SyncManager is unavailable."""
        if self._status_queue:
            self._fallback_timers.append(
                self.app.set_interval(0.1, self._poll_status_queue)
            )

        if self.stats:
            self._fallback_timers.append(
                self.app.set_interval(1.0, self._update_ui_stats)
            )
        self._start_heartbeat_timer()

    def _start_heartbeat_timer(self) -> None:
        if not self._heartbeat_timer_started:
            self._fallback_timers.append(
                self.app.set_interval(1.0, self._emit_realtime_heartbeats)
            )
            self._heartbeat_timer_started = True

    def _emit_realtime_heartbeats(self) -> None:
        for request in self._projection_reducer.heartbeat():
            self._safe_call_from_thread(self.app.present_surface, request)

    def _poll_status_queue(self):
        """Poll status queue for new events without losing later items."""
        max_events_per_poll = 50
        for _ in range(max_events_per_poll):
            try:
                event_dict = self._status_queue.get_nowait()
            except Empty:
                return
            try:
                self._process_event(event_dict)
            except Exception:
                logger.exception("Falha inesperada ao processar evento AGI")

    def _process_event(self, event_dict):
        """Process event and route to appropriate handlers.

        Args:
            event_dict: Event dictionary from status queue
        """
        from aura_cli.application.agents.events import AgiEvent

        if (
            isinstance(event_dict, dict)
            and event_dict.get("type") == "human_intervention_request"
        ):
            self._present_intervention(event_dict)
            return

        if not isinstance(event_dict, dict):
            logger.warning("Evento AGI descartado: payload não é um objeto")
            return
        event_type = event_dict.get("type")
        event_data = event_dict.get("data", {})
        if not event_type or not is_valid_queue_event(event_type, event_data):
            logger.warning(
                "Evento AGI descartado por falha de contrato: %s",
                event_type or "<missing type>",
            )
            return

        try:
            event = AgiEvent.from_dict(event_dict)
        except (KeyError, TypeError, ValueError) as error:
            logger.warning("AGI event discarded due to invalid payload: %s", error)
            return

        safe_event_dict = sanitize_event_dict_for_presentation(event.to_dict())
        try:
            event_stream_panel = self.app.query_one("#event_stream_panel")
            event_stream_panel.write_event(safe_event_dict)
        except Exception as error:
            logger.debug("Fallback event stream unavailable: %s", error)

        if event.type == AgiEventType.APPROVAL_REQUESTED:
            self.approval_center = request_approval(
                self.approval_center, approval_request_from_event(event)
            )
        elif event.type == AgiEventType.APPROVAL_RESOLVED:
            self.approval_center = resolve_approval(
                self.approval_center, approval_resolution_from_event(event)
            )

        if event.type == AgiEventType.CHAT_MESSAGE:
            data = event.data
            self._safe_call_from_thread(
                self.app.post_message_to_chat,
                data.get("sender", "Unknown"),
                data.get("content", ""),
                task_id=event.task_id,
            )
        elif event.type in TASK_TREE_EVENT_TYPES:
            self._safe_call_from_thread(self.app.update_task_tree, event)

        if event.type != AgiEventType.CHAT_MESSAGE:
            for request in self._projection_reducer.reduce(event):
                self._safe_call_from_thread(self.app.present_surface, request)

        try:
            from aura_cli.tui.core.event_bus import TUIEvents

            TUIEvents.bus.publish(
                "tui.sync.state",
                {"path": f"events.{event.type!s}", "value": safe_event_dict},
            )
        except Exception as error:
            logger.debug("Fallback sync event publication failed: %s", error)

    def _present_intervention(self, request: Dict[str, Any]) -> None:
        """Open a correlated Textual decision modal and unblock its worker."""
        task_id = str(request.get("task_id") or "")
        request_id = str(request.get("request_id") or "")
        if not task_id or not request_id:
            logger.warning("Intervention request missing task_id or request_id")
            return
        context = request.get("context") or {}
        if not isinstance(context, dict):
            logger.warning("Invalid intervention context for task_id=%s", task_id)
            context = {}
        metadata = context.get("metadata") or {}
        if not isinstance(metadata, dict):
            metadata = {}
        options = [
            ("once", "Aprovar uma vez"),
            ("session", "Aprovar nesta sessão"),
        ]
        if metadata.get("policy_key"):
            options.append(("policy", "Aprovar e salvar política"))
        options.append(("decline", "Recusar"))

        def deliver(scope: Optional[str]) -> None:
            approved = scope in {"once", "session", "policy"}
            response = {
                "task_id": task_id,
                "request_id": request_id,
                "approved": approved,
                "cancelled": scope is None,
                "reason": None if approved else "declined",
                "scope": scope or "once",
            }

            resolver = self._intervention_adapter_resolver
            adapter = None
            resolver_error = None
            if resolver is not None:
                try:
                    adapter = resolver(task_id)
                except Exception as error:
                    resolver_error = error
                    logger.warning(
                        "Intervention adapter resolver failed for task_id=%s: %s",
                        task_id,
                        error,
                    )

            if adapter is None:
                reason = "resolver_failed" if resolver_error else "adapter_unavailable"
                response.update(
                    approved=False,
                    cancelled=True,
                    reason=reason,
                    scope="once",
                )
                self._terminal_intervention_responses.append(response.copy())
                logger.warning(
                    "Intervention response terminalized as cancelled: %s "
                    "for task_id=%s request_id=%s",
                    reason,
                    task_id,
                    request_id,
                )
                return

            try:
                adapter.receive_response(response)
            except Exception as error:
                terminal_response = response.copy()
                terminal_response.update(
                    approved=False,
                    cancelled=True,
                    reason="delivery_failed",
                    scope="once",
                )
                self._terminal_intervention_responses.append(terminal_response)
                logger.warning(
                    "Intervention response could not be delivered for "
                    "task_id=%s request_id=%s: %s",
                    task_id,
                    request_id,
                    error,
                )

        def open_modal() -> None:
            from aura_cli.tui.components.shared.dialogs import SelectDialog

            self.app.push_screen(
                SelectDialog(
                    title="Ação necessária",
                    message=str(request.get("prompt") or "Confirmar operação?"),
                    options=options,
                    default="once",
                ),
                deliver,
            )

        self._safe_call_from_thread(open_modal)

    def _update_ui_stats(self):
        """Update sidebar with current statistics."""
        if not self.stats:
            return

        stats_data = {
            "status": self.stats.current_status,
            "mode": "Interactive",
            "files_read": len(self.stats._files_read_list),
            "files_edited": len(self.stats._files_edited_list),
            "files_created": len(self.stats._files_created_list),
            "llm_calls": self.stats.llm_calls,
            "tool_calls": self.stats.tool_calls,
            "total_tokens": self.stats.total_tokens,
            "total_execution_time": f"{self.stats.total_execution_time:.2f}s",
        }

        try:
            sidebar = self.app.query_one("AuraStatusSidebar")
            sidebar.update_stats(stats_data)
        except Exception as error:
            logger.debug("Fallback sidebar update unavailable: %s", error)

    def print(self, renderable: Any, **kwargs):
        """Redirect generic print to chat log.

        In TUI mode, Rich renderables are ignored (TUI has its own widgets).
        Only plain strings are forwarded to chat.
        """
        if renderable is None:
            return

        # Skip Rich renderables that are visual-only (separators, bubbles, etc.)
        text = None
        if isinstance(renderable, str):
            text = renderable
        elif hasattr(renderable, "plain"):
            # Rich Text object
            plain = renderable.plain.strip()
            if plain and not all(c in "─·━" for c in plain):
                text = plain
        # Ignore other Rich renderables (Padding, Group, Panel etc.)

        if text and text.strip():
            self._present(PresentationIntent.INFORMATION, text)

    def display_response(self, response: str, title: Optional[str] = None):
        """Display agent response in chat.

        Args:
            response: Response content
            title: Optional title (unused in TUI)
        """
        self._present(PresentationIntent.RESPONSE, response, title=title)

    def display_error(self, error: str):
        """Display error as notification and chat message.

        Args:
            error: Error message
        """
        self._present(
            PresentationIntent.ERROR,
            f"{ERROR} {error}",
            title="Erro",
            persistent=True,
        )

    def display_success(self, message: str):
        """Display success notification.

        Args:
            message: Success message
        """
        self._present(PresentationIntent.SUCCESS, message, title="Sucesso")

    def display_investigator_progress(self, step: str, status: str):
        """Display investigator progress as notification.

        Args:
            step: Current step name
            status: Step status
        """
        if status == "completed":
            self._present(
                PresentationIntent.PROGRESS, f"Investigator: {step} completed"
            )

    def prompt(self) -> str:
        """Prompt for user input with graceful fallback.

        Note:
            In TUI mode, blocking prompts are not fully supported. Input should
            come via event-driven flow through on_input_submitted.

        Returns:
            Empty string (TUI mode cannot block for input)
        """
        logger.warning(
            "prompt() called in TUI mode - this indicates code that should use "
            "event-driven input. Returning empty string to prevent crash."
        )

        try:
            self._safe_call_from_thread(
                self.app.notify,
                "Input requested via blocking prompt - please use the input bar below",
                title="Input Required",
                severity="warning",
                timeout=5,
            )
        except Exception as e:
            logger.debug(f"Could not show notification: {e}")

        return ""

    async def push_screen_wait(self, screen):
        """Await a modal screen result (tool_execution / bridge API)."""
        return await self.app.push_screen_wait(screen)

    async def prompt_async(self, message: str = "") -> str:
        """
        Asynchronous prompt for user input via dialog.

        Shows an input dialog in the TUI and waits for user response.

        Args:
            message: Optional prompt message to display

        Returns:
            User input string or empty string if cancelled
        """
        try:
            from aura_cli.tui.components.shared.dialogs import InputDialog

            result = await self.app.push_screen_wait(
                InputDialog(title="Input", message=message or "Enter input:")
            )
            return result or ""
        except Exception as e:
            logger.warning(f"Async prompt failed: {e}")
            return ""

    def update_status(self, status: str, message: str = ""):
        """Update sidebar and footer status display.

        Args:
            status: Status text
            message: Optional status message
        """
        try:
            sidebar = self.app.query_one("AuraStatusSidebar")
            sidebar.update_stats({"status": status, "message": message})
        except Exception as e:
            logger.debug(f"Could not update sidebar status: {e}")

        if message:
            try:
                from aura_cli.tui.widgets.footer import AuraFooter

                footer = self.app.query_one("#footer", AuraFooter)
                self._safe_call_from_thread(footer.set_status, message)
            except Exception as e:
                logger.debug(f"Could not update footer status: {e}")

    def emit_capability_decision(
        self,
        tool_name: str,
        decision: Any,
        *,
        task_id: Optional[str] = None,
        phase: str = "evaluation",
        execution_id: Optional[str] = None,
    ) -> None:
        """Emit an argument-free capability event to the shared status queue."""
        if self._status_queue is None:
            return
        from aura_cli.application.agents.events import create_capability_decision

        risk_level = getattr(decision, "risk_level", None)
        if risk_level is not None:
            risk_level = getattr(risk_level, "value", str(risk_level))
        self._status_queue.put(
            create_capability_decision(
                task_id=task_id or "global_chat",
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

    def display_warning(self, message: str):
        """Display warning as notification and chat message.

        Args:
            message: Warning message
        """
        self._present(PresentationIntent.WARNING, f"{WARNING} {message}", title="Aviso")

    def display_capability_decision(
        self,
        tool_name: str,
        decision: CapabilityDecision,
        *,
        task_id: str | None = None,
    ) -> None:
        """Present a blocked capability as a persistent security surface."""
        if decision.allowed:
            return
        content = f"Operação bloqueada: `{tool_name}`\n{decision.reason}"
        self._present(
            PresentationIntent.ERROR,
            content,
            title="Segurança",
            persistent=True,
            task_id=task_id or "global_chat",
        )

    def display_info(self, message: str):
        """Display info message in chat.

        Args:
            message: Info message
        """
        self._present(PresentationIntent.INFORMATION, f"{INFO} {message}")

    def display_shell_output(self, command: str, success: bool, output: str):
        """Display shell command output in chat.

        Args:
            command: Executed command
            success: Whether command succeeded
            output: Command output
        """
        status_icon = SUCCESS if success else ERROR
        content = f"**{status_icon} Shell Command:** `{command}`\n\n```\n{output}\n```"
        self._present(PresentationIntent.TOOL_RESULT, content, persistent=True)

    def clear(self):
        """Clear chat log."""
        self._safe_call_from_thread(self.app.query_one("AuraChatLog").clear)

    def display_investigator_summary(self, results: dict):
        """Display investigator summary in chat.

        Args:
            results: Investigator results dictionary
        """
        summary = results.get("summary", {})
        content = f"""## ▥ Investigator Summary

- **Files Analyzed:** {summary.get("files_analyzed", 0)}
- **Total Lines:** {summary.get("total_lines", 0)}
- **Languages:** {", ".join(summary.get("languages", []))}
"""
        self._present(PresentationIntent.INFORMATION, content, persistent=True)

    @property
    def status_queue(self):
        """Get status queue for compatibility."""
        return self._status_queue if hasattr(self, "_status_queue") else None

    @status_queue.setter
    def status_queue(self, value):
        """Set status queue and update SyncManager.

        Args:
            value: New status queue
        """
        self._status_queue = value
        if self._sync_manager:
            self._sync_manager.queue = value

    @property
    def sync_manager(self) -> Optional["SyncManager"]:
        """Get SyncManager instance."""
        return self._sync_manager

    def stop(self):
        """Stop manager and cleanup resources."""
        manager, self._sync_manager = self._sync_manager, None
        self._init_pending = True
        if manager:
            manager.stop()
            logger.info("SyncManager stopped")

        for timer in self._fallback_timers:
            with contextlib.suppress(Exception):
                timer.stop()
        self._fallback_timers.clear()
        self._heartbeat_timer_started = False

    def get_sync_metrics(self) -> Dict[str, Any]:
        """Get synchronization metrics.

        Returns:
            Dictionary containing sync metrics or status
        """
        if self._sync_manager:
            return self._sync_manager.get_metrics()
        return {"sync_manager": "not_initialized"}
