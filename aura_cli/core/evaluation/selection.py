"""Deterministic candidate selection and anonymised review pools."""

from __future__ import annotations

import hashlib
from typing import Iterable, Mapping

from aura_cli.core.evaluation.metrics import diversity_score
from aura_cli.core.evaluation.models import Candidate, EvaluationReport

DEFAULT_WEIGHTS = {
    "correctness": 0.30,
    "completeness": 0.25,
    "robustness": 0.20,
    "specificity": 0.15,
    "clarity": 0.10,
}


def anonymous_id(candidate_id: str) -> str:
    """Create a stable opaque identifier for blind evaluation."""
    return "candidate-" + hashlib.sha256(candidate_id.encode("utf-8")).hexdigest()[:10]


def select_best(
    candidates: Iterable[Candidate],
    *,
    weights: Mapping[str, float] | None = None,
    baseline_id: str | None = None,
) -> EvaluationReport:
    """Select the highest weighted candidate with stable tie breaking."""
    items = list(candidates)
    active_weights = dict(weights or DEFAULT_WEIGHTS)
    ranked = sorted(
        items,
        key=lambda item: (item.score.weighted(active_weights), item.candidate_id),
        reverse=True,
    )
    winner = ranked[0] if ranked else None
    notes: list[str] = []
    if baseline_id and any(item.candidate_id == baseline_id for item in items):
        notes.append(f"baseline_present:{baseline_id}")
    return EvaluationReport(
        winner_id=winner.candidate_id if winner else None,
        candidates=items,
        criteria_weights=active_weights,
        diversity=diversity_score(item.output for item in items),
        notes=notes,
    )


def blind_pool(candidates: Iterable[Candidate]) -> list[dict]:
    """Return candidates without revealing their original IDs to a judge."""
    return [
        {"id": anonymous_id(item.candidate_id), "output": item.output, "score": item.score.to_dict()}
        for item in candidates
    ]
