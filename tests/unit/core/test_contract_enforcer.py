"""Tests for runtime contract enforcement."""

import pytest

from aura_cli.core.contracts.contract_enforcer import (
    Contract,
    ContractAction,
    ContractEnforcer,
    ContractViolationError,
)


def test_block_contract_raises_violation() -> None:
    enforcer = ContractEnforcer()
    enforcer.add_contract(Contract(
        name="no-drop",
        trigger="run_shell_command",
        action=ContractAction.BLOCK,
        message="DROP TABLE blocked",
        pattern=r"DROP\s+TABLE",
    ))

    ctx = {"tool_name": "run_shell_command", "arguments": {"command": "DROP TABLE users;"}}

    with pytest.raises(ContractViolationError, match="no-drop"):
        enforcer.check_before_tool_call(ctx)


def test_warn_contract_logs_but_allows() -> None:
    enforcer = ContractEnforcer()
    enforcer.add_contract(Contract(
        name="warn-rm",
        trigger="run_shell_command",
        action=ContractAction.WARN,
        message="Recursive delete detected",
        pattern=r"rm\s+-rf",
    ))

    ctx = {"tool_name": "run_shell_command", "arguments": {"command": "rm -rf /tmp"}}
    result = enforcer.check_before_tool_call(ctx)

    assert result == ctx
    assert len(enforcer.violation_log) == 1
    assert enforcer.violation_log[0]["action"] == "WARN"


def test_log_contract_records_silently() -> None:
    enforcer = ContractEnforcer()
    enforcer.add_contract(Contract(
        name="log-all",
        trigger="git_commit",
        action=ContractAction.LOG,
        message="Git commit observed",
    ))

    ctx = {"tool_name": "git_commit", "arguments": {"message": "wip"}}
    enforcer.check_before_tool_call(ctx)

    assert len(enforcer.violation_log) == 1
    assert enforcer.violation_log[0]["action"] == "LOG"


def test_no_matching_contract_allows() -> None:
    enforcer = ContractEnforcer()
    enforcer.add_contract(Contract(
        name="block-drop",
        trigger="run_shell_command",
        action=ContractAction.BLOCK,
        message="blocked",
        pattern=r"DROP\s+TABLE",
    ))

    ctx = {"tool_name": "read_file", "arguments": {"path": "main.py"}}
    result = enforcer.check_before_tool_call(ctx)

    assert result == ctx
    assert enforcer.violation_log == []


def test_condition_based_contract_evaluates() -> None:
    enforcer = ContractEnforcer()
    enforcer.add_contract(Contract(
        name="no-force-push-main",
        trigger="git_commit",
        action=ContractAction.BLOCK,
        message="Force push to main is blocked",
        condition="args.force and args.branch == 'main'",
    ))

    # Should block
    ctx = {"tool_name": "git_commit", "arguments": {"force": True, "branch": "main"}}
    with pytest.raises(ContractViolationError, match="no-force-push-main"):
        enforcer.check_before_tool_call(ctx)

    # Should allow non-main
    ctx2 = {"tool_name": "git_commit", "arguments": {"force": True, "branch": "dev"}}
    result = enforcer.check_before_tool_call(ctx2)
    assert result == ctx2


def test_load_profile_agi_safe() -> None:
    enforcer = ContractEnforcer()
    count = enforcer.load_profile("agi-safe")

    assert count >= 3
    assert enforcer.contract_count >= 3


def test_load_profile_unknown_returns_zero() -> None:
    enforcer = ContractEnforcer()
    count = enforcer.load_profile("nonexistent")

    assert count == 0


def test_violation_log_is_capped() -> None:
    enforcer = ContractEnforcer(_log_limit=3)  # type: ignore
    enforcer.add_contract(Contract(
        name="log-all",
        trigger="test_tool",
        action=ContractAction.LOG,
        message="logged",
    ))
    for _ in range(10):
        enforcer.check_before_tool_call({"tool_name": "test_tool", "arguments": {}})

    assert len(enforcer.violation_log) == 3


def test_contract_trigger_mismatch_does_not_match() -> None:
    contract = Contract(
        name="test",
        trigger="read_file",
        action=ContractAction.BLOCK,
        message="blocked",
    )

    assert not contract.matches("write_file", {})
    assert contract.matches("read_file", {})
