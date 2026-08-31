"""
Task planner for agents.

Provides strategic planning for complex tasks,
decomposition into subtasks and dependency ordering.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List
import uuid

from aura_cli.core.agents.agent_base import AgentTask
from aura_cli.core.logger import get_logger

logger = get_logger(__name__)


class PlanStrategy(Enum):
    """Planning strategy enum."""

    SEQUENTIAL = "sequential"  # Sequential execution
    PARALLEL = "parallel"  # Parallel execution when possible
    DEPENDENCY_ORDER = "dependency_order"  # Ordered by dependencies
    PRIORITY_ORDER = "priority_order"  # Ordenado por prioridade


@dataclass
class TaskPlan:
    """A complete execution plan (steps, dependencies, metadata)."""

    plan_id: str
    description: str
    strategy: PlanStrategy
    tasks: List[AgentTask] = field(default_factory=list)
    estimated_duration: float = 0.0
    estimated_cost: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


class TaskPlanner:
    """Creates and optimises execution plans for complex tasks."""

    def __init__(self):
        """Initialise the task planner."""
        logger.info("TaskPlanner initialized")

    def create_plan(
        self,
        description: str,
        tasks: List[Dict[str, Any]],
        strategy: PlanStrategy = PlanStrategy.DEPENDENCY_ORDER,
    ) -> TaskPlan:
        """Create an execution plan for a goal description."""
        plan_id = str(uuid.uuid4())[:8]

        agent_tasks = []
        for task_data in tasks:
            task = AgentTask(
                id=task_data.get("id", str(uuid.uuid4())[:8]),
                description=task_data.get("description", ""),
                priority=task_data.get("priority", 5),
                dependencies=task_data.get("dependencies", []),
                parameters=task_data.get("parameters", {}),
            )
            agent_tasks.append(task)

        ordered_tasks = self._order_tasks(agent_tasks, strategy)

        estimated_duration = self._estimate_duration(ordered_tasks)
        estimated_cost = self._estimate_cost(ordered_tasks)

        plan = TaskPlan(
            plan_id=plan_id,
            description=description,
            strategy=strategy,
            tasks=ordered_tasks,
            estimated_duration=estimated_duration,
            estimated_cost=estimated_cost,
        )

        logger.info(
            f"Plan {plan_id} created: {len(ordered_tasks)} tasks, "
            f"duração estimada: {estimated_duration:.1f}s"
        )

        return plan

    def _order_tasks(
        self, tasks: List[AgentTask], strategy: PlanStrategy
    ) -> List[AgentTask]:
        """Order tasks according to the given strategy."""
        if strategy == PlanStrategy.PRIORITY_ORDER:
            return sorted(tasks, key=lambda t: t.priority, reverse=True)

        elif strategy == PlanStrategy.DEPENDENCY_ORDER:
            return self._topological_sort(tasks)

        elif strategy == PlanStrategy.PARALLEL:
            return self._group_parallel_tasks(tasks)

        else:
            return tasks

    def _topological_sort(self, tasks: List[AgentTask]) -> List[AgentTask]:
        """Sort tasks by dependencies (topological sort)."""
        {task.id: task for task in tasks}

        in_degree = {task.id: len(task.dependencies) for task in tasks}

        queue = [task for task in tasks if in_degree[task.id] == 0]
        result = []

        while queue:
            current = queue.pop(0)
            result.append(current)

            for task in tasks:
                if current.id in task.dependencies:
                    in_degree[task.id] -= 1
                    if in_degree[task.id] == 0:
                        queue.append(task)

        if len(result) != len(tasks):
            logger.warning(
                "Ciclo detectado nas dependências ou tarefa órfã. "
                "Algumas tarefas podem não ser executadas."
            )
            remaining = [t for t in tasks if t not in result]
            result.extend(remaining)

        return result

    def _group_parallel_tasks(self, tasks: List[AgentTask]) -> List[AgentTask]:
        """Group tasks that can run in parallel."""
        return self._topological_sort(tasks)

    def _estimate_duration(self, tasks: List[AgentTask]) -> float:
        """Estimate total plan duration."""
        base_duration = 5.0

        total = 0.0
        for task in tasks:
            multiplier = 1.0 + (task.priority / 10.0)
            total += base_duration * multiplier

        return total

    def _estimate_cost(self, tasks: List[AgentTask]) -> float:
        """Estimate total plan cost (tokens, etc.)."""
        base_cost = 100.0

        total = 0.0
        for task in tasks:
            complexity = len(str(task.parameters))
            total += base_cost + (complexity * 10)

        return total

    def optimize_plan(self, plan: TaskPlan) -> TaskPlan:
        """
        Otimiza um plano existente.

        Args:
            plan: Plano a otimizar

        Returns:
            Plano otimizado
        """
        optimized_tasks = self._topological_sort(plan.tasks)

        plan.estimated_duration = self._estimate_duration(optimized_tasks)
        plan.estimated_cost = self._estimate_cost(optimized_tasks)
        plan.tasks = optimized_tasks

        logger.info(f"Plano {plan.plan_id} otimizado")

        return plan
