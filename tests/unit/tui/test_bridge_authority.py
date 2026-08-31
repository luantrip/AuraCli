from __future__ import annotations

from queue import Queue
from unittest.mock import MagicMock, patch

from aura_cli.application.agents.events import AgiEvent, AgiEventType
from aura_cli.tui.bridge import TextualUIManager
from aura_cli.tui.core.sync_manager import SyncManager
from aura_cli.tui.widgets.event_stream_panel import EventStreamPanel


def _task_start_dict() -> dict:
    return {
        "type": "agi_task_start",
        "task_id": "task-1",
        "data": {
            "description": "Auditar",
            "objective": "Paridade",
            "status": "starting",
        },
    }


def test_fallback_validates_before_event_stream() -> None:
    app = MagicMock()
    app.call_from_thread = MagicMock()
    bridge = TextualUIManager(app, status_queue=Queue())

    bridge._process_event({"type": "agi_task_start", "task_id": "task-1", "data": {}})

    app.query_one.assert_not_called()
    app.call_from_thread.assert_not_called()


def test_normal_and_fallback_share_one_task_tree_projection() -> None:
    event_dict = _task_start_dict()

    fallback_app = MagicMock()
    fallback_app.call_from_thread = MagicMock()
    fallback = TextualUIManager(fallback_app, status_queue=Queue())
    fallback._process_event(event_dict)

    fallback_tree_calls = [
        call
        for call in fallback_app.call_from_thread.call_args_list
        if call.args and call.args[0] == fallback_app.update_task_tree
    ]
    assert len(fallback_tree_calls) == 1

    normal_app = MagicMock()
    normal_app.call_from_thread = MagicMock()
    manager = SyncManager(normal_app, status_queue=Queue(), store=MagicMock())
    manager._running = True
    manager._handle_agent_event(AgiEvent.from_dict(event_dict))

    normal_tree_calls = [
        call
        for call in normal_app.call_from_thread.call_args_list
        if call.args and call.args[0] == normal_app.update_task_tree
    ]
    assert len(normal_tree_calls) == 1


def test_event_stream_direct_tool_details_redact_args_and_accept_string_enum() -> None:
    event = AgiEvent(
        type="tool_executing",
        task_id="task-1",
        data={
            "tool_name": "shell",
            "tool_args": {"command": "cat super-secret.txt"},
        },
    )
    panel = EventStreamPanel()
    panel.mount = MagicMock()
    panel.scroll_end = MagicMock()
    panel._set_empty_state_visible = MagicMock()
    static = MagicMock()

    with patch(
        "aura_cli.tui.widgets.event_stream_panel.Static", return_value=static
    ) as factory:
        panel.write_event(
            {
                "type": AgiEventType.TOOL_EXECUTING,
                "task_id": "task-1",
                "data": event.data,
            }
        )
        panel.write_event_details(event)

    rendered_payloads = [call.args[0] for call in factory.call_args_list]
    assert rendered_payloads
    assert all("super-secret.txt" not in str(payload) for payload in rendered_payloads)
    assert any(
        "Event Type: tool_executing" in str(payload) for payload in rendered_payloads
    )
