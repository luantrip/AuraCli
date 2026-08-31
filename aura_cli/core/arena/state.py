"""Serializable Arena domain objects."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Optional

from aura_cli.core.agents.strategy_deck import AgentCard


@dataclass
class AgentStanding:
    agent_id: str
    card: AgentCard
    solution: str = ""
    alive: bool = True
    attacks_survived: list[str] = field(default_factory=list)


@dataclass
class MatchResult:
    match_id: str
    round_number: int
    agent_a: str
    agent_b: str
    winner: Optional[str] = None
    scores: dict[str, dict[str, float]] = field(default_factory=dict)
    reason: str = ""


@dataclass
class ArenaState:
    run_id: str
    task: str
    seed: int
    phase: str = "spawn"
    round_number: int = 0
    agents: dict[str, AgentStanding] = field(default_factory=dict)
    matches: list[MatchResult] = field(default_factory=list)
    baseline: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
