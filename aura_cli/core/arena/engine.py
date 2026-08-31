"""Resumable single-elimination bracket state machine."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional
import uuid

from aura_cli.core.agents.strategy_deck import StrategyDeck

from .state import AgentStanding, ArenaState, MatchResult


class ArenaEngine:
    def __init__(self, arena_dir: Path, deck: Optional[StrategyDeck] = None) -> None:
        self.arena_dir = Path(arena_dir)
        self.state_path = self.arena_dir / "arena.json"
        self.deck = deck or StrategyDeck()
        self.state: Optional[ArenaState] = None

    def init(self, n_agents: int, seed: int, task: str, baseline: Optional[str] = None) -> ArenaState:
        if n_agents < 2:
            raise ValueError("n_agents must be at least 2")
        cards = self.deck.draw(n_agents, seed=seed)
        run_id = uuid.uuid4().hex[:12]
        self.state = ArenaState(run_id=run_id, task=task, seed=seed, baseline=baseline)
        self.state.agents = {f"a{index + 1:03d}": AgentStanding(f"a{index + 1:03d}", card)
                             for index, card in enumerate(cards)}
        self._persist()
        return self.state

    def resume(self) -> ArenaState:
        payload = json.loads(self.state_path.read_text(encoding="utf-8"))
        self.state = ArenaState(run_id=payload["run_id"], task=payload["task"], seed=payload["seed"],
                                phase=payload.get("phase", "spawn"), round_number=payload.get("round_number", 0),
                                baseline=payload.get("baseline"))
        self.state.agents = {key: AgentStanding(key, __import__("aura_cli.core.agents.strategy_deck", fromlist=["AgentCard"]).AgentCard.from_dict(value["card"]),
                             value.get("solution", ""), value.get("alive", True), value.get("attacks_survived", []))
                             for key, value in payload.get("agents", {}).items()}
        self.state.matches = [MatchResult(**item) for item in payload.get("matches", [])]
        return self.state

    def record_solution(self, agent_id: str, solution: str) -> None:
        state = self._require_state()
        state.agents[agent_id].solution = solution
        self._persist()

    def pairings(self) -> list[tuple[str, str]]:
        alive = [agent_id for agent_id, agent in self._require_state().agents.items() if agent.alive]
        return list(zip(alive[::2], alive[1::2], strict=False))

    def record_match(self, agent_a: str, agent_b: str, winner: str,
                     scores: Optional[dict[str, dict[str, float]]] = None, reason: str = "") -> MatchResult:
        state = self._require_state()
        if winner not in (agent_a, agent_b):
            raise ValueError("winner must be one of the match participants")
        state.round_number += 1
        result = MatchResult(f"m{len(state.matches) + 1:04d}", state.round_number, agent_a, agent_b, winner, scores or {}, reason)
        state.matches.append(result)
        state.agents[agent_a].alive = agent_a == winner
        state.agents[agent_b].alive = agent_b == winner
        state.phase = "done" if len([a for a in state.agents.values() if a.alive]) == 1 else "judge"
        self._persist()
        return result

    def winner(self) -> Optional[AgentStanding]:
        return next((agent for agent in self._require_state().agents.values() if agent.alive), None)

    def status(self) -> dict:
        state = self._require_state()
        return {"run_id": state.run_id, "task": state.task, "phase": state.phase,
                "round": state.round_number, "agents": len(state.agents),
                "alive": [key for key, value in state.agents.items() if value.alive],
                "matches": len(state.matches)}

    def _require_state(self) -> ArenaState:
        if self.state is None:
            raise RuntimeError("arena is not initialized")
        return self.state

    def _persist(self) -> None:
        self.arena_dir.mkdir(parents=True, exist_ok=True)
        self.state_path.write_text(json.dumps(self._require_state().to_dict(), indent=2), encoding="utf-8")
