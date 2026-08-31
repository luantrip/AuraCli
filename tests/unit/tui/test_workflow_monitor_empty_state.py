"""Empty-state and presentation-copy contracts for WorkflowMonitor."""

from unittest.mock import MagicMock

import pytest
from textual.app import App, ComposeResult
from textual.widgets import Button, Static

from aura_cli.tui.widgets.workflow_monitor import WorkflowMonitor


class WorkflowMonitorHarness(App[None]):
    """Minimal host for the read-only workflow activity surface."""

    def compose(self) -> ComposeResult:
        yield WorkflowMonitor(id="workflow")


@pytest.mark.asyncio
async def test_workflow_monitor_has_localized_empty_state_and_clear_cycle() -> None:
    app = WorkflowMonitorHarness()

    async with app.run_test(size=(120, 30)) as pilot:
        await pilot.pause()
        monitor = app.query_one(WorkflowMonitor)
        empty = monitor.query_one("#workflow-empty-state", Static)

        headers = [widget.render().plain for widget in monitor.query(".pane-header")]
        assert any("Trilha operacional" in header for header in headers)
        assert "Atividade AGI/Ops" in monitor.query_one(".field-help").render().plain
        assert empty.display is True
        assert str(monitor.query_one("#clear_btn", Button).label) == "✖ Limpar"
        assert str(monitor.query_one("#export_btn", Button).label) == "⊞ Exportar"

        monitor._format_operational_event = MagicMock(return_value="evento projetado")
        monitor.consume_agi_event(MagicMock())
        await pilot.pause()
        assert empty.display is False
        assert monitor.activity_lines == ("evento projetado",)

        monitor._clear_activity()
        await pilot.pause()
        assert empty.display is True
        assert monitor.activity_lines == ()
