from queue import Queue
from unittest.mock import Mock, patch

import pytest

from aura_cli.application.agents.event_emitter import AgiEventAdapter
from aura_cli.application.agents.events import (
    AgiEvent,
    AgiEventType,
    create_lifecycle_event,
)
from aura_cli.application.agents.operational_feedback import describe_operational_event
from aura_cli.application.presentation.agent_event_reducer import AgentEventStateReducer
from aura_cli.application.presentation.lifecycle_audit import audit_event_lifecycles
from aura_cli.application.presentation.state_store import ReactiveStateStore
from aura_cli.application.presentation.task_conversation import reduce_task_tree
from aura_cli.application.presentation.work_items import (
    WorkItemAttention,
    WorkItemState,
    work_item_from_agent_event,
)
from aura_cli.core.events.contracts import is_valid_event


class EventStore(ReactiveStateStore):
    def __init__(self) -> None:
        super().__init__({"tasks": {}, "messages": []})

    def add_task(self, task_id: str, task_data: dict) -> None:
        self.set(f"tasks.{task_id}", task_data)

    def get_task(self, task_id: str) -> dict | None:
        return self.get(f"tasks.{task_id}")

    def add_message(self, message: dict) -> None:
        self.set("messages", [*self.get("messages", []), message])


def lifecycle(
    event_type: AgiEventType,
    *,
    task_id: str = "task",
    status: str,
    message: str = "state changed",
    **data,
) -> AgiEvent:
    payload = create_lifecycle_event(
        event_type,
        task_id,
        status=status,
        message=message,
        **data,
    )
    return AgiEvent.from_dict(payload)


@pytest.mark.parametrize(
    ("event_type", "status"),
    [
        (AgiEventType.TASK_CANCELLED, "cancelled"),
        (AgiEventType.TASK_INTERRUPTED, "interrupted"),
        (AgiEventType.APPROVAL_REQUESTED, "awaiting_user"),
        (AgiEventType.APPROVAL_RESOLVED, "running"),
        (AgiEventType.EXTERNAL_WAIT_STARTED, "waiting_external"),
        (AgiEventType.EXTERNAL_WAIT_ENDED, "running"),
    ],
)
def test_explicit_lifecycle_payloads_pass_unified_contract(
    event_type: AgiEventType, status: str
) -> None:
    raw = create_lifecycle_event(
        event_type,
        "task",
        status=status,
        message="visible state",
        resumable=True,
    )
    assert is_valid_event(raw["type"], raw["data"])


def test_checkpoint_contract_is_registered() -> None:
    assert is_valid_event(
        AgiEventType.CHECKPOINT_CREATED,
        {
            "name": "before-edit",
            "status": "completed",
            "message": "Checkpoint created",
            "artifacts": ["checkpoint://1"],
            "resumable": True,
        },
    )


def test_emitter_produces_symmetric_approval_lifecycle() -> None:
    queue = Queue()
    adapter = AgiEventAdapter(queue)
    task_id = adapter.start_task("Build", "Refactor")
    adapter.request_approval("approval-1", "Run tests?", action="shell")
    adapter.resolve_approval("approval-1", approved=True)
    adapter.complete_task(True, "done")

    events = [AgiEvent.from_dict(queue.get_nowait()) for _ in range(4)]
    audit = audit_event_lifecycles(events)

    assert audit.is_symmetric
    assert audit.started == audit.terminal == (task_id,)
    assert not audit.resumable


def test_audit_accepts_visible_pending_state_and_detects_silent_dangling_task() -> None:
    started = AgiEvent(
        type=AgiEventType.TASK_START,
        task_id="task",
        data={"description": "Build"},
    )
    pending = lifecycle(
        AgiEventType.EXTERNAL_WAIT_STARTED,
        status="waiting_external",
        resumable=True,
    )

    assert audit_event_lifecycles([started]).incomplete == ("task",)
    audit = audit_event_lifecycles([started, pending])
    assert audit.is_symmetric
    assert audit.resumable == ("task",)


def test_audit_rejects_terminal_event_without_corresponding_start() -> None:
    cancelled = lifecycle(AgiEventType.TASK_CANCELLED, status="cancelled")
    audit = audit_event_lifecycles([cancelled])
    assert not audit.is_symmetric
    assert audit.orphan_terminal == ("task",)


@pytest.mark.parametrize(
    ("event", "expected", "attention"),
    [
        (
            lifecycle(AgiEventType.TASK_CANCELLED, status="cancelled"),
            WorkItemState.CANCELLED,
            WorkItemAttention.NONE,
        ),
        (
            lifecycle(
                AgiEventType.TASK_INTERRUPTED,
                status="interrupted",
                resumable=True,
            ),
            WorkItemState.INTERRUPTED,
            WorkItemAttention.PASSIVE,
        ),
        (
            lifecycle(
                AgiEventType.APPROVAL_REQUESTED,
                status="awaiting_user",
                request_id="approval",
                action="shell",
            ),
            WorkItemState.AWAITING_USER,
            WorkItemAttention.ACTION,
        ),
        (
            lifecycle(
                AgiEventType.EXTERNAL_WAIT_STARTED,
                status="waiting_external",
                resumable=True,
            ),
            WorkItemState.WAITING_EXTERNAL,
            WorkItemAttention.NONE,
        ),
    ],
)
def test_work_item_projection_covers_new_lifecycle(
    event: AgiEvent, expected: WorkItemState, attention: WorkItemAttention
) -> None:
    item = work_item_from_agent_event(event)
    assert item.state is expected
    assert item.attention is attention
    assert describe_operational_event(event) is not None


def test_reducer_and_task_tree_follow_error_and_resumable_interruption() -> None:
    store = EventStore()
    reducer = AgentEventStateReducer(store)
    start = AgiEvent(
        type=AgiEventType.TASK_START,
        task_id="task",
        data={"description": "Build"},
    )
    interrupted = lifecycle(
        AgiEventType.TASK_INTERRUPTED,
        status="interrupted",
        reason="timeout",
        resumable=True,
    )
    failed = lifecycle(
        AgiEventType.TASK_ERROR,
        status="failed",
        reason="worker crashed",
    )

    reducer.reduce(start)
    effect = reducer.reduce(interrupted)
    assert store.get_task("task")["status"] == "interrupted"
    assert store.get_task("task")["resumable"] is True
    assert effect.hide_thinking is True

    tree = reduce_task_tree(reduce_task_tree({}, start), interrupted)
    assert tree["task"]["status"] == "interrupted"

    reducer.reduce(failed)
    assert store.get_task("task")["status"] == "failed"
    assert store.get_task("task")["error"] == "worker crashed"


def test_worker_cancel_api_emits_terminal_event() -> None:
    from aura_cli.cli.workers.base_worker import BaseWorker

    worker = BaseWorker(task_id="task")
    worker.agi_event_adapter = Mock()
    worker.cancel("user stopped")

    assert worker._shutdown_event.is_set()
    worker.agi_event_adapter.cancel_task.assert_called_once_with("user stopped")


def test_human_intervention_brackets_legacy_request_with_canonical_lifecycle() -> None:
    from aura_cli.core.tools.human_intervention_adapter import HumanInterventionAdapter

    queue = Queue()
    emitter = Mock()
    adapter = HumanInterventionAdapter(queue, "task", lifecycle_emitter=emitter)
    adapter.responses["request-1"] = {"approved": True, "request_id": "request-1"}
    request = {
        "type": "human_intervention_request",
        "task_id": "task",
        "request_id": "request-1",
        "request_type": "confirmation",
        "prompt": "Run shell?",
        "timeout": 10,
    }

    with patch(
        "aura_cli.core.tools.human_intervention_adapter.create_confirmation_request",
        return_value=request,
    ):
        assert adapter.request_confirmation("Run shell?") is True

    emitter.request_approval.assert_called_once_with(
        "request-1", "Run shell?", action="confirmation", policy_key=None
    )
    emitter.resolve_approval.assert_called_once_with(
        "request-1", approved=True, message="Approval resolved", scope="once"
    )
    assert queue.get_nowait() == request


def test_notebook_snapshot_emits_checkpoint_artifact() -> None:
    from aura_cli.cli.workers.base_worker import BaseWorker

    worker = BaseWorker(task_id="task")
    worker.context_manager = Mock(
        conversation_history=[{"role": "user"}, {"role": "assistant"}]
    )
    worker._notebook_service = Mock()
    worker._notebook_service.create_snapshot.return_value = "snapshots/task.md"
    worker.agi_event_adapter = Mock()

    assert worker._create_notebook_snapshot() == "snapshots/task.md"
    worker.agi_event_adapter.checkpoint_created.assert_called_once_with(
        "notebook snapshot", "snapshots/task.md"
    )
