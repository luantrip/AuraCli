"""Background Arena tournament worker."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Optional

from aura_cli.application.artifacts import ArtifactLayout
from aura_cli.cli.workers.base_worker import BaseWorker
from aura_cli.core.agents.subagent_runner import run_subagent
from aura_cli.core.arena.engine import ArenaEngine
from aura_cli.core.arena.judge import ArenaJudge
from aura_cli.core.arena.templates import COMPETITOR_TEMPLATE
from aura_cli.core.evaluation.models import Candidate, Score
from aura_cli.core.evaluation.reporting import save_report
from aura_cli.core.evaluation.selection import select_best


class ArenaWorker(BaseWorker):
    def __init__(self, task: str, project_root: Path, agents: int = 4, seed: int = 0,
                 executor: Optional[Callable[..., str]] = None, **kwargs: Any) -> None:
        super().__init__(task_id="arena", **kwargs)
        self.task = task
        self.project_root = Path(project_root)
        self.agent_count = agents
        self.seed = seed
        self.executor = executor or run_subagent

    def _run_impl(self) -> None:
        engine = ArenaEngine(ArtifactLayout(project_root=self.project_root).project("arena"))
        state = engine.init(self.agent_count, self.seed, self.task)
        self._throttled_status_update(f"› [Arena] Spawned {len(state.agents)} competitors")
        for agent in state.agents.values():
            prompt = COMPETITOR_TEMPLATE.format(task=self.task, card=agent.card.short_label())
            engine.record_solution(agent.agent_id, self.executor(prompt, strategy_card=agent.card))
        judge = ArenaJudge()
        while len([agent for agent in state.agents.values() if agent.alive]) > 1:
            for agent_a, agent_b in engine.pairings():
                result = judge.judge(self.task, agent_a, state.agents[agent_a].solution,
                                     agent_b, state.agents[agent_b].solution)
                engine.record_match(agent_a, agent_b, result.winner, result.scores, result.reason)
            state = engine.state or state
        winner = engine.winner()
        candidates = []
        for agent in state.agents.values():
            scores = next(
                (match.scores.get(agent.agent_id, {}) for match in state.matches
                 if agent.agent_id in (match.agent_a, match.agent_b)),
                {},
            )
            candidates.append(
                Candidate(
                    agent.agent_id,
                    agent.solution,
                    Score(**scores),
                    {"strategy_card": agent.card.to_dict()},
                )
            )
        report = select_best(candidates)
        save_report(report, engine.arena_dir / "evaluation.json", title="Arena Evaluation")
        self._publish_terminal_result({"status": "success", "task_id": self.task_id,
                                       "winner": winner.agent_id if winner else None,
                                       "solution": winner.solution if winner else "",
                                       "evaluation_report": str(engine.arena_dir / "evaluation.json")})
