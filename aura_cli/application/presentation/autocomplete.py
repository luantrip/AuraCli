"""Neutral fuzzy matching for command and argument suggestions."""

from difflib import SequenceMatcher
from typing import Iterable


class FuzzyMatcher:
    """Score and rank text candidates with prefix-aware fuzzy matching."""

    @staticmethod
    def similarity(a: str, b: str) -> float:
        left, right = a.casefold(), b.casefold()
        if left == right:
            return 1.0
        if right.startswith(left):
            return 0.95 + (len(left) / len(right)) * 0.05
        score = SequenceMatcher(None, left, right).ratio()
        return max(score, 0.7) if left in right else score

    @staticmethod
    def fuzzy_match(
        query: str, candidates: Iterable[str], min_score: float = 0.3
    ) -> list[tuple[str, float]]:
        normalized = query.casefold()
        results: list[tuple[str, float]] = []
        for candidate in candidates:
            comparable = candidate.casefold()
            if comparable.startswith(normalized):
                score = 1.0 + len(query) / len(candidate)
            elif normalized in comparable:
                score = 0.8 + len(query) / len(candidate) * 0.2
            else:
                score = SequenceMatcher(None, normalized, comparable).ratio()
            if score >= min_score:
                results.append((candidate, score))
        return sorted(results, key=lambda item: item[1], reverse=True)
