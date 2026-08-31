"""UIManager - Centralized user interface manager (Facade).

This module provides a unified facade for the Aura CLI UI system, delegating
responsibilities to specialized components:
- InputManager: Handles user input and prompts
- RenderCoordinator: Handles display and rendering
- UIEventManager: Handles background event listening

This maintains backward compatibility while improving internal architecture.
"""

from typing import Any, Optional

from rich.console import Console

from aura_cli.cli.ui.components.status_bar import StatusBar
from aura_cli.cli.ui.events import UIEventManager
from aura_cli.cli.ui.input import InputManager
from aura_cli.cli.ui.rendering import RenderCoordinator
from aura_cli.core.stats import StatsTracker, get_stats


class UIManager:
    """Centralised Aura CLI UI manager (Facade)."""

    def __init__(
        self,
        stats: Optional[StatsTracker] = None,
        status_queue=None,
        console: Optional[Console] = None,
    ):
        """Initialize the UIManager and all sub-component facades."""
        self.console = console if console is not None else Console()
        self.stats = stats or get_stats()
        self.status_queue = status_queue

        # Initialize sub-components
        self._render_coordinator = RenderCoordinator(self.console, self.stats)
        self._input_manager = InputManager(self.console, self.stats, self.status_queue)
        self._event_manager = UIEventManager(
            self.status_queue, self._render_coordinator
        )
        self.status_bar = StatusBar(self.stats)

        # Expose sub-components for direct access if needed
        self.display = self._render_coordinator
        self.status = self._render_coordinator.status

    @property
    def is_tui_mode(self) -> bool:
        """Return True if the TUI is active."""
        return False

    # --- Delegation to RenderCoordinator ---

    def show_thinking(self):
        """Show thinking status."""
        self._render_coordinator.status.set_thinking()

    def show_working(self, message: str = "Processando"):
        """Show a working indicator."""
        self._render_coordinator.status.set_working(message)

    def show_idle(self):
        """Set status to idle."""
        self._render_coordinator.status.set_idle()

    def stop_status(self):
        """Stop current status."""
        self._render_coordinator.status.stop()

    def display_response(self, content: str, title: str = "Aura"):
        """Display response panel."""
        self._render_coordinator.render_response(content, title)

    def display_error(self, error: str):
        """Display error message."""
        self._render_coordinator.render_error(error)

    def display_success(self, message: str):
        """Display success message."""
        self._render_coordinator.render_success(message)

    def display_warning(self, message: str):
        """Display warning message."""
        self._render_coordinator.render_warning(message)

    def emit_capability_decision(
        self,
        tool_name: str,
        decision: Any,
        *,
        task_id: Optional[str] = None,
        phase: str = "evaluation",
        execution_id: Optional[str] = None,
    ) -> None:
        """Emit an argument-free capability audit event when a queue exists."""
        if self.status_queue is None:
            return
        from aura_cli.application.agents.events import create_capability_decision

        risk_level = getattr(decision, "risk_level", None)
        if risk_level is not None:
            risk_level = getattr(risk_level, "value", str(risk_level))
        self.status_queue.put(
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

    def display_info(self, message: str):
        """Display info message."""
        self._render_coordinator.render_info(message)

    def record_turn_metrics(self, exec_time: float = 0.0, model: str = "") -> None:
        """Record metrics for the current turn."""
        self.status_bar.record_turn_metrics(exec_time=exec_time, model=model)

    def display_status_bar(self, todo_summary: str = "") -> None:
        """Render the status bar before the next prompt."""
        self.console.print(
            self.status_bar.render(
                todo_summary=todo_summary,
                console_width=self.console.width,
            )
        )

    def display_shell_output(self, command: str, success: bool, output: str):
        """Display shell command output."""
        self._render_coordinator.render_shell_output(command, success, output)

    def display_investigator_progress(self, step: str, status: str):
        """Display codebase investigator progress."""
        self._render_coordinator.display_investigator_progress(step, status)

    def display_investigator_summary(self, results: dict):
        """Display the final codebase analysis summary."""
        self._render_coordinator.display_investigator_summary(results)

    def handle_human_intervention_request(self, request: dict) -> dict:
        """Handle a human intervention request by rendering the confirmation dialog.

        Renders the appropriate dialog component based on the request type
        (confirm, input, select, manual step) and returns the user's response.

        Args:
            request: InterventionRequest dict with keys: request_id, request_type, prompt, context, etc.

        Returns:
            Response dict with: approved (bool), value, cancelled, reason.
        """
        try:
            from aura_cli.cli.ui.components.human_confirmation_dialog import (
                HumanConfirmationDialog,
                HumanDoubleConfirmationDialog,
            )
            from aura_cli.core.events.human_intervention_events import (
                InterventionRequest,
                InterventionRequestType,
                RiskLevel,
            )

            req_type = request.get("request_type", "confirm")

            if req_type in (
                InterventionRequestType.CONFIRM,
                "confirm",
                "double_confirm",
            ):
                normalized = dict(request)
                normalized.setdefault("task_id", "cli")
                normalized.setdefault("request_id", "cli-confirmation")
                normalized["request_type"] = "confirm"
                intervention = InterventionRequest.from_dict(normalized)
                is_double = (
                    req_type == "double_confirm"
                    or intervention.context.risk_level is RiskLevel.CRITICAL
                )
                dialog = (
                    HumanDoubleConfirmationDialog()
                    if is_double
                    else HumanConfirmationDialog()
                )
                return dialog.prompt_user(intervention)

            # Fallback: generic yes/no for unknown types
            from rich.prompt import Prompt

            answer = Prompt.ask(
                f"[bold]{request.get('prompt', 'Confirmar?')}[/bold] [dim](s/n)[/dim]",
                choices=["s", "n", "y"],
                default="n",
            )
            approved = answer.lower() in ("s", "y")
            return {
                "approved": approved,
                "cancelled": False,
                "value": "Sim" if approved else "Não",
            }

        except Exception as e:
            from aura_cli.core.logger import get_logger

            get_logger(__name__).warning(
                "handle_human_intervention_request falhou: %s", e
            )
            return {
                "approved": False,
                "cancelled": True,
                "reason": "ui_error",
                "error": str(e),
            }

    def print(self, *args, **kwargs):
        """Print directly to console."""
        self.console.print(*args, **kwargs)

    def clear(self):
        """Clear console."""
        self.console.clear()

    # --- Delegation to InputManager ---

    def prompt(self, tangent_indicator: str = "") -> str:
        """Show the user input prompt."""
        return self._input_manager.prompt(tangent_indicator)

    # --- Delegation to UIEventManager ---

    def start_agi_event_listener(self):
        """Inicia thread que escuta eventos AGI."""
        self._event_manager.start_listener()

    def stop_agi_event_listener(self):
        """Stop the AGI event listener."""
        self._event_manager.stop_listener()
