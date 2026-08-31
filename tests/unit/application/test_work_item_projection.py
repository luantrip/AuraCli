import pytest

from aura_cli.application.presentation.tui_surfaces import PresentationIntent
from aura_cli.application.presentation.work_item_projection import (
    ProjectionTone,
    project_work_item,
    surface_requests_from_projection,
)
from aura_cli.application.presentation.work_items import (
    WorkItemAttention,
    WorkItemCapability,
    WorkItemEnvelope,
    WorkItemEvidence,
    WorkItemIdentity,
    WorkItemKind,
    WorkItemState,
)


def item(
    state: WorkItemState,
    *,
    kind: WorkItemKind = WorkItemKind.TOOL,
    attention: WorkItemAttention = WorkItemAttention.NONE,
) -> WorkItemEnvelope:
    return WorkItemEnvelope(
        identity=WorkItemIdentity(
            session_id="session", turn_id="turn", execution_id="call"
        ),
        kind=kind,
        state=state,
        summary="Executar testes",
        detail="pytest -q",
        attention=attention,
        evidence=WorkItemEvidence(
            summary="12 passed",
            paths=("tests/",),
            artifact_refs=("artifact://log",),
            exit_code=0,
        ),
        capabilities=frozenset({WorkItemCapability.INSPECT}),
    )


@pytest.mark.parametrize(
    "state",
    [
        WorkItemState.QUEUED,
        WorkItemState.PREPARING,
        WorkItemState.RUNNING,
        WorkItemState.STREAMING,
        WorkItemState.WAITING_EXTERNAL,
        WorkItemState.AWAITING_USER,
    ],
)
def test_transient_states_stay_out_of_conversation(state: WorkItemState) -> None:
    projection = project_work_item(item(state))
    assert projection.conversation is None
    assert projection.activity is not None
    assert projection.activity.replace is True


def test_completed_item_projects_durable_summary_and_full_inspection() -> None:
    projection = project_work_item(item(WorkItemState.COMPLETED))
    assert projection.conversation is not None
    assert "12 passed" in projection.conversation.content
    assert projection.activity.tone is ProjectionTone.SUCCESS
    assert projection.inspection.paths == ("tests/",)
    assert projection.inspection.artifact_refs == ("artifact://log",)
    assert projection.inspection.exit_code == 0


def test_failure_is_persistent_actionable_and_inspectable() -> None:
    projection = project_work_item(
        item(WorkItemState.FAILED, attention=WorkItemAttention.CRITICAL)
    )
    assert projection.conversation is not None
    assert projection.attention is not None
    assert projection.attention.tone is ProjectionTone.ERROR
    assert projection.attention.blocking is False


def test_approval_is_blocking_attention_but_not_chat_telemetry() -> None:
    projection = project_work_item(
        item(WorkItemState.AWAITING_USER, attention=WorkItemAttention.ACTION)
    )
    assert projection.conversation is None
    assert projection.attention is not None
    assert projection.attention.blocking is True
    assert projection.attention.title == "Ação necessária"


def test_checkpoint_stays_in_activity_and_inspection() -> None:
    projection = project_work_item(
        item(WorkItemState.COMPLETED, kind=WorkItemKind.CHECKPOINT)
    )
    assert projection.conversation is None
    assert projection.activity.tone is ProjectionTone.SUCCESS


def test_projection_identity_is_stable_across_lifecycle_updates() -> None:
    running = project_work_item(item(WorkItemState.RUNNING))
    completed = project_work_item(item(WorkItemState.COMPLETED))
    assert running.identity_key == completed.identity_key
    assert running.activity.key == completed.activity.key


def test_surface_requests_keep_transient_activity_out_of_conversation() -> None:
    projection = project_work_item(item(WorkItemState.RUNNING))
    requests = surface_requests_from_projection(projection, task_id="task")
    assert [request.intent for request in requests] == [PresentationIntent.PROGRESS]
    assert requests[0].task_id == "task"
    assert requests[0].key == projection.identity_key
    assert requests[0].tone == projection.activity.tone.value
    assert requests[0].replace


def test_surface_requests_make_approval_a_blocking_decision() -> None:
    projection = project_work_item(
        item(WorkItemState.AWAITING_USER, attention=WorkItemAttention.ACTION)
    )
    requests = surface_requests_from_projection(projection, task_id="task")
    assert [request.intent for request in requests] == [
        PresentationIntent.PROGRESS,
        PresentationIntent.DECISION,
    ]
