from aura_cli.contracts.security import ToolAccessDecision
from aura_cli.core.agents.tool_calling.tool_policies import (
    AccessLevel,
    PolicyManager,
    ToolPolicy,
)


def test_policy_manager_evaluate_access_returns_typed_decision() -> None:
    manager = PolicyManager()
    manager.add_policy(
        ToolPolicy(tool_name="write_file", access_level=AccessLevel.DENIED)
    )

    decision = manager.evaluate_access("write_file", "cli_agent", {"path": "x"})

    assert decision == ToolAccessDecision(
        allowed=False,
        reason="Acesso negado à ferramenta 'write_file'",
    )
    assert decision.as_legacy_tuple() == (
        False,
        "Acesso negado à ferramenta 'write_file'",
    )


def test_evaluate_access_does_not_consume_rate_limit() -> None:
    manager = PolicyManager()
    manager.add_policy(
        ToolPolicy(tool_name="read_file", access_level=AccessLevel.FULL, rate_limit=1)
    )

    first = manager.evaluate_access("read_file", "cli_agent", {})
    second = manager.evaluate_access("read_file", "cli_agent", {})

    assert first == ToolAccessDecision(allowed=True)
    assert second == ToolAccessDecision(allowed=True)
    assert manager.call_counts == {}


def test_commit_access_consumes_one_rate_limit_slot() -> None:
    manager = PolicyManager()
    manager.add_policy(
        ToolPolicy(tool_name="read_file", access_level=AccessLevel.FULL, rate_limit=1)
    )

    committed = manager.commit_access("read_file", "cli_agent", {})
    evaluated_after_commit = manager.evaluate_access("read_file", "cli_agent", {})
    second_commit = manager.commit_access("read_file", "cli_agent", {})

    assert committed == ToolAccessDecision(allowed=True)
    assert evaluated_after_commit == ToolAccessDecision(
        allowed=False, reason="Rate limit excedido para 'read_file'"
    )
    assert second_commit == evaluated_after_commit
    assert len(manager.call_counts["read_file:cli_agent"]) == 1


def test_policy_manager_legacy_tuple_remains_unchanged() -> None:
    manager = PolicyManager()
    manager.add_policy(
        ToolPolicy(tool_name="read_file", access_level=AccessLevel.FULL, rate_limit=1)
    )

    assert manager.check_access("read_file", "cli_agent", {}) == (True, None)
    assert manager.check_access("read_file", "cli_agent", {}) == (
        False,
        "Rate limit excedido para 'read_file'",
    )
