"""Problem decomposer for agents.

Decomposes complex problems into smaller, manageable components.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List

from aura_cli.core.agents.agent_base import AgentTask
from aura_cli.core.logger import get_logger

logger = get_logger(__name__)


class DecompositionStrategy(Enum):
    """Decomposition strategy enum."""

    HIERARCHICAL = "hierarchical"  # Hierarchical decomposition
    FUNCTIONAL = "functional"  # Por funcionalidade
    SEQUENTIAL = "sequential"  # By logical sequence
    PARALLEL = "parallel"  # Por paralelismo


@dataclass
class ProblemComponent:
    """A single component of a decomposed problem."""

    id: str
    description: str
    complexity: int = 5
    dependencies: List[str] = field(default_factory=list)
    estimated_effort: float = 1.0
    subtasks: List[AgentTask] = field(default_factory=list)


class ProblemDecomposer:
    """Decomposes complex problems into executable sub-tasks."""

    def __init__(self):
        """Initialise the problem decomposer."""
        logger.info("ProblemDecomposer initialized")

    def decompose(
        self,
        problem_description: str,
        strategy: DecompositionStrategy = DecompositionStrategy.HIERARCHICAL,
        max_depth: int = 3,
    ) -> List[ProblemComponent]:
        """Decompose a problem into components."""
        logger.info(f"Decompondo problema: {problem_description[:50]}...")

        if strategy == DecompositionStrategy.HIERARCHICAL:
            return self._hierarchical_decompose(problem_description, max_depth)
        elif strategy == DecompositionStrategy.FUNCTIONAL:
            return self._functional_decompose(problem_description)
        elif strategy == DecompositionStrategy.SEQUENTIAL:
            return self._sequential_decompose(problem_description)
        else:  # PARALLEL
            return self._parallel_decompose(problem_description)

    def _hierarchical_decompose(
        self, problem: str, max_depth: int
    ) -> List[ProblemComponent]:
        """Hierarchical domain decomposition."""
        components = []

        keywords = {
            "criar": ["design", "implementar", "testar"],
            "refatorar": ["analisar", "modificar", "validar"],
            "corrigir": ["identificar", "corrigir", "testar"],
            "otimizar": ["medir", "analisar", "otimizar", "validar"],
        }

        problem_lower = problem.lower()
        problem_type = None
        for key in keywords:
            if key in problem_lower:
                problem_type = key
                break

        if not problem_type:
            steps = ["analisar", "planejar", "executar", "validar"]
        else:
            steps = keywords[problem_type]

        for i, step in enumerate(steps):
            component = ProblemComponent(
                id=f"comp_{i + 1}",
                description=f"{step.capitalize()}: {problem}",
                complexity=5 + i,
                dependencies=[f"comp_{j}" for j in range(i)],
                estimated_effort=1.0 + (i * 0.5),
            )
            components.append(component)

        logger.info(f"Problema decomposto em {len(components)} componentes")

        return components

    def _functional_decompose(self, problem: str) -> List[ProblemComponent]:
        """Functional responsibility decomposition."""
        components = []
        functions = ["leitura", "escrita", "processamento", "validação", "apresentação"]

        for i, func in enumerate(functions):
            component = ProblemComponent(
                id=f"func_{i + 1}",
                description=f"Funcionalidade {func}: {problem}",
                complexity=5,
                estimated_effort=1.0,
            )
            components.append(component)

        return components

    def _sequential_decompose(self, problem: str) -> List[ProblemComponent]:
        """Sequential ordered decomposition."""
        steps = ["Preparação", "Execução", "Validação", "Finalização"]

        components = []
        for i, step in enumerate(steps):
            component = ProblemComponent(
                id=f"seq_{i + 1}",
                description=f"{step}: {problem}",
                complexity=5,
                dependencies=[f"seq_{j}" for j in range(i)],
                estimated_effort=1.0,
            )
            components.append(component)

        return components

    def _parallel_decompose(self, problem: str) -> List[ProblemComponent]:
        """Parallel group decomposition."""
        components = []

        parallel_parts = [
            "Análise inicial",
            "Preparação de recursos",
            "Configuração de ambiente",
        ]

        for i, part in enumerate(parallel_parts):
            component = ProblemComponent(
                id=f"par_{i + 1}",
                description=f"{part}: {problem}",
                complexity=5,
                estimated_effort=1.0,
            )
            components.append(component)

        return components

    def estimate_complexity(self, component: ProblemComponent) -> int:
        """Estimate the complexity level of a component."""
        base = 3

        base += len(component.dependencies)
        base += len(component.subtasks)

        return min(max(base, 1), 10)

    def generate_subtasks(self, component: ProblemComponent) -> List[AgentTask]:
        """Generate concrete subtasks from components."""
        import uuid

        subtasks = []

        action_to_type = {
            "ler": "read_file",
            "processar": "analyze_code",
            "escrever": "write_file",
            "validar": "validate_syntax",
        }

        action_words = ["ler", "processar", "escrever", "validar"]

        for action in action_words:
            task_type = action_to_type.get(action)
            if not task_type:
                continue

            task = AgentTask(
                id=str(uuid.uuid4())[:8],
                description=f"{action.capitalize()} para: {component.description}",
                priority=5,
                dependencies=[],
                parameters={
                    "type": task_type,
                    "component_id": component.id,
                    "action": action,
                },
            )
            subtasks.append(task)

        if not subtasks:
            task = AgentTask(
                id=str(uuid.uuid4())[:8],
                description=f"Processar: {component.description}",
                priority=5,
                dependencies=[],
                parameters={
                    "type": "list_directory",
                    "component_id": component.id,
                    "action": "processar",
                },
            )
            subtasks.append(task)

        return subtasks
