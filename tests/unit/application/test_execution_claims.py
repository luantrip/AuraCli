from aura_cli.application.conversation.claims import (
    factual_fallback,
    validate_completion_claims,
)
from aura_cli.application.execution import TurnExecution


def test_rejects_mutation_claim_without_tool() -> None:
    turn = TurnExecution(session_id="session")

    result = validate_completion_claims("Crie App.tsx", "Criei App.tsx.", turn)

    assert result.supported is False
    assert "Nenhuma operação" in factual_fallback(turn, result.issues)


def test_rejects_test_success_after_nonzero_exit() -> None:
    turn = TurnExecution(session_id="session")
    turn.plan_operation("call", "run_shell_command", {"command": "pytest tests"})
    turn.start_operation("call")
    turn.finish_operation("call", {"exit_code": 4, "stderr": "ImportError"}, 1.0)

    result = validate_completion_claims(
        "Rode os testes", "Todos os testes passaram.", turn
    )

    assert result.supported is False
    assert any("falha" in issue for issue in result.issues)


def test_accepts_test_success_with_exit_zero() -> None:
    turn = TurnExecution(session_id="session")
    turn.plan_operation("call", "run_shell_command", {"command": "pytest tests"})
    turn.start_operation("call")
    turn.finish_operation("call", {"exit_code": 0, "stdout": "3 passed"}, 1.0)

    result = validate_completion_claims(
        "Rode os testes", "Todos os testes passaram.", turn
    )

    assert result.supported is True


def test_detects_action_promise_without_progress() -> None:
    turn = TurnExecution(session_id="session")

    result = validate_completion_claims("Implemente a tela", "Vou iniciar agora.", turn)

    assert result.supported is False
    assert result.promises_action is True


def test_commit_claim_requires_repository_branch_and_head() -> None:
    turn = TurnExecution(session_id="session")
    turn.plan_operation("call", "git_commit", {"message": "baseline"})
    turn.start_operation("call")
    turn.finish_operation("call", "commit created", 0.1)

    result = validate_completion_claims("Crie um commit", "Commit criado.", turn)

    assert result.supported is False
