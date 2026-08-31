"""Tests for live operational trail rendering in WorkflowMonitor."""

from aura_cli.core.events.agi_events import AgiEvent, AgiEventType
from aura_cli.tui.widgets.workflow_monitor import WorkflowMonitor


def test_workflow_monitor_formats_tool_execution_with_path_hint():
    """Tool execution trail should explain the operation concisely."""
    monitor = WorkflowMonitor()
    event = AgiEvent(
        type=AgiEventType.TOOL_EXECUTING,
        task_id="task-1",
        data={
            "tool_name": "write_file",
            "tool_args": {"path": "src/app.py"},
            "status": "executing",
        },
    )

    line = monitor._format_operational_event(event)

    assert "Editar" in line
    assert "em execução" in line
    assert "src/app.py" in line


def test_workflow_monitor_formats_task_update_humanly():
    """Task updates should become readable human trail lines."""
    monitor = WorkflowMonitor()
    event = AgiEvent(
        type=AgiEventType.TASK_UPDATE,
        task_id="task-1",
        data={"status": "creating directories", "message": "setting up project tree"},
    )

    line = monitor._format_operational_event(event)

    assert "em execução" in line
    assert "setting up project tree" in line


def test_workflow_monitor_formats_tool_result_with_timing():
    """Tool result trail should include success and timing when available."""
    monitor = WorkflowMonitor()
    event = AgiEvent(
        type=AgiEventType.TOOL_RESULT,
        task_id="task-1",
        data={
            "tool_name": "list_directory",
            "success": True,
            "execution_time": 1.4,
        },
    )

    line = monitor._format_operational_event(event)

    assert "Ler" in line
    assert "completed" in line
