"""Contract tests for task-local confirmation decisions."""

from __future__ import annotations

from unittest.mock import patch

from aura_cli.application.tools.execution_policy import (
    TaskExecutionPolicy,
    execution_policy_context,
)
from aura_cli.core.events.human_intervention_events import (
    InterventionContext,
    RiskLevel,
)
from aura_cli.core.tools.human_intervention_adapter import (
    InterventionHelper,
    confirm_tool_execution_locally,
)


def test_task_policy_rejects_high_risk_without_dangerous_capability() -> None:
    request_context = InterventionContext(
        tool_name="run_shell_command",
        risk_level=RiskLevel.HIGH,
    )
    with patch.object(
        InterventionHelper,
        "build_tool_confirmation_request",
        return_value=(RiskLevel.HIGH, request_context, "confirm", 1),
    ):
        with execution_policy_context(
            TaskExecutionPolicy(
                task_id="subagent:task",
                auto_confirm=True,
                allow_dangerous=False,
                confirm_writes=False,
            )
        ):
            assert (
                confirm_tool_execution_locally(
                    "run_shell_command",
                    {"command": "rm -rf /"},
                    fallback_message="confirm",
                )
                is False
            )


def test_task_policy_can_auto_confirm_explicit_medium_write() -> None:
    request_context = InterventionContext(
        tool_name="write_file",
        risk_level=RiskLevel.MEDIUM,
    )
    with patch.object(
        InterventionHelper,
        "build_tool_confirmation_request",
        return_value=(RiskLevel.MEDIUM, request_context, "confirm", 1),
    ):
        with execution_policy_context(
            TaskExecutionPolicy(
                task_id="subagent:task",
                auto_confirm=True,
                allow_dangerous=False,
                confirm_writes=False,
            )
        ):
            assert (
                confirm_tool_execution_locally(
                    "write_file",
                    {"path": "safe.txt", "content": "ok"},
                    fallback_message="confirm",
                )
                is True
            )
