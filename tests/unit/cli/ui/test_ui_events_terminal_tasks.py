"""Tests for terminal task visibility in the CLI event renderer."""

from unittest.mock import Mock

from aura_cli.application.agents.events import (
    AgiEventType,
    create_lifecycle_event,
    create_task_start,
)
from aura_cli.cli.ui.components.agi_task_window import AgiTaskWindow
from aura_cli.cli.ui.events import UIEventManager


def test_terminal_task_is_rendered_once_before_cleanup(monkeypatch):
    """A completed task remains observable without being rendered repeatedly."""
    render = Mock()
    manager = UIEventManager(status_queue=None, render_coordinator=render)
    window = AgiTaskWindow(
        task_id="task-terminal",
        description="Task",
        objective="Finish task",
    )
    window.complete(True, result="done")
    manager._active_agi_tasks[window.task_id] = window
    monkeypatch.setattr(
        "aura_cli.cli.ui.composition.render_task_composite_surface",
        lambda value: value,
    )

    manager._render_all_content()
    manager._render_all_content()

    assert render.render_component.call_count == 1
    manager.clear_completed_tasks()
    assert manager.get_active_tasks() == {}


def test_task_cancelled_event_becomes_terminal_window():
    """A cancellation event must not leave an AGI window spinning forever."""
    manager = UIEventManager(status_queue=None, render_coordinator=Mock())
    manager._process_agi_event(
        create_task_start("task-cancelled", "Task", "Finish task")
    )
    manager._process_agi_event(
        create_lifecycle_event(
            AgiEventType.TASK_CANCELLED,
            "task-cancelled",
            status="cancelled",
            message="Task cancelled",
            reason="cancelled by user",
        )
    )

    window = manager._active_agi_tasks["task-cancelled"]
    assert window.status == "cancelled"
    assert window.is_complete() is True
    assert window.is_active() is False
    assert window.error == "cancelled by user"

    manager.clear_completed_tasks()
    assert manager.get_active_tasks() == {}
