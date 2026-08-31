"""Deterministic token budgets for long-running conversational sessions."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class BudgetDecision(str, Enum):
    CONTINUE = "continue"
    COMPACT = "compact"
    STOP = "stop"


@dataclass(frozen=True)
class TokenBudget:
    context_soft_limit: int
    context_hard_limit: int
    session_soft_limit: int
    session_hard_limit: int

    def decide(self, *, context_tokens: int, session_tokens: int) -> BudgetDecision:
        if (
            context_tokens >= self.context_hard_limit
            or session_tokens >= self.session_hard_limit
        ):
            return BudgetDecision.STOP
        if (
            context_tokens >= self.context_soft_limit
            or session_tokens >= self.session_soft_limit
        ):
            return BudgetDecision.COMPACT
        return BudgetDecision.CONTINUE


__all__ = ["BudgetDecision", "TokenBudget"]
