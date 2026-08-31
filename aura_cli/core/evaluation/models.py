"""Serializable contracts for agent evaluation runs."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Mapping


@dataclass(frozen=True)
class Score:
    """Weighted quality dimensions for one candidate."""

    correctness: float = 0.0
    completeness: float = 0.0
    robustness: float = 0.0
    specificity: float = 0.0
    clarity: float = 0.0

    def weighted(self, weights: Mapping[str, float] | None = None) -> float:
        values = asdict(self)
        active = weights or dict.fromkeys(values, 1.0)
        total = sum(float(active.get(name, 0.0)) for name in values)
        if total <= 0:
            return 0.0
        return sum(values[name] * float(active.get(name, 0.0)) for name in values) / total

    def to_dict(self) -> dict[str, float]:
        return asdict(self)


@dataclass
class Candidate:
    """An agent output and its evaluation metadata."""

    candidate_id: str
    output: str
    score: Score = field(default_factory=Score)
    metadata: dict[str, Any] = field(default_factory=dict)
    baseline: bool = False

    @property
    def total_score(self) -> float:
        return self.score.weighted()

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["score"] = self.score.to_dict()
        return payload


@dataclass
class EvaluationReport:
    """Persistable result of comparing a candidate pool."""

    winner_id: str | None
    candidates: list[Candidate]
    criteria_weights: dict[str, float] = field(default_factory=dict)
    diversity: float = 0.0
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "winner_id": self.winner_id,
            "candidates": [candidate.to_dict() for candidate in self.candidates],
            "criteria_weights": dict(self.criteria_weights),
            "diversity": self.diversity,
            "notes": list(self.notes),
        }
