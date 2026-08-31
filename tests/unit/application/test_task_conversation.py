"""Task-tree reduction and focused-conversation presentation contracts."""

from aura_cli.application.agents.events import AgiEvent, AgiEventType
from aura_cli.application.presentation.task_conversation import (
    filter_conversation_messages,
    find_task_entry,
    reduce_task_tree,
)


def event(
    kind: AgiEventType, task_id: str, data: dict, parent: str | None = None
) -> AgiEvent:
    return AgiEvent(type=kind, task_id=task_id, data=data, parent_task_id=parent)


def test_task_tree_lifecycle_is_pure_and_searches_descendants() -> None:
    original = {}
    tasks = reduce_task_tree(
        original, event(AgiEventType.TASK_START, "root", {"description": "Build"})
    )
    tasks = reduce_task_tree(
        tasks,
        event(AgiEventType.SUBTASK_START, "child", {"description": "Inspect"}, "root"),
    )
    tasks = reduce_task_tree(
        tasks, event(AgiEventType.SUBTASK_COMPLETE, "child", {"success": True}, "root")
    )

    assert original == {}
    assert tasks["root"]["name"] == "Build"
    assert find_task_entry(tasks, "child")["status"] == "completed"
    assert find_task_entry(tasks, "missing") is None


def test_tool_lifecycle_preserves_failed_result_status() -> None:
    tasks = reduce_task_tree({}, event(AgiEventType.TASK_START, "root", {}))
    tasks = reduce_task_tree(
        tasks,
        event(AgiEventType.TOOL_EXECUTING, "tool", {"tool_name": "shell"}, "root"),
    )
    tasks = reduce_task_tree(
        tasks, event(AgiEventType.TOOL_RESULT, "tool", {"success": False}, "root")
    )

    assert tasks["root"]["children"]["tool"]["status"] == "failed"


def test_conversation_focus_includes_global_messages_without_mutating_input() -> None:
    messages = [
        {"task_id": "global_chat", "content": "global"},
        {"task_id": "one", "content": "one"},
        {"task_id": "two", "content": "two"},
    ]

    assert [
        item["content"] for item in filter_conversation_messages(messages, "one")
    ] == [
        "global",
        "one",
    ]
    assert filter_conversation_messages(messages, None) == messages
    assert len(messages) == 3
