"""Tests for CLI operational feedback rendering in UIEventManager."""

from unittest.mock import Mock

from aura_cli.cli.ui.events import UIEventManager
from aura_cli.core.events.agi_events import (
    AgiEventType,
    AgiTaskCompleteEvent,
    ChatMessageEvent,
    ToolExecutingEvent,
)


def test_ui_event_manager_renders_operational_feedback_for_tool_events():
    """Tool events should produce a visible informational trail in the CLI."""
    render = Mock()
    render.stats = Mock()
    manager = UIEventManager(status_queue=None, render_coordinator=render)

    manager._process_agi_event(
        ToolExecutingEvent.create(
            task_id="task-1",
            tool_name="write_file",
            tool_args={"path": "src/app.py"},
        ).to_dict()
    )

    render.render_info.assert_called_once()
    message = render.render_info.call_args.args[0]
    assert "Editar src/app.py · em execução" in message
    assert "src/app.py" in message


def test_ui_event_manager_does_not_render_operational_feedback_for_chat_messages():
    """Chat message events should stay in chat history only."""
    render = Mock()
    render.stats = Mock()
    manager = UIEventManager(status_queue=None, render_coordinator=render)

    manager._process_agi_event(
        ChatMessageEvent.create(
            sender="assistant",
            content="Worker finished setup",
            task_id="task-1",
        ).to_dict()
    )

    render.render_info.assert_not_called()
    history = manager.get_chat_history()
    assert len(history) == 1
    assert history[0].content == "Worker finished setup"


def test_ui_event_manager_deduplicates_identical_operational_feedback():
    """Consecutive duplicate operational lines should not spam the CLI."""
    render = Mock()
    render.stats = Mock()
    manager = UIEventManager(status_queue=None, render_coordinator=render)
    event = {
        "type": AgiEventType.PLANNING,
        "task_id": "task-1",
        "data": {},
    }

    manager._process_agi_event(event)
    manager._process_agi_event(event)

    render.render_info.assert_called_once()


def test_ui_event_manager_rejects_incomplete_task_completion_before_rendering():
    """A completion without success is invalid and must not reach the Rich adapter."""
    render = Mock()
    render.stats = Mock()
    manager = UIEventManager(status_queue=None, render_coordinator=render)

    manager._process_agi_event(
        {
            "type": AgiEventType.TASK_COMPLETE,
            "task_id": "task-invalid",
            "data": {"result": "ambiguous"},
        }
    )

    assert manager.get_active_tasks() == {}
    render.render_info.assert_not_called()
    render.render_success.assert_not_called()
    render.render_error.assert_not_called()


def test_ui_event_manager_renders_high_importance_task_success_with_task_prefix():
    """High-importance task outcomes should be grouped with task context."""
    render = Mock()
    render.stats = Mock()
    manager = UIEventManager(status_queue=None, render_coordinator=render)

    manager._process_agi_event(
        AgiTaskCompleteEvent.create(
            task_id="ops-42",
            success=True,
            result="environment prepared",
        ).to_dict()
    )

    render.render_success.assert_called_once()
    message = render.render_success.call_args.args[0]
    assert "[ops-42]" in message
    assert "environment prepared" in message


def test_ui_event_manager_renders_supervisor_return_to_chat_as_warning():
    """Supervisor-level fallback should appear as a warning line in the CLI."""
    render = Mock()
    render.stats = Mock()
    manager = UIEventManager(status_queue=None, render_coordinator=render)

    manager._process_agi_event(
        {
            "type": AgiEventType.TASK_UPDATE,
            "task_id": "ops-99",
            "data": {
                "status": "returned_to_chat",
                "message": "Worker returned control to chat",
                "details": {
                    "supervisor_state": "returned_to_chat",
                    "fallback_reason": "external_dependency",
                },
            },
        }
    )

    render.render_warning.assert_called_once()
    message = render.render_warning.call_args.args[0]
    assert "[ops-99]" in message
    assert "interrupted" in message
    assert "returned control to chat" in message
    assert manager.get_supervisor_state("ops-99") == "returned_to_chat"
    render.stats.set_notification.assert_called_once()
    notification = render.stats.set_notification.call_args.args[0]
    assert "SUPERVISOR" in notification
    assert "[RETURNED_TO_CHAT]" in notification
    assert "returned control to chat" in notification


def test_ui_event_manager_surfaces_human_intervention_request_before_dialog():
    """Human intervention requests should be visible in the operational trail."""
    render = Mock()
    render.stats = Mock()
    manager = UIEventManager(status_queue=None, render_coordinator=render)

    from unittest.mock import patch

    with patch("aura_cli.cli.helpers._handle_intervention_request") as handler:
        manager._process_agi_event(
            {
                "type": "human_intervention_request",
                "task_id": "agi-77",
                "prompt": "Approve git commit?",
            }
        )

    render.render_warning.assert_called_once()
    message = render.render_warning.call_args.args[0]
    assert "[agi-77]" in message
    assert "[SUPERVISOR:AWAITING_HUMAN]" in message
    assert "waiting for a human decision" in message
    assert manager.get_supervisor_state("agi-77") == "awaiting_human"
    render.stats.set_notification.assert_called_once()
    notification = render.stats.set_notification.call_args.args[0]
    assert "[AWAITING_HUMAN]" in notification
    assert "awaiting human decision" in notification
    handler.assert_called_once()


def test_ui_event_manager_deduplicates_identical_supervisor_notifications():
    """StatusBar should only update when supervisor state meaningfully changes."""
    render = Mock()
    render.stats = Mock()
    manager = UIEventManager(status_queue=None, render_coordinator=render)

    event = {
        "type": AgiEventType.TASK_UPDATE,
        "task_id": "ops-11",
        "data": {
            "status": "returned_to_chat",
            "message": "Worker returned control to chat",
            "details": {
                "supervisor_state": "returned_to_chat",
                "fallback_reason": "external_dependency",
            },
        },
    }

    manager._process_agi_event(event)
    manager._process_agi_event(event)

    assert render.stats.set_notification.call_count == 1
    assert manager.get_supervisor_state("ops-11") == "returned_to_chat"


def test_ui_event_manager_propagates_supervisor_state_to_active_window():
    """Active task windows should reflect the current supervisor state."""
    render = Mock()
    render.stats = Mock()
    manager = UIEventManager(status_queue=None, render_coordinator=render)

    manager._process_agi_event(
        {
            "type": AgiEventType.TASK_START,
            "task_id": "agi-55",
            "data": {
                "description": "Task",
                "objective": "Analyze project",
                "status": "starting",
            },
        }
    )
    manager._process_agi_event(
        {
            "type": AgiEventType.TASK_UPDATE,
            "task_id": "agi-55",
            "data": {
                "status": "awaiting_human",
                "message": "Worker returned control to chat",
                "details": {
                    "supervisor_state": "awaiting_human",
                    "fallback_reason": "human_approval_required",
                },
            },
        }
    )

    window = manager.get_active_tasks()["agi-55"]
    assert window.supervisor_state == "awaiting_human"
    assert window.fallback_reason == "human_approval_required"
