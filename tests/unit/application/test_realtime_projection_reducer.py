from datetime import datetime, timezone

from aura_cli.application.agents.events import AgiEvent, AgiEventType
from aura_cli.application.presentation import PresentationIntent
from aura_cli.application.presentation.work_item_projection import (
    RealtimeProjectionReducer,
)


def event(event_type: AgiEventType, at: float, **data) -> AgiEvent:
    return AgiEvent(type=event_type, task_id="task-1", timestamp=at, data=data)


def activity(requests):
    return next(
        request for request in requests if request.intent is PresentationIntent.PROGRESS
    )


def test_reducer_preserves_start_time_across_independent_event_snapshots() -> None:
    reducer = RealtimeProjectionReducer(heartbeat_seconds=15)
    reducer.reduce(event(AgiEventType.TASK_START, 100.0, description="Build"))

    request = activity(
        reducer.reduce(
            event(AgiEventType.TASK_UPDATE, 121.0, status="running", message="Testing")
        )
    )

    assert request.elapsed_seconds == 21
    assert request.content.endswith("21s")
    assert request.heartbeat_due
    assert request.replace


def test_terminal_event_consolidates_and_stops_future_heartbeats() -> None:
    reducer = RealtimeProjectionReducer(heartbeat_seconds=5)
    reducer.reduce(event(AgiEventType.TASK_START, 100.0, description="Build"))
    request = activity(
        reducer.reduce(
            event(AgiEventType.TASK_COMPLETE, 110.0, success=True, result="Done")
        )
    )

    assert request.elapsed_seconds == 10
    assert request.consolidate
    assert not request.replace
    assert reducer.heartbeat(now=datetime.fromtimestamp(120, timezone.utc)) == ()


def test_heartbeat_refreshes_active_row_without_creating_terminal_output() -> None:
    reducer = RealtimeProjectionReducer(heartbeat_seconds=5)
    reducer.reduce(event(AgiEventType.TASK_START, 100.0, description="Build"))

    requests = reducer.heartbeat(now=datetime.fromtimestamp(106, timezone.utc))

    assert len(requests) == 1
    assert requests[0].heartbeat_due
    assert requests[0].elapsed_seconds == 6
    assert requests[0].content.endswith("6s")
    assert requests[0].replace
    assert reducer.heartbeat(now=datetime.fromtimestamp(107, timezone.utc)) == ()


def test_background_flag_survives_to_both_terminal_adapters() -> None:
    reducer = RealtimeProjectionReducer()
    request = activity(
        reducer.reduce(
            event(AgiEventType.TASK_START, 100.0, description="Index", background=True)
        )
    )
    assert request.background


def test_approval_resolution_targets_exact_attention_key() -> None:
    reducer = RealtimeProjectionReducer()
    requested = activity(
        reducer.reduce(
            event(
                AgiEventType.APPROVAL_REQUESTED,
                100.0,
                request_id="approval-7",
                status="awaiting_user",
                message="Executar?",
            )
        )
    )
    resolved = activity(
        reducer.reduce(
            event(
                AgiEventType.APPROVAL_RESOLVED,
                101.0,
                request_id="approval-7",
                status="running",
                message="Aprovado",
            )
        )
    )
    assert requested.key == "task:task-1/execution:approval-7"
    assert resolved.key == requested.key
    assert resolved.resolves_attention
    assert resolved.consolidate
    assert reducer.heartbeat(now=datetime.fromtimestamp(120, timezone.utc)) == ()


def test_tool_result_keeps_specific_grammar_when_transport_omits_args() -> None:
    reducer = RealtimeProjectionReducer()
    reducer.reduce(
        event(
            AgiEventType.TOOL_EXECUTING,
            100.0,
            execution_id="call-1",
            tool_name="run_shell_command",
            tool_args={"command": "pytest -q"},
        )
    )
    request = activity(
        reducer.reduce(
            event(
                AgiEventType.TOOL_RESULT,
                103.0,
                execution_id="call-1",
                tool_name="run_shell_command",
                success=True,
                result="12 passed",
            )
        )
    )
    assert "Testar pytest -q · completed" in request.content
    assert request.elapsed_seconds == 3
