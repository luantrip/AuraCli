"""Tests for shared operational feedback formatting."""

from aura_cli.core.events.agi_events import AgiEvent, AgiEventType
from aura_cli.core.events.operational_feedback import (
    describe_operational_event,
    format_operational_event,
)


def test_format_operational_event_formats_tool_execution_with_path_hint():
    """Tool execution lines should include the best path hint."""
    event = AgiEvent(
        type=AgiEventType.TOOL_EXECUTING,
        task_id="task-1",
        data={
            "tool_name": "write_file",
            "tool_args": {"path": "src/app.py"},
            "status": "executing",
        },
    )

    line = format_operational_event(event)

    assert "running write_file" in line
    assert "src/app.py" in line


def test_format_operational_event_formats_task_update_humanly():
    """Task updates should become readable trail lines."""
    event = AgiEvent(
        type=AgiEventType.TASK_UPDATE,
        task_id="task-1",
        data={"status": "creating directories", "message": "setting up project tree"},
    )

    line = format_operational_event(event)

    assert "Agent is creating directories" in line
    assert "setting up project tree" in line


def test_format_operational_event_formats_tool_result_with_timing():
    """Tool result lines should include success and timing when available."""
    event = AgiEvent(
        type=AgiEventType.TOOL_RESULT,
        task_id="task-1",
        data={
            "tool_name": "list_directory",
            "success": True,
            "execution_time": 1.4,
        },
    )

    line = format_operational_event(event)

    assert "list_directory completed" in line
    assert "(1.4s)" in line


def test_describe_operational_event_marks_completed_task_high_importance_success():
    """Completed tasks should carry task context and success severity."""
    event = AgiEvent(
        type=AgiEventType.TASK_COMPLETE,
        task_id="ops-7",
        data={"success": True, "result": "workspace prepared"},
    )

    feedback = describe_operational_event(event)

    assert feedback is not None
    assert feedback.task_id == "ops-7"
    assert feedback.level == "success"
    assert feedback.importance == "high"
    assert "workspace prepared" in feedback.message


def test_describe_operational_event_marks_returned_to_chat_as_high_priority():
    """Supervisor handoff back to chat should be visually explicit."""
    event = AgiEvent(
        type=AgiEventType.TASK_UPDATE,
        task_id="ops-8",
        data={
            "status": "returned_to_chat",
            "message": "Worker returned control to chat",
            "details": {
                "supervisor_state": "returned_to_chat",
                "fallback_reason": "external_dependency",
            },
        },
    )

    feedback = describe_operational_event(event)

    assert feedback is not None
    assert feedback.level == "warning"
    assert feedback.importance == "high"
    assert feedback.group == "supervisor"
    assert feedback.supervisor_state == "returned_to_chat"
    assert "returned control to chat" in feedback.message


def test_describe_operational_event_marks_awaiting_human_as_high_priority():
    """Human-approval handoff should become explicit operational feedback."""
    event = AgiEvent(
        type=AgiEventType.TASK_UPDATE,
        task_id="agi-9",
        data={
            "status": "awaiting_human",
            "message": "Worker returned control to chat",
            "details": {
                "supervisor_state": "awaiting_human",
                "fallback_reason": "human_approval_required",
            },
        },
    )

    feedback = describe_operational_event(event)

    assert feedback is not None
    assert feedback.level == "warning"
    assert feedback.importance == "high"
    assert feedback.group == "supervisor"
    assert feedback.supervisor_state == "awaiting_human"
    assert "waiting for a human decision" in feedback.message
