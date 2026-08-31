"""
Tests for the Pydantic-based AGI events system.
"""

from aura_cli.core.events.agi_events import (
    AgiEvent,
    AgiEventType,
    AgiTaskCompleteEvent,
    AgiTaskStartEvent,
    AgiTaskUpdateEvent,
    ChatMessageEvent,
    ToolExecutingEvent,
    ToolResultEvent,
    create_chat_message,
    create_task_complete,
    create_task_start,
    create_task_update,
    create_tool_executing,
    create_tool_result,
)


class TestAgiEventType:
    def test_values(self):
        assert AgiEventType.TASK_START.value == "agi_task_start"
        assert AgiEventType.TOOL_EXECUTING.value == "tool_executing"
        assert AgiEventType.CHAT_MESSAGE.value == "chat_message"


class TestAgiEvent:
    def test_creation(self):
        event = AgiEvent(
            type=AgiEventType.TASK_START,
            task_id="task_1",
            data={"key": "value"},
        )
        assert event.type == AgiEventType.TASK_START
        assert event.task_id == "task_1"
        assert event.data == {"key": "value"}
        assert event.parent_task_id is None
        assert isinstance(event.timestamp, float)

    def test_to_dict(self):
        event = AgiEvent(
            type=AgiEventType.TASK_START,
            task_id="task_1",
            data={"key": "value"},
        )
        d = event.to_dict()
        assert d["type"] == "agi_task_start"
        assert d["task_id"] == "task_1"
        assert d["data"] == {"key": "value"}

    def test_from_dict(self):
        data = {
            "type": "agi_task_start",
            "task_id": "task_1",
            "timestamp": 1234567890.0,
            "data": {"key": "value"},
            "parent_task_id": None,
        }
        event = AgiEvent.from_dict(data)
        assert event.type == AgiEventType.TASK_START
        assert event.task_id == "task_1"
        assert event.timestamp == 1234567890.0


class TestAgiTaskStartEvent:
    def test_create(self):
        event = AgiTaskStartEvent.create(
            task_id="task_1",
            description="Test task",
            objective="Complete testing",
            parent_task_id="parent_1",
        )
        assert event.type == AgiEventType.TASK_START
        assert event.task_id == "task_1"
        assert event.parent_task_id == "parent_1"
        assert event.data["description"] == "Test task"
        assert event.data["objective"] == "Complete testing"
        assert event.data["status"] == "starting"


class TestAgiTaskUpdateEvent:
    def test_create(self):
        event = AgiTaskUpdateEvent.create(
            task_id="task_1",
            status="running",
            message="Making progress",
            details={"progress": 50},
        )
        assert event.type == AgiEventType.TASK_UPDATE
        assert event.data["status"] == "running"
        assert event.data["message"] == "Making progress"
        assert event.data["details"]["progress"] == 50


class TestAgiTaskCompleteEvent:
    def test_create_success(self):
        event = AgiTaskCompleteEvent.create(
            task_id="task_1",
            success=True,
            result="Task completed successfully",
            stats={"duration": 10},
        )
        assert event.type == AgiEventType.TASK_COMPLETE
        assert event.data["success"] is True
        assert event.data["status"] == "completed"
        assert event.data["result"] == "Task completed successfully"

    def test_create_failure(self):
        event = AgiTaskCompleteEvent.create(
            task_id="task_1",
            success=False,
            error="Something went wrong",
        )
        assert event.data["success"] is False
        assert event.data["status"] == "failed"
        assert event.data["error"] == "Something went wrong"


class TestToolExecutingEvent:
    def test_create(self):
        event = ToolExecutingEvent.create(
            task_id="task_1",
            tool_name="read_file",
            tool_args={"path": "test.py"},
            parent_task_id="parent_1",
            execution_id="exec_1",
        )
        assert event.type == AgiEventType.TOOL_EXECUTING
        assert event.data["tool_name"] == "read_file"
        assert event.data["tool_args"]["path"] == "test.py"
        assert event.data["status"] == "executing"
        assert event.data["execution_id"] == "exec_1"


class TestToolResultEvent:
    def test_create_success(self):
        event = ToolResultEvent.create(
            task_id="task_1",
            tool_name="read_file",
            success=True,
            result="file contents",
            execution_time=0.5,
            parent_task_id="parent_1",
            execution_id="exec_1",
        )
        assert event.type == AgiEventType.TOOL_RESULT
        assert event.data["success"] is True
        assert event.data["status"] == "completed"
        assert event.data["execution_time"] == 0.5
        assert event.data["execution_id"] == "exec_1"
        assert event.parent_task_id == "parent_1"

    def test_create_failure(self):
        event = ToolResultEvent.create(
            task_id="task_1",
            tool_name="read_file",
            success=False,
            result=None,
            error="File not found",
        )
        assert event.data["success"] is False
        assert event.data["status"] == "failed"
        assert event.data["error"] == "File not found"


class TestChatMessageEvent:
    def test_create(self):
        event = ChatMessageEvent.create(
            sender="user",
            content="Hello, Aura!",
            task_id="chat_1",
            metadata={"source": "cli"},
        )
        assert event.type == AgiEventType.CHAT_MESSAGE
        assert event.data["sender"] == "user"
        assert event.data["content"] == "Hello, Aura!"
        assert event.data["metadata"]["source"] == "cli"

    def test_from_dict(self):
        data = {
            "type": "chat_message",
            "task_id": "chat_1",
            "timestamp": 1234567890.0,
            "data": {
                "sender": "assistant",
                "content": "Hello!",
                "metadata": {},
            },
        }
        event = ChatMessageEvent.from_dict(data)
        assert event.data["sender"] == "assistant"
        assert event.data["content"] == "Hello!"


class TestFactoryFunctions:
    def test_create_task_start(self):
        d = create_task_start("task_1", "Description", "Objective")
        assert d["type"] == "agi_task_start"
        assert d["task_id"] == "task_1"

    def test_create_task_update(self):
        d = create_task_update("task_1", "running", "Working...")
        assert d["type"] == "agi_task_update"
        assert d["data"]["status"] == "running"

    def test_create_task_complete(self):
        d = create_task_complete("task_1", True, "Done")
        assert d["type"] == "agi_task_complete"
        assert d["data"]["success"] is True

    def test_create_tool_executing(self):
        d = create_tool_executing("task_1", "tool", {"arg": "val"})
        assert d["type"] == "tool_executing"
        assert d["data"]["tool_name"] == "tool"

    def test_create_tool_result(self):
        d = create_tool_result("task_1", "tool", True, "result")
        assert d["type"] == "tool_result"
        assert d["data"]["success"] is True

    def test_create_chat_message(self):
        d = create_chat_message("user", "Hello")
        assert d["type"] == "chat_message"
        assert d["data"]["sender"] == "user"
