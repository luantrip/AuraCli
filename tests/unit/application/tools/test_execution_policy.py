"""Task-scoped execution policy regressions."""

import threading
from unittest.mock import Mock, patch

import pytest

from aura_cli.application.tools.execution_policy import (
    TaskExecutionPolicy,
    execution_policy_context,
    get_execution_policy,
    set_task_auto_confirm,
)
from aura_cli.cli import tool_execution
from aura_cli.cli.utils.exceptions import ToolExecutionError
from aura_cli.contracts.security import ToolAccessDecision
from aura_cli.core.events.human_intervention_events import RiskLevel


def test_execution_policy_context_restores_previous_state() -> None:
    assert get_execution_policy() is None
    policy = TaskExecutionPolicy(
        task_id="task-a",
        auto_confirm=False,
        allow_dangerous=False,
        confirm_writes=True,
    )

    with execution_policy_context(policy):
        assert get_execution_policy() is policy
        assert set_task_auto_confirm(True) is True
        assert policy.auto_confirm is True

    assert get_execution_policy() is None


def test_concurrent_tasks_do_not_share_confirmation_policy() -> None:
    barrier = threading.Barrier(2)
    observed: dict[str, tuple[str, bool, bool]] = {}

    def run_task(task_id: str, allow_dangerous: bool) -> None:
        policy = TaskExecutionPolicy(
            task_id=task_id,
            auto_confirm=True,
            allow_dangerous=allow_dangerous,
            confirm_writes=False,
        )
        with execution_policy_context(policy):
            barrier.wait(timeout=2)
            current = get_execution_policy()
            assert current is policy
            observed[task_id] = (
                current.task_id,
                current.allow_dangerous,
                current.confirm_writes,
            )

    first = threading.Thread(target=run_task, args=("task-a", False))
    second = threading.Thread(target=run_task, args=("task-b", True))
    first.start()
    second.start()
    first.join(timeout=3)
    second.join(timeout=3)

    assert not first.is_alive()
    assert not second.is_alive()
    assert observed == {
        "task-a": ("task-a", False, False),
        "task-b": ("task-b", True, False),
    }
    assert get_execution_policy() is None


def test_task_auto_confirm_does_not_bypass_high_risk_intervention() -> None:
    context = Mock(tool_name="run_shell_command", tool_args={"command": "git status"})
    medium_request = (RiskLevel.MEDIUM, context, "confirm", 1)
    policy = TaskExecutionPolicy(
        task_id="task-medium",
        auto_confirm=True,
        allow_dangerous=False,
        confirm_writes=False,
    )

    with (
        patch.object(
            tool_execution.InterventionHelper,
            "build_tool_confirmation_request",
            return_value=medium_request,
        ),
        patch.object(tool_execution, "_intervention_adapter", None),
    ):
        with execution_policy_context(policy):
            assert (
                tool_execution._check_tool_requires_confirmation(
                    "run_shell_command", {"command": "git status"}, Mock(), None
                )
                is True
            )

    high_request = (RiskLevel.HIGH, context, "confirm high", 1)
    adapter = Mock()
    adapter.request_confirmation.return_value = False
    high_policy = TaskExecutionPolicy(
        task_id="task-high",
        auto_confirm=True,
        allow_dangerous=False,
        confirm_writes=False,
    )
    with (
        patch.object(
            tool_execution.InterventionHelper,
            "build_tool_confirmation_request",
            return_value=high_request,
        ),
        patch.object(tool_execution, "_intervention_adapter", adapter),
    ):
        with execution_policy_context(high_policy):
            assert (
                tool_execution._check_tool_requires_confirmation(
                    "run_shell_command", {"command": "rm -rf /"}, Mock(), None
                )
                is False
            )
    adapter.request_confirmation.assert_called_once()


def test_high_risk_task_without_adapter_is_rejected_fail_closed() -> None:
    context = Mock(tool_name="run_shell_command", tool_args={"command": "rm -rf /"})
    request = (RiskLevel.CRITICAL, context, "confirm critical", 1)
    policy = TaskExecutionPolicy(
        task_id="task-no-adapter",
        auto_confirm=True,
        allow_dangerous=False,
        confirm_writes=False,
    )

    with (
        patch.object(
            tool_execution.InterventionHelper,
            "build_tool_confirmation_request",
            return_value=request,
        ),
        patch.object(tool_execution, "_intervention_adapter", None),
    ):
        with execution_policy_context(policy):
            assert (
                tool_execution._check_tool_requires_confirmation(
                    "run_shell_command", {"command": "rm -rf /"}, Mock(), None
                )
                is False
            )


def test_capability_denial_reaches_ui_adapter_with_task_context() -> None:
    context = Mock(tool_name="run_shell_command", tool_args={"command": "rm -rf /"})
    request = (RiskLevel.CRITICAL, context, "confirm critical", 1)
    policy = TaskExecutionPolicy(
        task_id="task-ui-feedback",
        auto_confirm=True,
        allow_dangerous=False,
        confirm_writes=False,
    )
    ui = Mock()

    with (
        patch.object(
            tool_execution.InterventionHelper,
            "build_tool_confirmation_request",
            return_value=request,
        ),
        patch.object(tool_execution, "_intervention_adapter", None),
    ):
        with execution_policy_context(policy):
            assert (
                tool_execution._check_tool_requires_confirmation(
                    "run_shell_command", {"command": "rm -rf /"}, Mock(), ui
                )
                is False
            )

    ui.display_capability_decision.assert_called_once()
    args, kwargs = ui.display_capability_decision.call_args
    assert args[0] == "run_shell_command"
    assert args[1].allowed is False
    assert kwargs == {"task_id": "task-ui-feedback"}


def test_blocked_capability_falls_back_to_headless_warning() -> None:
    context = Mock(tool_name="run_shell_command", tool_args={"command": "rm -rf /"})
    request = (RiskLevel.CRITICAL, context, "confirm critical", 1)
    policy = TaskExecutionPolicy(
        task_id="task-headless",
        auto_confirm=True,
        allow_dangerous=False,
        confirm_writes=False,
    )
    ui = Mock(spec=tool_execution.UIManager)

    with (
        patch.object(
            tool_execution.InterventionHelper,
            "build_tool_confirmation_request",
            return_value=request,
        ),
        patch.object(tool_execution, "_intervention_adapter", None),
    ):
        with execution_policy_context(policy):
            assert (
                tool_execution._check_tool_requires_confirmation(
                    "run_shell_command", {"command": "rm -rf /"}, Mock(), ui
                )
                is False
            )

    ui.display_warning.assert_called_once_with(
        "Execução de run_shell_command bloqueada: "
        "Operação de alto risco rejeitada: adapter de intervenção ausente."
    )


def test_guard_uses_broker_for_one_policy_access_decision() -> None:
    manager = Mock()
    manager.check_access.return_value = (False, "somente leitura")
    ui = Mock()

    with (
        patch.object(tool_execution, "_get_policy_manager", return_value=manager),
        patch.object(tool_execution, "_run_ops_audit", return_value=True),
    ):
        with execution_policy_context(TaskExecutionPolicy(task_id="task-access")):
            with pytest.raises(
                ToolExecutionError,
                match="Execução de write_file bloqueada: Acesso negado pela política",
            ):
                tool_execution._check_execution_guards(
                    "write_file", {"path": "sentinel.txt"}, Mock(), ui
                )

    manager.check_access.assert_called_once_with(
        "write_file", "cli_agent", {"path": "sentinel.txt"}
    )
    ui.emit_capability_decision.assert_called_once()
    _, audit_kwargs = ui.emit_capability_decision.call_args
    assert audit_kwargs == {"task_id": "task-access", "phase": "blocked"}
    ui.display_capability_decision.assert_called_once()
    _, kwargs = ui.display_capability_decision.call_args
    assert kwargs == {"task_id": "task-access"}


def test_guard_and_runner_do_not_duplicate_policy_access_check() -> None:
    manager = Mock()
    manager.check_access.return_value = (True, None)

    with (
        patch.object(tool_execution, "_get_policy_manager", return_value=manager),
        patch.object(tool_execution, "_run_ops_audit", return_value=True),
        patch.object(tool_execution, "_get_tool_interceptor", return_value=None),
        patch.object(tool_execution, "_call_tool", return_value="ok"),
        patch.object(tool_execution, "_track_tool_feedback"),
    ):
        with execution_policy_context(TaskExecutionPolicy(task_id="task-once")):
            assert (
                tool_execution._check_execution_guards(
                    "read_file", {"path": "sentinel.txt"}, Mock(), Mock()
                )
                is None
            )
            assert (
                tool_execution._run_tool_with_interceptors(
                    "read_file",
                    {"path": "sentinel.txt"},
                    {},
                    None,
                    None,
                    True,
                )
                == "ok"
            )

    manager.check_access.assert_called_once_with(
        "read_file", "cli_agent", {"path": "sentinel.txt"}
    )


def test_runner_commits_typed_access_once_before_tool_call() -> None:
    events: list[str] = []

    class TypedManager:
        def evaluate_access(self, *args) -> ToolAccessDecision:
            events.append("evaluate")
            return ToolAccessDecision(allowed=True)

        def commit_access(self, *args) -> ToolAccessDecision:
            events.append("commit")
            return ToolAccessDecision(allowed=True)

        def check_access(self, *args):
            raise AssertionError("legacy tuple path should not be used")

    with (
        patch.object(
            tool_execution, "_get_policy_manager", return_value=TypedManager()
        ),
        patch.object(tool_execution, "_run_ops_audit", return_value=True),
        patch.object(tool_execution, "_get_tool_interceptor", return_value=None),
        patch.object(tool_execution, "_call_tool", return_value="ok"),
        patch.object(tool_execution, "_track_tool_feedback"),
    ):
        with execution_policy_context(TaskExecutionPolicy(task_id="task-commit")):
            assert (
                tool_execution._check_execution_guards(
                    "read_file", {"path": "sentinel.txt"}, Mock(), Mock()
                )
                is None
            )
            assert (
                tool_execution._run_tool_with_interceptors(
                    "read_file",
                    {"path": "sentinel.txt"},
                    {},
                    None,
                    None,
                    True,
                )
                == "ok"
            )

    assert events == ["evaluate", "commit"]


def test_executor_prefers_typed_access_contract() -> None:
    class TypedOnlyManager:
        def evaluate_access(
            self, tool_name: str, agent_id: str, parameters: dict
        ) -> ToolAccessDecision:
            assert (tool_name, agent_id, parameters) == (
                "read_file",
                "cli_agent",
                {"path": "sentinel.txt"},
            )
            return ToolAccessDecision(allowed=True)

        def check_access(self, *args):
            raise AssertionError("legacy tuple path should not be used")

    with patch.object(
        tool_execution, "_get_policy_manager", return_value=TypedOnlyManager()
    ):
        with execution_policy_context(TaskExecutionPolicy(task_id="task-typed")):
            assert tool_execution._evaluate_policy_access(
                "read_file", {"path": "sentinel.txt"}
            ) == (True, None)


def test_policy_denial_is_typed_and_stops_tool_execution() -> None:
    manager = Mock()
    manager.check_access.return_value = (False, "somente leitura")

    with patch.object(tool_execution, "_get_policy_manager", return_value=manager):
        with pytest.raises(ToolExecutionError, match="Acesso negado pela política"):
            tool_execution._run_policy_check("write_file", {"path": "x"})


def test_policy_failure_is_fail_closed_inside_task() -> None:
    manager = Mock()
    manager.check_access.side_effect = RuntimeError("broker indisponível")
    policy = TaskExecutionPolicy(task_id="task-policy-error")

    with patch.object(tool_execution, "_get_policy_manager", return_value=manager):
        with execution_policy_context(policy):
            with pytest.raises(ToolExecutionError, match="Failed to evaluate tool policy"):
                tool_execution._run_policy_check("run_shell_command", {"command": "ls"})


def test_policy_failure_keeps_legacy_fallback_outside_task() -> None:
    manager = Mock()
    manager.check_access.side_effect = RuntimeError("broker indisponível")

    with patch.object(tool_execution, "_get_policy_manager", return_value=manager):
        tool_execution._run_policy_check("read_file", {"path": "README.md"})
