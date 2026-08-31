from pathlib import Path

from aura_cli.application.execution import OperationStatus, TurnExecution, TurnPhase
from aura_cli.core.sessions.turn_repository import AtomicTurnRepository


def test_atomic_repository_restores_complete_last_turn(tmp_path: Path) -> None:
    repository = AtomicTurnRepository(tmp_path / "sessions")
    turn = TurnExecution(session_id="session-1")
    turn.plan_operation("call-1", "write_file", {"path": str(tmp_path / "x")})
    turn.start_operation("call-1")
    turn.finish_operation("call-1", "ok", 0.2)
    turn.phase = TurnPhase.COMPLETED
    history = [
        {"role": "user", "content": "crie x"},
        {"role": "assistant", "content": "x criado"},
    ]

    repository.persist_turn(turn, history, current_directory="/workspace")
    restored = repository.restore_latest(current_directory="/workspace")

    assert restored is not None
    assert restored.conversation_history == history
    assert restored.last_turn is not None
    assert restored.last_turn.turn_id == turn.turn_id
    assert restored.last_turn.operations[0].tool_call_id == "call-1"
    assert restored.last_turn.operations[0].status is OperationStatus.SUCCEEDED
    assert restored.last_turn.operations[0].evidence.existed_before is False


def test_atomic_repository_replaces_same_turn_instead_of_duplicating(
    tmp_path: Path,
) -> None:
    repository = AtomicTurnRepository(tmp_path)
    turn = TurnExecution(session_id="same")

    repository.persist_turn(
        turn,
        [],
        current_directory="/workspace",
    )
    repository.persist_turn(
        turn, [{"role": "user", "content": "updated"}], current_directory="/workspace"
    )

    restored = repository.restore_session("same")
    assert restored is not None
    assert len(restored.turns) == 1
    assert restored.conversation_history[-1]["content"] == "updated"


def test_repository_document_never_contains_raw_sensitive_arguments(
    tmp_path: Path,
) -> None:
    repository = AtomicTurnRepository(tmp_path)
    turn = TurnExecution(session_id="safe")
    turn.plan_operation("secret", "run_shell_command", {"api_token": "do-not-store"})

    repository.persist_turn(
        turn,
        [{"role": "user", "content": "authorization: Bearer raw-secret"}],
        current_directory="/workspace",
    )

    persisted = (tmp_path / "safe.json").read_text(encoding="utf-8")
    assert "do-not-store" not in persisted
    assert "raw-secret" not in persisted
    assert "[REDACTED]" in persisted
    report = repository.export_sanitized_report(
        "safe", tmp_path / "reports" / "safe.json"
    )
    assert report.read_text(encoding="utf-8") == persisted
