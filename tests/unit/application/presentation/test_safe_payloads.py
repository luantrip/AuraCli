import json

from aura_cli.application.agents.events import AgiEvent, AgiEventType
from aura_cli.application.presentation.agent_event_reducer import AgentEventStateReducer
from aura_cli.application.presentation.safe_payloads import (
    REDACTED_VALUE,
    redact_tool_args,
    safe_tool_args_json,
    sanitize_event_for_presentation,
    sanitize_intervention_context,
)
from aura_cli.application.presentation.task_conversation import reduce_task_tree
from aura_cli.core.events.human_intervention_events import (
    InterventionContext,
    RiskLevel,
)
from aura_cli.core.stats import get_stats


class EventStore:
    def __init__(self) -> None:
        self.tasks: dict[str, dict] = {}
        self.messages: list[dict] = []

    def add_task(self, task_id: str, task_data: dict) -> None:
        self.tasks[task_id] = task_data

    def get_task(self, task_id: str) -> dict | None:
        return self.tasks.get(task_id)

    def add_message(self, message: dict) -> None:
        self.messages.append(message)


def tool_event() -> AgiEvent:
    return AgiEvent(
        type=AgiEventType.TOOL_EXECUTING,
        task_id="exec-1",
        parent_task_id="root",
        timestamp=10.0,
        data={
            "tool_name": "run_shell_command",
            "tool_args": {
                "command": "cat /private/SECRET_SENTINEL",
                "token": "Bearer SECRET_SENTINEL",
                "nested": {"query": "SECRET_SENTINEL"},
            },
        },
    )


def test_redact_tool_args_preserves_shape_without_values() -> None:
    args = redact_tool_args(tool_event().data["tool_args"])

    assert args["command"] == REDACTED_VALUE
    assert args["token"] == REDACTED_VALUE
    assert args["nested"]["query"] == REDACTED_VALUE
    assert "SECRET_SENTINEL" not in safe_tool_args_json(args)


def test_sanitize_event_copies_only_tool_payload() -> None:
    event = tool_event()
    safe_event = sanitize_event_for_presentation(event)

    assert safe_event is not event
    assert event.data["tool_args"]["command"] == "cat /private/SECRET_SENTINEL"
    assert safe_event.data["tool_args"]["command"] == REDACTED_VALUE
    assert "SECRET_SENTINEL" not in json.dumps(safe_event.model_dump())


def test_reducer_chat_and_store_do_not_expose_raw_tool_args() -> None:
    store = EventStore()
    store.tasks["root"] = {"children": {}}
    reduction = AgentEventStateReducer(store).reduce(tool_event())

    serialized = json.dumps(
        {
            "chat": reduction.chat.content if reduction.chat else None,
            "store": store.tasks,
        }
    )
    assert "SECRET_SENTINEL" not in serialized
    assert (
        store.tasks["root"]["children"]["exec-1"]["tool_args"]["command"]
        == REDACTED_VALUE
    )


def test_task_tree_detail_event_is_sanitized() -> None:
    tree = {"root": {"children": {}}}
    reduced = reduce_task_tree(tree, tool_event())

    event = reduced["root"]["children"]["exec-1"]["event"]
    assert event.data["tool_args"]["command"] == REDACTED_VALUE
    assert "SECRET_SENTINEL" not in json.dumps(event.model_dump())


def test_intervention_context_copy_is_safe_and_original_is_unchanged() -> None:
    context = InterventionContext(
        tool_name="run_shell_command",
        tool_args={"command": "echo SECRET_SENTINEL"},
        risk_level=RiskLevel.HIGH,
    )
    safe_context = sanitize_intervention_context(context)

    assert safe_context is not context
    assert context.tool_args == {"command": "echo SECRET_SENTINEL"}
    assert safe_context.tool_args == {"command": REDACTED_VALUE}


def test_stats_compatibility_state_is_not_needed_for_redaction() -> None:
    assert hasattr(get_stats(), "skip_confirmations")
