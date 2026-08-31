from unittest.mock import Mock, patch

from aura_cli.application.tools.execution_policy import TaskExecutionPolicy
from aura_cli.cli import tool_execution
from aura_cli.contracts.security import ToolAccessDecision


def test_headless_sink_receives_allowed_evaluation_without_tool_args() -> None:
    observations = []

    def sink(tool_name, decision, *, task_id=None, phase="evaluation"):
        observations.append((tool_name, decision, task_id, phase))

    with patch.object(tool_execution, "INTERVENTION_AVAILABLE", False):
        allowed = tool_execution._check_tool_requires_confirmation(
            "read_file",
            {"path": "/private/example.txt"},
            Mock(),
            capability_audit=sink,
        )

    assert allowed is True
    assert len(observations) == 1
    tool_name, decision, task_id, phase = observations[0]
    assert tool_name == "read_file"
    assert decision.allowed is True
    assert task_id is None
    assert phase == "evaluation"


def test_headless_sink_receives_blocked_access_with_task_id() -> None:
    observations = []

    def sink(tool_name, decision, *, task_id=None, phase="evaluation"):
        observations.append((tool_name, decision, task_id, phase))

    policy = TaskExecutionPolicy(
        task_id="task-headless", fail_closed_policy_errors=True
    )
    with patch.object(tool_execution, "get_execution_policy", return_value=policy):
        allowed = tool_execution._check_tool_requires_confirmation(
            "delete_file",
            {"path": "sentinel.txt"},
            Mock(),
            access_allowed=False,
            access_reason="denied by test policy",
            capability_audit=sink,
        )

    assert allowed is False
    assert len(observations) == 1
    tool_name, decision, task_id, phase = observations[0]
    assert tool_name == "delete_file"
    assert decision.allowed is False
    assert decision.reason == "denied by test policy"
    assert task_id == "task-headless"
    assert phase == "blocked"


def test_headless_sink_receives_commit_after_policy_reservation() -> None:
    observations = []

    def sink(tool_name, decision, *, task_id=None, phase="evaluation"):
        observations.append((tool_name, decision, task_id, phase))

    policy = TaskExecutionPolicy(task_id="task-commit")

    class TypedManager:
        def commit_access(self, function_name, agent_name, function_args):
            return ToolAccessDecision(allowed=True, reason=None)

    manager = TypedManager()
    manager.commit_access = Mock(wraps=manager.commit_access)
    with (
        patch.object(tool_execution, "get_execution_policy", return_value=policy),
        patch.object(tool_execution, "_get_policy_manager", return_value=manager),
    ):
        tool_execution._commit_policy_access(
            "read_file",
            {"path": "sentinel.txt"},
            capability_audit=sink,
        )

    manager.commit_access.assert_called_once_with(
        "read_file", "cli_agent", {"path": "sentinel.txt"}
    )
    assert len(observations) == 1
    assert observations[0][0] == "read_file"
    assert observations[0][2:] == ("task-commit", "commit")
    assert observations[0][1].allowed is True


def test_headless_sink_failure_does_not_change_safe_decision() -> None:
    def failing_sink(*args, **kwargs):
        raise RuntimeError("audit sink unavailable")

    with patch.object(tool_execution, "INTERVENTION_AVAILABLE", False):
        allowed = tool_execution._check_tool_requires_confirmation(
            "read_file",
            {},
            Mock(),
            capability_audit=failing_sink,
        )

    assert allowed is True
