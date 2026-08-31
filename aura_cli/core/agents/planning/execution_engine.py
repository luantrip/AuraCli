"""Execution engine for task plans.

Provides controlled plan execution with sequential, parallel and hybrid modes.
"""

from dataclasses import dataclass, field
from enum import Enum
import threading
import time
from typing import Any, Dict, List, Optional

from aura_cli.core.agents.agent_base import AgentTask
from aura_cli.core.agents.planning.task_planner import TaskPlan
from aura_cli.core.logger import get_logger
from aura_cli.core.stats import get_stats

logger = get_logger(__name__)


class ExecutionMode(Enum):
    """Execution mode enum (sequential, parallel, hybrid)."""

    SEQUENTIAL = "sequential"  # Sequential execution
    PARALLEL = "parallel"  # Parallel execution
    HYBRID = "hybrid"  # Hybrid (parallel when possible)


@dataclass
class ExecutionResult:
    """Result of a plan execution step."""

    task_id: str
    success: bool
    result: Any = None
    duration: float = 0.0
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class ExecutionEngine:
    """Plan execution engine."""

    def __init__(self, orchestrator: Any, mode: ExecutionMode = ExecutionMode.HYBRID):
        """Initialise the execution engine."""
        self.orchestrator = orchestrator
        self.mode = mode
        self.stats = get_stats()

        self.lock = threading.Lock()
        self.results: Dict[str, ExecutionResult] = {}

        logger.info(f"ExecutionEngine initialized (mode: {mode.value})")

    def execute_plan(
        self, plan: TaskPlan, max_iterations: int = 1000
    ) -> Dict[str, Any]:
        """Execute a full plan and return all results."""
        logger.info(
            f"Executando plano {plan.plan_id} "
            f"({len(plan.tasks)} tarefas, modo: {self.mode.value})"
        )

        self.results.clear()

        if self.mode == ExecutionMode.SEQUENTIAL:
            return self._execute_sequential(plan, max_iterations)
        elif self.mode == ExecutionMode.PARALLEL:
            return self._execute_parallel(plan, max_iterations)
        else:
            return self._execute_hybrid(plan, max_iterations)

    def _execute_sequential(
        self, plan: TaskPlan, max_iterations: int
    ) -> Dict[str, Any]:
        """Execute a plan sequentially."""
        completed = 0
        failed = 0

        for task in plan.tasks:
            if completed + failed >= max_iterations:
                break

            result = self._execute_task(task)
            self.results[task.id] = result

            if result.success:
                completed += 1
            else:
                failed += 1
                if task.priority >= 8:
                    logger.error(
                        f"Tarefa crítica {task.id} falhou, interrompendo execução"
                    )
                    break

        return {
            "plan_id": plan.plan_id,
            "completed": completed,
            "failed": failed,
            "total": len(plan.tasks),
            "results": {
                tid: self._result_to_dict(r) for tid, r in self.results.items()
            },
        }

    def _execute_parallel(self, plan: TaskPlan, max_iterations: int) -> Dict[str, Any]:
        """Execute a plan in parallel."""
        task_groups = self._group_by_dependency_level(plan.tasks)

        completed = 0
        failed = 0

        for group in task_groups:
            if completed + failed >= max_iterations:
                break

            threads = []
            for task in group:
                # Use daemon threads for short-lived parallel execution
                # These threads are immediately joined, so daemon is safe
                thread = threading.Thread(
                    target=self._execute_task_thread,
                    args=(task,),
                    daemon=True,
                )
                thread.start()
                threads.append(thread)

            for thread in threads:
                thread.join()

            for task in group:
                if task.id in self.results:
                    result = self.results[task.id]
                    if result.success:
                        completed += 1
                    else:
                        failed += 1

        return {
            "plan_id": plan.plan_id,
            "completed": completed,
            "failed": failed,
            "total": len(plan.tasks),
            "results": {
                tid: self._result_to_dict(r) for tid, r in self.results.items()
            },
        }

    def _execute_hybrid(self, plan: TaskPlan, max_iterations: int) -> Dict[str, Any]:
        """Execute a plan in hybrid mode."""
        task_groups = self._group_by_dependency_level(plan.tasks)

        completed = 0
        failed = 0

        for group in task_groups:
            if completed + failed >= max_iterations:
                break

            if len(group) > 1:
                threads = []
                for task in group:
                    # Use daemon threads for short-lived parallel execution
                    # These threads are immediately joined, so daemon is safe
                    thread = threading.Thread(
                        target=self._execute_task_thread,
                        args=(task,),
                        daemon=True,
                    )
                    thread.start()
                    threads.append(thread)

                for thread in threads:
                    thread.join()
            else:
                result = self._execute_task(group[0])
                self.results[group[0].id] = result

            for task in group:
                if task.id in self.results:
                    result = self.results[task.id]
                    if result.success:
                        completed += 1
                    else:
                        failed += 1

        return {
            "plan_id": plan.plan_id,
            "completed": completed,
            "failed": failed,
            "total": len(plan.tasks),
            "results": {
                tid: self._result_to_dict(r) for tid, r in self.results.items()
            },
        }

    def _execute_task(self, task: AgentTask) -> ExecutionResult:
        """Execute a single plan task."""
        start_time = time.time()

        try:
            agent_id = task.parameters.get("agent_id")
            if agent_id:
                agent = self.orchestrator.get_agent(agent_id)
            else:
                agents = list(self.orchestrator.agents.values())
                if not agents:
                    raise ValueError("Nenhum agente disponível")
                agent = agents[0]

            result_value = agent._execute_task(task)

            duration = time.time() - start_time

            result = ExecutionResult(
                task_id=task.id, success=True, result=result_value, duration=duration
            )

            self.stats.track_tool_usage("execution_engine_execute")

            logger.info(f"Task {task.id} executed successfully ({duration:.2f}s)")

            return result

        except Exception as e:
            duration = time.time() - start_time
            error_msg = str(e)

            result = ExecutionResult(
                task_id=task.id, success=False, duration=duration, error=error_msg
            )

            logger.error(f"Task {task.id} failed: {error_msg}", exc_info=True)

            return result

    def _execute_task_thread(self, task: AgentTask) -> None:
        """Execute a task in a separate thread."""
        result = self._execute_task(task)
        with self.lock:
            self.results[task.id] = result

    def _group_by_dependency_level(
        self, tasks: List[AgentTask]
    ) -> List[List[AgentTask]]:
        """Group tasks by dependency level."""
        groups = []
        remaining = tasks.copy()
        completed_ids: set[str] = set()

        while remaining:
            ready = [
                t
                for t in remaining
                if all(dep in completed_ids for dep in t.dependencies)
            ]

            if not ready:
                if remaining:
                    groups.append(remaining)
                break

            groups.append(ready)
            completed_ids.update(t.id for t in ready)
            remaining = [t for t in remaining if t not in ready]

        return groups

    def _result_to_dict(self, result: ExecutionResult) -> Dict[str, Any]:
        """Convert an execution result to a dict."""
        return {
            "task_id": result.task_id,
            "success": result.success,
            "duration": result.duration,
            "error": result.error,
            "result_preview": str(result.result)[:200] if result.result else None,
        }

    def get_results(self) -> Dict[str, ExecutionResult]:
        """Return all execution results."""
        return self.results.copy()
