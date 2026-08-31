"""Shared scoring rubric for arena judges."""

WEIGHTS = {
    "correctness": 0.30,
    "completeness": 0.25,
    "robustness": 0.20,
    "specificity": 0.15,
    "clarity": 0.10,
}


def weighted_score(scores: dict[str, float]) -> float:
    return sum(float(scores.get(name, 0.0)) * weight for name, weight in WEIGHTS.items())
