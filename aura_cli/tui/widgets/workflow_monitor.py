"""Read-only operational trail for real AGI/Ops events."""

from __future__ import annotations

from datetime import datetime

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.widgets import Button, Static

from aura_cli.application.agents.events import AgiEvent
from aura_cli.application.agents.workflow import (
    StepState as StepStatus,
)
from aura_cli.application.agents.workflow import (
    Workflow,
    WorkflowStep,
)
from aura_cli.application.agents.workflow import WorkflowState as WorkflowStatus
from aura_cli.application.artifacts import ArtifactLayout
from aura_cli.application.presentation import PresentationIntent
from aura_cli.application.presentation.work_item_projection import (
    RealtimeProjectionReducer,
)


class WorkflowMonitor(Static):
    """Display and export the bounded operational trail produced by real events."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._activity_lines: tuple[str, ...] = ()
        self._projection_reducer = RealtimeProjectionReducer()

    @property
    def activity_lines(self) -> tuple[str, ...]:
        return self._activity_lines

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Static("⟳ Trilha operacional", classes="pane-header")
            yield Static(
                "Atividade AGI/Ops em tempo real. Esta superfície é somente leitura e nunca executa workflows.",
                classes="field-help",
            )
            yield Static(
                "Nenhuma atividade operacional ainda. Inicie uma tarefa para acompanhar os eventos.",
                id="workflow-empty-state",
                classes="empty-state",
            )
            yield VerticalScroll(id="workflow_activity_log", classes="output-log")
            with Horizontal(classes="action-bar"):
                yield Button("✖ Limpar", id="clear_btn")
                yield Button("⊞ Exportar", id="export_btn")

    def _set_empty_state_visible(self, visible: bool) -> None:
        """Keep the empty-state guidance synchronized with the activity log."""
        self.query_one("#workflow-empty-state", Static).display = visible

    def consume_agi_event(self, event: AgiEvent) -> None:
        message = self._format_operational_event(event)
        if message:
            self._activity_lines = (*self._activity_lines, message)[-200:]
            self._write_activity(message)
            self._set_empty_state_visible(False)

    def _format_operational_event(self, event: AgiEvent) -> str:
        request = next(
            (
                item
                for item in self._projection_reducer.reduce(event)
                if item.intent is PresentationIntent.PROGRESS
            ),
            None,
        )
        return request.content if request else ""

    def _write_activity(self, message: str) -> None:
        container = self.query_one("#workflow_activity_log", VerticalScroll)
        container.mount(Static(message, classes="log-entry log-info"))
        container.scroll_end()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "clear_btn":
            self._clear_activity()
        elif event.button.id == "export_btn":
            self._export_results()

    def _clear_activity(self) -> None:
        self._activity_lines = ()
        self.query_one("#workflow_activity_log", VerticalScroll).remove_children()
        self._set_empty_state_visible(True)

    def _export_results(self) -> None:
        if not self._activity_lines:
            self.notify(
                "Nenhuma atividade operacional para exportar.", title="Workflows"
            )
            return
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        path = ArtifactLayout().project("reports", f"operational-trail-{timestamp}.md")
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                "\n".join(("# Aura Operational Trail", "", *self._activity_lines, "")),
                encoding="utf-8",
            )
        except OSError as error:
            self.log.error("Unable to export operational trail: %s", error)
            self.notify(
                "Failed to export operational trail.",
                title="Workflows",
                severity="error",
            )
            return
        self.notify(f"Trilha exportada: {path}", title="Workflows")


__all__ = [
    "StepStatus",
    "Workflow",
    "WorkflowMonitor",
    "WorkflowStatus",
    "WorkflowStep",
]
