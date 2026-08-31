"""Scoring and tie-breaking for Arena matches."""

from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Callable, Optional

from .rubric import WEIGHTS, weighted_score


@dataclass(frozen=True)
class Judgment:
    winner: str
    scores: dict[str, dict[str, float]]
    reason: str
    fatal: tuple[str, ...] = ()

    def to_dict(self) -> dict:
        return {"winner": self.winner, "scores": self.scores, "reason": self.reason, "fatal": list(self.fatal)}


class ArenaJudge:
    def __init__(self, evaluator: Optional[Callable[[str], str]] = None) -> None:
        self.evaluator = evaluator

    def judge(self, task: str, agent_a: str, solution_a: str, agent_b: str, solution_b: str) -> Judgment:
        if self.evaluator:
            return self._parse(self.evaluator(self.prompt(task, agent_a, solution_a, agent_b, solution_b)), agent_a, agent_b)
        scores = {agent_a: self._baseline_score(solution_a), agent_b: self._baseline_score(solution_b)}
        winner = agent_a if weighted_score(scores[agent_a]) >= weighted_score(scores[agent_b]) else agent_b
        return Judgment(winner, scores, "Selected by rubric score.")

    @staticmethod
    def prompt(task: str, agent_a: str, solution_a: str, agent_b: str, solution_b: str) -> str:
        return (f"Score solutions for task: {task}\n{agent_a}: {solution_a}\n"
                f"{agent_b}: {solution_b}\nReturn JSON: winner, scores, reason.")

    @staticmethod
    def _parse(raw: str, agent_a: str, agent_b: str) -> Judgment:
        try:
            data = json.loads(raw)
            scores = data["scores"]
            winner = data.get("winner")
            if winner not in (agent_a, agent_b):
                raise ValueError("invalid winner")
            return Judgment(winner, scores, str(data.get("reason", "")), tuple(data.get("fatal", [])))
        except (ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
            raise ValueError(f"invalid arena judgment: {exc}") from exc

    @staticmethod
    def _baseline_score(solution: str) -> dict[str, float]:
        length = len(solution.strip())
        quality = min(10.0, max(1.0, length / 400.0 + (2.0 if "\n" in solution else 0.0)))
        return dict.fromkeys(WEIGHTS, quality)
