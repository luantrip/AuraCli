"""Quality and diversity metrics for agent outputs."""

from __future__ import annotations

import re
from typing import Iterable

from aura_cli.core.evaluation.models import Candidate


def _tokens(text: str) -> set[str]:
    return set(re.findall(r"[a-zA-Z0-9_]+", text.lower()))


def diversity_score(outputs: Iterable[str]) -> float:
    """Return mean pairwise Jaccard distance in the range 0..1."""
    token_sets = [_tokens(output) for output in outputs]
    if len(token_sets) < 2:
        return 0.0
    distances: list[float] = []
    for index, left in enumerate(token_sets):
        for right in token_sets[index + 1 :]:
            union = left | right
            distances.append(1.0 - (len(left & right) / len(union) if union else 1.0))
    return sum(distances) / len(distances)


def quality_summary(candidates: Iterable[Candidate]) -> dict[str, float]:
    """Summarise score distribution without depending on a model provider."""
    items = list(candidates)
    if not items:
        return {"count": 0.0, "mean": 0.0, "max": 0.0, "min": 0.0}
    totals = [candidate.total_score for candidate in items]
    return {
        "count": float(len(totals)),
        "mean": sum(totals) / len(totals),
        "max": max(totals),
        "min": min(totals),
    }
