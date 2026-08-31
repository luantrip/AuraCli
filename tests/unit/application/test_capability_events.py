from queue import Queue

from aura_cli.application.agents.event_emitter import AgiEventAdapter
from aura_cli.application.agents.events import (
    AgiEventType,
    create_capability_decision,
)
from aura_cli.application.agents.queue_event_emitter import QueueAgiAdapter
from aura_cli.application.presentation.event_bus import TypedEventBus
from aura_cli.application.tools.capability_broker import CapabilityDecision
from aura_cli.cli.ui.manager import UIManager
from aura_cli.core.events.contracts import (
    CapabilityDecisionPayload,
    validate_event,
)


def test_capability_decision_factory_matches_registered_contract() -> None:
    event = create_capability_decision(
        "task-1",
        "run_shell_command",
        allowed=False,
        requires_confirmation=False,
        risk_level="critical",
        reason="adapter ausente",
        phase="evaluation",
        execution_id="exec-1",
    )

    assert event["type"] == AgiEventType.CAPABILITY_DECISION.value
    assert event["task_id"] == "task-1"
    assert "tool_args" not in event["data"]
    payload = validate_event(event["type"], event["data"])
    assert payload is not None
    assert payload.tool_name == "run_shell_command"
    assert payload.allowed is False
    assert payload.phase == "evaluation"


def test_capability_decision_event_is_accepted_by_typed_event_bus() -> None:
    bus = TypedEventBus()
    bus.define(
        AgiEventType.CAPABILITY_DECISION.value,
        CapabilityDecisionPayload,
    )
    event = create_capability_decision(
        "task-2",
        "write_file",
        allowed=True,
        requires_confirmation=True,
        risk_level="high",
        reason="confirmação necessária",
        phase="decision",
    )

    assert bus.publish(event["type"], event["data"]) is True

    assert bus.get_history()[-1].event_type == AgiEventType.CAPABILITY_DECISION.value


def test_queue_adapter_emits_correlated_capability_decision() -> None:
    queue = Queue()
    adapter = QueueAgiAdapter(queue, task_id="task-queue")
    decision = CapabilityDecision(
        allowed=True,
        requires_confirmation=False,
        reason="safe",
        risk_level=None,
    )

    adapter.capability_decision("read_file", decision, phase="evaluation")
    event = queue.get_nowait()

    assert event["type"] == AgiEventType.CAPABILITY_DECISION.value
    assert event["task_id"] == "task-queue"
    assert event["data"]["allowed"] is True
    assert event["data"]["phase"] == "evaluation"


def test_ui_manager_emits_capability_decision_to_status_queue() -> None:
    queue = Queue()
    ui = UIManager(status_queue=queue)
    decision = CapabilityDecision(
        allowed=False,
        requires_confirmation=False,
        reason="denied",
        risk_level="critical",
    )

    ui.emit_capability_decision(
        "delete_file", decision, task_id="task-ui", phase="blocked"
    )
    event = queue.get_nowait()

    assert event["type"] == AgiEventType.CAPABILITY_DECISION.value
    assert event["task_id"] == "task-ui"
    assert event["data"]["reason"] == "denied"
    assert "tool_args" not in event["data"]


def test_event_adapter_emits_correlated_capability_decision() -> None:
    queue = Queue()
    adapter = AgiEventAdapter(queue, task_id="task-3")
    decision = CapabilityDecision(
        allowed=False,
        requires_confirmation=False,
        reason="bloqueada pela policy",
        risk_level="high",
    )

    adapter.capability_decision(
        "delete_file", decision, phase="commit", execution_id="exec-3"
    )
    event = queue.get_nowait()

    assert event["type"] == AgiEventType.CAPABILITY_DECISION.value
    assert event["task_id"] == "task-3"
    assert event["data"] == {
        "tool_name": "delete_file",
        "allowed": False,
        "requires_confirmation": False,
        "risk_level": "high",
        "reason": "bloqueada pela policy",
        "phase": "commit",
        "execution_id": "exec-3",
    }
