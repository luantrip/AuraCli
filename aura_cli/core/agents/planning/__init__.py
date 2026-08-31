"""Agent planning package — task decomposition and execution.

Re-exports TaskPlanner, ProblemDecomposer, ExecutionEngine (sequential/parallel
modes), ParallelExecutor and TaskGroup. Supports depth-first, breadth-first and
other planning strategies.
"""

from aura_cli.core.agents.planning.execution_engine import (
    ExecutionEngine,
    ExecutionMode,
    ExecutionResult,
)
from aura_cli.core.agents.planning.parallel_executor import ParallelExecutor, TaskGroup
from aura_cli.core.agents.planning.problem_decomposer import (
    DecompositionStrategy,
    ProblemComponent,
    ProblemDecomposer,
)
from aura_cli.core.agents.planning.task_parameter_normalizer import (
    TaskParameterNormalizer,
    get_task_normalizer,
    normalize_task_params,
)
from aura_cli.core.agents.planning.task_planner import (
    PlanStrategy,
    TaskPlan,
    TaskPlanner,
)
from aura_cli.core.agents.planning.task_validator import (
    TaskValidator,
    ValidationResult,
    ValidationRule,
)

__all__ = [
    "DecompositionStrategy",
    "ExecutionEngine",
    "ExecutionMode",
    "ExecutionResult",
    "ParallelExecutor",
    "PlanStrategy",
    "ProblemComponent",
    "ProblemDecomposer",
    "TaskGroup",
    "TaskParameterNormalizer",
    "TaskPlan",
    "TaskPlanner",
    "TaskValidator",
    "ValidationResult",
    "ValidationRule",
    "get_task_normalizer",
    "normalize_task_params",
]
