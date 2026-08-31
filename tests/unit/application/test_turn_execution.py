from aura_cli.application.agents.delegation import (
    DelegationLaunchOutcome,
    DelegationLaunchStatus,
    format_delegation_launch_outcome,
)
from aura_cli.application.execution import OperationStatus, TurnExecution
from aura_cli.application.tools.shell_policy import ShellCommandResult


def test_ledger_records_one_sanitized_operation_per_call(tmp_path) -> None:
    path = tmp_path / "created.txt"
    path.write_text("done")
    turn = TurnExecution(session_id="session-1", turn_id="turn-1")

    record = turn.plan_operation(
        "call-1", "write_file", {"path": str(path), "api_key": "secret"}
    )
    turn.start_operation("call-1")
    turn.finish_operation("call-1", "Arquivo criado com sucesso", 0.25)

    assert record.arguments_sanitized["api_key"] == "[REDACTED]"
    assert record.status is OperationStatus.SUCCEEDED
    assert record.evidence.existing_paths == [str(path)]


def test_ledger_rejects_duplicate_tool_call_id() -> None:
    turn = TurnExecution(session_id="session-1")
    turn.plan_operation("same", "read_file", {"path": "README.md"})

    try:
        turn.plan_operation("same", "read_file", {"path": "README.md"})
    except ValueError as error:
        assert "duplicate tool_call_id" in str(error)
    else:
        raise AssertionError("duplicate call was accepted")


def test_nonzero_exit_code_is_failure() -> None:
    turn = TurnExecution(session_id="session-1")
    turn.plan_operation("test-1", "run_shell_command", {"command": "pytest"})
    turn.start_operation("test-1")
    turn.finish_operation("test-1", {"exit_code": 4, "stdout": "failed"}, 1.0)

    assert turn.operation("test-1").status is OperationStatus.FAILED


def test_raised_operation_is_closed_as_failure() -> None:
    turn = TurnExecution(session_id="session-1")
    turn.plan_operation("call-1", "read_file", {"path": "missing"})
    turn.start_operation("call-1")

    turn.fail_operation("call-1", FileNotFoundError("missing"))

    record = turn.operation("call-1")
    assert record.status is OperationStatus.FAILED
    assert record.finished_at is not None
    assert record.duration is not None


def test_string_compatible_shell_result_preserves_exit_code() -> None:
    turn = TurnExecution(session_id="session-1")
    turn.plan_operation("call", "run_shell_command", {"command": "pytest"})
    turn.start_operation("call")

    turn.finish_operation("call", ShellCommandResult("1 failed", exit_code=1), 0.2)

    record = turn.operation("call")
    assert record.status is OperationStatus.FAILED
    assert record.evidence.exit_code == 1


def test_file_lists_are_ledger_projections(tmp_path) -> None:
    created = tmp_path / "created.py"
    turn = TurnExecution(session_id="session")
    turn.plan_operation("read", "read_file", {"path": "source.py"})
    turn.start_operation("read")
    turn.finish_operation("read", "content", 0.1)
    turn.plan_operation("write", "write_file", {"path": str(created)})
    turn.start_operation("write")
    created.write_text("pass")
    turn.finish_operation("write", "success", 0.1)

    assert turn.files_read == ["source.py"]
    assert turn.files_created == [str(created)]
    assert turn.files_edited == []


def test_overwriting_existing_file_projects_as_edit(tmp_path) -> None:
    path = tmp_path / "existing.py"
    path.write_text("before")
    turn = TurnExecution(session_id="session")
    turn.plan_operation("write", "write_file", {"path": str(path)})
    turn.start_operation("write")
    path.write_text("after")
    turn.finish_operation("write", "success", 0.1)

    assert turn.files_created == []
    assert turn.files_edited == [str(path)]


def test_delegation_launch_is_recorded_as_accepted_not_completed() -> None:
    receipt = format_delegation_launch_outcome(
        DelegationLaunchOutcome(
            DelegationLaunchStatus.STARTED,
            "ops",
            request="deploy",
            task_id="task-1",
            thread_name="worker-1",
        )
    )
    turn = TurnExecution(session_id="session")
    turn.plan_operation("call", "delegate_to_ops", {"task": "deploy"})
    turn.start_operation("call")
    turn.finish_operation("call", receipt, 0.013)

    assert turn.delegations[0].status == "accepted"
    assert turn.delegations[0].task_id == "task-1"
