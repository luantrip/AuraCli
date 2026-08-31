from datetime import datetime, timezone

import pytest

from aura_cli.application.agents.events import AgiEvent, AgiEventType
from aura_cli.application.execution import OperationStatus, TurnExecution, TurnPhase
from aura_cli.application.presentation.work_item_projection import (
    RealtimeProjectionReducer,
)
from aura_cli.application.presentation.work_items import (
    WorkItemAttention,
    WorkItemCapability,
    WorkItemEnvelope,
    WorkItemIdentity,
    WorkItemKind,
    WorkItemState,
    transition_work_item,
    work_item_from_agent_event,
    work_item_from_operation,
    work_item_from_turn,
)

NOW = datetime(2026, 8, 13, 12, 0, tzinfo=timezone.utc)


def envelope(state: WorkItemState = WorkItemState.QUEUED) -> WorkItemEnvelope:
    return WorkItemEnvelope(
        identity=WorkItemIdentity(session_id="session", turn_id="turn"),
        kind=WorkItemKind.TURN,
        state=state,
        summary="Refatorar",
        updated_at=NOW,
    )


def agent_event(
    event_type: AgiEventType,
    *,
    task_id: str = "task-1",
    data: dict | None = None,
    parent_task_id: str | None = None,
) -> AgiEvent:
    return AgiEvent(
        type=event_type,
        task_id=task_id,
        parent_task_id=parent_task_id,
        timestamp=NOW.timestamp(),
        data=data or {},
    )


def test_identity_requires_a_correlation_key_and_builds_stable_key() -> None:
    with pytest.raises(ValueError, match="correlation key"):
        WorkItemIdentity()

    identity = WorkItemIdentity(
        session_id="s", turn_id="t", task_id="a", execution_id="x"
    )
    assert identity.stable_key == "session:s/turn:t/task:a/execution:x"


def test_identity_preserves_request_and_tool_call_correlation() -> None:
    identity = WorkItemIdentity(request_id="request-1", tool_call_id="tool-1")
    assert identity.stable_key == "execution:request-1"
    restored = WorkItemIdentity(**identity.__dict__)
    assert restored == identity


def test_transition_derives_started_time_attention_and_capabilities() -> None:
    running = transition_work_item(envelope(), WorkItemState.RUNNING, now=NOW)
    assert running.started_at == NOW
    assert WorkItemCapability.CANCEL in running.capabilities

    awaiting = transition_work_item(
        running, WorkItemState.AWAITING_USER, summary="Autorizar shell", now=NOW
    )
    assert awaiting.attention is WorkItemAttention.ACTION
    assert WorkItemCapability.APPROVE in awaiting.capabilities
    assert WorkItemCapability.DECLINE in awaiting.capabilities


def test_terminal_state_cannot_be_resurrected() -> None:
    completed = transition_work_item(
        transition_work_item(envelope(), WorkItemState.RUNNING, now=NOW),
        WorkItemState.COMPLETED,
        now=NOW,
    )
    assert completed.is_terminal
    assert completed.finished_at == NOW
    with pytest.raises(ValueError, match="completed -> running"):
        transition_work_item(completed, WorkItemState.RUNNING, now=NOW)


def test_envelope_round_trip_preserves_identity_state_and_capabilities() -> None:
    running = transition_work_item(envelope(), WorkItemState.RUNNING, now=NOW)
    restored = WorkItemEnvelope.from_dict(running.to_dict())
    assert restored == running
    assert running.to_dict()["schema_version"] == WorkItemEnvelope.CONTRACT_VERSION


def test_legacy_envelope_without_schema_version_defaults_to_current_contract() -> None:
    payload = envelope().to_dict()
    payload.pop("schema_version")
    restored = WorkItemEnvelope.from_dict(payload)
    assert restored.schema_version == WorkItemEnvelope.CONTRACT_VERSION


def test_interrupted_item_can_resume_but_declined_item_is_terminal() -> None:
    running = transition_work_item(envelope(), WorkItemState.RUNNING, now=NOW)
    interrupted = transition_work_item(running, WorkItemState.INTERRUPTED, now=NOW)
    assert WorkItemCapability.RESUME in interrupted.capabilities
    assert (
        transition_work_item(interrupted, WorkItemState.RUNNING).state
        is WorkItemState.RUNNING
    )

    waiting = transition_work_item(running, WorkItemState.AWAITING_USER, now=NOW)
    declined = transition_work_item(waiting, WorkItemState.DECLINED, now=NOW)
    assert declined.is_terminal


@pytest.mark.parametrize(
    ("phase", "expected"),
    [
        (TurnPhase.THINKING, WorkItemState.PREPARING),
        (TurnPhase.EXECUTING, WorkItemState.RUNNING),
        (TurnPhase.RESPONDING, WorkItemState.STREAMING),
        (TurnPhase.COMPLETED, WorkItemState.COMPLETED),
        (TurnPhase.FAILED, WorkItemState.FAILED),
        (TurnPhase.INTERRUPTED, WorkItemState.INTERRUPTED),
    ],
)
def test_turn_projection_maps_phase_without_mutating_ledger(
    phase: TurnPhase, expected: WorkItemState
) -> None:
    turn = TurnExecution(session_id="session", turn_id="turn", phase=phase)
    item = work_item_from_turn(turn)
    assert item.identity.session_id == "session"
    assert item.identity.turn_id == "turn"
    assert item.state is expected
    assert turn.phase is phase


def test_operation_projection_preserves_full_correlation_and_evidence() -> None:
    turn = TurnExecution(session_id="session", turn_id="turn")
    operation = turn.plan_operation("call-1", "edit_file", {"file_path": "a.py"})
    operation.status = OperationStatus.SUCCEEDED
    operation.result_summary = "Arquivo atualizado"
    operation.output_reference = "artifact://diff/1"
    operation.evidence.exit_code = 0

    item = work_item_from_operation(turn, operation)

    assert item.identity.operation_id == operation.operation_id
    assert item.identity.execution_id == "call-1"
    assert item.identity.turn_id == "turn"
    assert item.state is WorkItemState.COMPLETED
    assert item.evidence.paths == ("a.py",)
    assert item.evidence.artifact_refs == ("artifact://diff/1",)
    assert item.evidence.exit_code == 0


def test_agent_waiting_for_human_becomes_actionable() -> None:
    item = work_item_from_agent_event(
        agent_event(
            AgiEventType.TASK_UPDATE,
            data={
                "status": "waiting",
                "message": "Preciso de autorização",
                "turn_id": "turn",
                "details": {"supervisor_state": "awaiting_human"},
            },
        )
    )
    assert item.identity.task_id == "task-1"
    assert item.identity.turn_id == "turn"
    assert item.state is WorkItemState.AWAITING_USER
    assert item.attention is WorkItemAttention.ACTION
    assert WorkItemCapability.APPROVE in item.capabilities


def test_agent_error_and_checkpoint_cover_previously_unprojected_events() -> None:
    failed = work_item_from_agent_event(
        agent_event(AgiEventType.TASK_ERROR, data={"error": "worker crashed"})
    )
    checkpoint = work_item_from_agent_event(
        agent_event(
            AgiEventType.CHECKPOINT_CREATED,
            data={"name": "checkpoint-1", "artifacts": ["checkpoint://1"]},
        )
    )

    assert failed.state is WorkItemState.FAILED
    assert failed.attention is WorkItemAttention.CRITICAL
    assert WorkItemCapability.RETRY in failed.capabilities
    assert checkpoint.kind is WorkItemKind.CHECKPOINT
    assert checkpoint.state is WorkItemState.COMPLETED
    assert checkpoint.evidence.artifact_refs == ("checkpoint://1",)


def test_tool_event_keeps_parent_and_execution_identity() -> None:
    item = work_item_from_agent_event(
        agent_event(
            AgiEventType.TOOL_EXECUTING,
            task_id="tool-task",
            parent_task_id="agent-task",
            data={
                "tool_name": "read_file",
                "execution_id": "call-7",
                "request_id": "request-7",
                "tool_call_id": "call-7",
                "tool_args": {"path": "src/app.py"},
            },
        )
    )
    assert item.kind is WorkItemKind.TOOL
    assert item.identity.parent_task_id == "agent-task"
    assert item.identity.execution_id == "call-7"
    assert item.identity.request_id == "request-7"
    assert item.identity.tool_call_id == "call-7"
    assert item.evidence.paths == ("src/app.py",)
    assert item.summary == "Ler src/app.py"


def test_tool_result_projects_specific_test_evidence() -> None:
    item = work_item_from_agent_event(
        agent_event(
            AgiEventType.TOOL_RESULT,
            data={
                "tool_name": "run_shell_command",
                "tool_args": {"command": "pytest -q"},
                "success": True,
                "result": {"passed": 12, "failed": 0, "skipped": 1},
            },
        )
    )
    assert item.summary == "Testar pytest -q"
    assert item.evidence.summary == "passed=12 · failed=0 · skipped=1"


@pytest.mark.parametrize("event_type", list(AgiEventType))
def test_every_agent_event_type_has_a_valid_work_item_projection(
    event_type: AgiEventType,
) -> None:
    item = work_item_from_agent_event(agent_event(event_type))
    assert item.identity.task_id == "task-1"
    assert isinstance(item.state, WorkItemState)


@pytest.mark.parametrize("event_type", list(AgiEventType))
def test_every_agent_event_type_has_one_shared_terminal_surface_projection(
    event_type: AgiEventType,
) -> None:
    event = agent_event(event_type)
    requests = RealtimeProjectionReducer().reduce(event)

    if event_type is AgiEventType.CHAT_MESSAGE:
        assert requests == ()
    else:
        assert requests
        assert all(request.task_id == event.task_id for request in requests)
        assert all(request.key for request in requests)
