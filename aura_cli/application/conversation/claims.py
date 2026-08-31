"""Validate model completion claims against the canonical turn ledger."""

from __future__ import annotations

from dataclasses import dataclass
import re

from aura_cli.application.execution import (
    OperationRecord,
    OperationStatus,
    TurnExecution,
)

_ACTION_REQUEST = re.compile(
    r"\b(cri(?:e|ar)|edite|altere|corrija|implemente|execute|rode|instale|"
    r"inicialize|commit|faça|faca|build|create|edit|fix|implement|run|install)\b",
    re.IGNORECASE,
)
_SUCCESS_CLAIM = re.compile(
    r"\b(conclu[ií]d[oa]|feito|pronto|sucesso|criei|editei|corrigi|implementei|"
    r"executei|instalei|passed|passaram|completed|created|fixed|implemented)\b",
    re.IGNORECASE,
)
_TEST_SUCCESS = re.compile(
    r"(?:todos?\s+os\s+)?testes?\s+(?:pass(?:ou|aram)|aprovad[oa]s?)|"
    r"tests?\s+(?:passed|pass)",
    re.IGNORECASE,
)
_FILE_SUCCESS = re.compile(r"\b(?:arquivo\s+)?(?:criad[oa]|created)\b", re.IGNORECASE)
_COMMIT_SUCCESS = re.compile(r"\bcommit\s+(?:criad[oa]|feito|created)\b", re.IGNORECASE)
_PROMISE = re.compile(
    r"\b(vou|irei|começarei|iniciarei|agora vou|i will|i'll|going to)\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class ClaimValidation:
    supported: bool
    issues: tuple[str, ...] = ()
    promises_action: bool = False


def request_requires_execution(request: str) -> bool:
    return bool(_ACTION_REQUEST.search(request))


def validate_completion_claims(
    request: str, response: str, turn: TurnExecution
) -> ClaimValidation:
    """Return unsupported factual claims and continuation-relevant promises."""
    issues: list[str] = []
    successful = [
        item for item in turn.operations if item.status is OperationStatus.SUCCEEDED
    ]
    failed = [item for item in turn.operations if item.status is OperationStatus.FAILED]
    requires_execution = request_requires_execution(request)

    if requires_execution and not turn.operations:
        issues.append("o pedido exige execução, mas nenhuma ferramenta foi chamada")
    if _SUCCESS_CLAIM.search(response) and failed:
        issues.append("há operações com falha no ledger")
    if _TEST_SUCCESS.search(response) and not _has_successful_test(successful):
        issues.append("não há execução de testes aprovada")
    if _FILE_SUCCESS.search(response) and not _has_existing_write(successful):
        issues.append("no created and existing file as post-condition")
    if _COMMIT_SUCCESS.search(response) and not _has_successful_commit(successful):
        issues.append("não há commit Git comprovado")

    promises_action = requires_execution and bool(_PROMISE.search(response))
    if promises_action:
        issues.append(
            "a resposta promete ação futura em vez de concluí-la ou executá-la"
        )

    return ClaimValidation(
        supported=not issues,
        issues=tuple(dict.fromkeys(issues)),
        promises_action=promises_action,
    )


def factual_fallback(turn: TurnExecution, issues: tuple[str, ...]) -> str:
    """Build a minimal response that cannot overstate the recorded execution."""
    failures = [
        item for item in turn.operations if item.status is OperationStatus.FAILED
    ]
    if failures:
        latest = failures[-1]
        detail = latest.result_summary or "falha sem detalhe"
        return f"A execução não foi concluída: {latest.label} falhou — {detail}"
    if not turn.operations:
        return "Nenhuma operação foi executada; não posso confirmar a ação solicitada."
    return "Não posso confirmar a conclusão: " + "; ".join(issues)


def repair_instruction(turn: TurnExecution, issues: tuple[str, ...]) -> str:
    facts = [
        f"{item.label}={item.status.value}: {item.result_summary or 'sem resultado'}"
        for item in turn.operations
    ]
    return (
        "A resposta proposta contém alegações sem evidência. Continue usando "
        "ferramentas se ainda puder concluir; caso contrário, responda apenas com "
        "os fatos e a falha/bloqueio. Problemas: "
        + "; ".join(issues)
        + ". Ledger: "
        + (" | ".join(facts) if facts else "nenhuma operação")
    )


def _has_successful_test(operations: list[OperationRecord]) -> bool:
    return any(
        item.category == "shell"
        and item.target
        and re.search(r"\b(pytest|unittest|npm\s+test|cargo\s+test)\b", item.target)
        and item.evidence.exit_code == 0
        for item in operations
    )


def _has_existing_write(operations: list[OperationRecord]) -> bool:
    return any(item.evidence.existing_paths for item in operations)


def _has_successful_commit(operations: list[OperationRecord]) -> bool:
    return any(
        item.status is OperationStatus.SUCCEEDED
        and item.evidence.repository is not None
        and item.evidence.branch is not None
        and item.evidence.commit is not None
        for item in operations
    )


__all__ = [
    "ClaimValidation",
    "factual_fallback",
    "repair_instruction",
    "request_requires_execution",
    "validate_completion_claims",
]
