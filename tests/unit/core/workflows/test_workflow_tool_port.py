"""Contracts for guarded tool execution in user workflows."""

from unittest.mock import Mock, patch

from aura_cli.core.workflows.user_workflow import UserWorkflowManager


def test_workflow_tool_step_is_blocked_without_adapter(tmp_path) -> None:
    manager = UserWorkflowManager(storage_path=tmp_path)

    with patch("aura_cli.core.service_registry.get_service_registry") as get_registry:
        result = manager._execute_tool("write_file", {"path": "x"}, 30)

    assert result["success"] is False
    assert "not configured" in result["error"]
    get_registry.assert_not_called()


def test_workflow_tool_step_uses_injected_port(tmp_path) -> None:
    executor = Mock(return_value="done")
    manager = UserWorkflowManager(storage_path=tmp_path, tool_executor=executor)

    result = manager._execute_tool("read_file", {"path": "x"}, 45)

    assert result == {"success": True, "output": "done"}
    executor.assert_called_once_with("read_file", {"path": "x"}, 45)
