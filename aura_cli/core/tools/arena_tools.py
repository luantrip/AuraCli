"""Read-only tools for inspecting the latest Arena run."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from aura_cli.application.artifacts import ArtifactLayout
from aura_cli.core.arena.engine import ArenaEngine


def _engine(project_root: Optional[Path] = None) -> ArenaEngine:
    return ArenaEngine(ArtifactLayout(project_root=project_root).project("arena"))


def arena_status(project_root: Optional[Path] = None) -> dict:
    engine = _engine(project_root)
    state = engine.resume()
    return {"run_id": state.run_id, "phase": state.phase, "round": state.round_number,
            "alive": [key for key, agent in state.agents.items() if agent.alive],
            "agents": len(state.agents), "matches": len(state.matches)}


def arena_winner(project_root: Optional[Path] = None) -> dict:
    winner = _engine(project_root).resume()
    agent = next((item for item in winner.agents.values() if item.alive), None)
    if not agent:
        return {}
    return {"agent_id": agent.agent_id, "solution": agent.solution, "card": agent.card.to_dict()}


def arena_card(agent_id: str, project_root: Optional[Path] = None) -> dict:
    agent = _engine(project_root).resume().agents.get(agent_id)
    if not agent:
        raise KeyError(agent_id)
    return agent.card.to_dict()
