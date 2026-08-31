from aura_cli.application.tools.capability_broker import decide_tool_capability
from aura_cli.application.tools.execution_policy import TaskExecutionPolicy
from aura_cli.core.events.human_intervention_events import RiskLevel


def test_no_risk_does_not_require_confirmation() -> None:
    decision = decide_tool_capability(None)

    assert decision.allowed is True
    assert decision.requires_confirmation is False
    assert decision.risk_level is None


def test_medium_risk_is_auto_confirmed_by_task_policy() -> None:
    policy = TaskExecutionPolicy(task_id="task-medium", auto_confirm=True)

    decision = decide_tool_capability(RiskLevel.MEDIUM, policy=policy)

    assert decision.allowed is True
    assert decision.requires_confirmation is False
    assert "task-local" in decision.reason


def test_high_risk_without_adapter_fails_closed() -> None:
    policy = TaskExecutionPolicy(
        task_id="task-high",
        auto_confirm=True,
        allow_dangerous=False,
        fail_closed_without_adapter=True,
    )

    decision = decide_tool_capability(
        RiskLevel.HIGH,
        policy=policy,
        adapter_available=False,
    )

    assert decision.allowed is False
    assert decision.requires_confirmation is False
    assert "adapter" in decision.reason


def test_high_risk_with_adapter_still_requires_confirmation() -> None:
    policy = TaskExecutionPolicy(
        task_id="task-high",
        auto_confirm=True,
        allow_dangerous=False,
    )

    decision = decide_tool_capability(
        RiskLevel.HIGH,
        policy=policy,
        adapter_available=True,
    )

    assert decision.allowed is True
    assert decision.requires_confirmation is True


def test_policy_denial_is_explainable() -> None:
    decision = decide_tool_capability(
        RiskLevel.LOW,
        access_allowed=False,
        access_reason="somente leitura",
    )

    assert decision.allowed is False
    assert decision.requires_confirmation is False
    assert decision.reason == "somente leitura"
