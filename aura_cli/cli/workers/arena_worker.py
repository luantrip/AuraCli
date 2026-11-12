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
    dashboard_prefix = "Aura Arena"

    def __init__(self, task: str, project_root: Path, agents: int = 4, seed: int = 0,
                 executor: Optional[Callable[..., str]] = None,
                 use_llm_judge: bool = False, model: str = "", **kwargs: Any) -> None:
        super().__init__(task_id="arena", **kwargs)
        self.task = task
        self.project_root = Path(project_root)
        self.agent_count = agents
        self.seed = seed
        self.executor = executor or run_subagent
        self.use_llm_judge = use_llm_judge
        self.model = model
        # Wire the lifecycle adapter so progress and the winner surface through
        # the same event bus consumed by the chat loop (parity with AGI/Ops).
        from aura_cli.application.agents.event_emitter import AgiEventAdapter

        self.agi_event_adapter = AgiEventAdapter(self.status_queue, self.task_id)

    def _build_judge(self) -> ArenaJudge:
        """Return the configured judge.

        Default is the deterministic rubric/heuristic judge. When
        ``use_llm_judge`` is set, an LLM evaluator is injected: it receives the
        judge prompt and returns the raw model response, which ``ArenaJudge``
        parses as JSON. If the evaluator fails, ``ArenaJudge`` raises and the
        run surfaces the error rather than silently faking a verdict.
        """
        if not self.use_llm_judge:
            return ArenaJudge()

        def _llm_evaluator(prompt: str) -> str:
            # Reuse the subagent runner as a lightweight single-shot LLM caller.
            return self.executor(prompt, model=self.model)

        return ArenaJudge(evaluator=_llm_evaluator)

    def _run_impl(self) -> None:
        self.agi_event_adapter.start_task(
            description="Arena tournament", objective=self.task
        )
        engine = ArenaEngine(ArtifactLayout(project_root=self.project_root).project("arena"))

        # Resume an interrupted run for the same task when a saved state exists;
        # otherwise start a fresh bracket.
        resumed = False
        if engine.state_path.exists():
            try:
                state = engine.resume()
                if state.task == self.task and state.phase != "done":
                    resumed = True
                    self._throttled_status_update(
                        f"› [Arena] Retomando disputa (rodada {state.round_number}, "
                        f"{len([a for a in state.agents.values() if a.alive])} vivos)"
                    )
                else:
                    state = engine.init(self.agent_count, self.seed, self.task)
            except (OSError, ValueError, KeyError):
                state = engine.init(self.agent_count, self.seed, self.task)
        else:
            state = engine.init(self.agent_count, self.seed, self.task)

        if not resumed:
            self._throttled_status_update(
                f"› [Arena] {len(state.agents)} competidores na disputa"
            )

        # Generate solutions only for agents that don't have one yet (resume-safe).
        for agent in state.agents.values():
            if agent.solution:
                continue
            prompt = COMPETITOR_TEMPLATE.format(task=self.task, card=agent.card.short_label())
            engine.record_solution(agent.agent_id, self.executor(prompt, strategy_card=agent.card))
        judge = self._build_judge()
        round_num = state.round_number
        while len([agent for agent in state.agents.values() if agent.alive]) > 1:
            round_num += 1
            alive = len([a for a in state.agents.values() if a.alive])
            self._throttled_status_update(
                f"› [Arena] Rodada {round_num}: {alive} competidores restantes"
            )
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
                    Score.from_mapping(scores),
                    {"strategy_card": agent.card.to_dict()},
                )
            )
        report = select_best(candidates)
        report_path = engine.arena_dir / "evaluation.json"
        save_report(report, report_path, title="Arena Evaluation")

        winner_id = winner.agent_id if winner else None
        if winner_id:
            summary = (
                f"🏆 Arena complete — winner: {winner_id}\n"
                f"Report: {report_path}"
            )
        else:
            summary = "Arena complete with no defined winner."
        self.agi_event_adapter.complete_task(
            success=winner is not None,
            result=summary,
        )
        self._publish_terminal_result({"status": "success", "task_id": self.task_id,
                                       "winner": winner_id,
                                       "solution": winner.solution if winner else "",
                                       "evaluation_report": str(report_path)})
