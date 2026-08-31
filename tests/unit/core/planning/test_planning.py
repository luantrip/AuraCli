"""
Testes Unitários para Sistema de Planejamento do Aura CLI.

Este módulo contém testes unitários que verificam o funcionamento individual
de componentes do sistema de planejamento de tarefas, incluindo planejamento
de tarefas, decomposição de problemas e execução de planos.

Componentes Testados:
    - TaskPlanner: Planejador de tarefas com estratégias
    - PlanStrategy: Estratégias de planejamento
    - ProblemDecomposer: Decompositor de problemas complexos
    - DecompositionStrategy: Estratégias de decomposição
    - ExecutionEngine: Engine de execução de planos
    - ExecutionMode: Modos de execução (sequential, parallel, hybrid)

Cenários de Teste:
    - Inicialização: Criação de planner, decomposer e engine
    - Planejamento Sequencial: Criação de plano sequencial
    - Planejamento por Prioridade: Ordenação por prioridade
    - Decomposição Hierárquica: Decomposição de problemas
    - Execução Sequencial: Execução de planos

Validações:
    - Planner inicializa corretamente
    - Planos são criados com estratégias corretas
    - Tarefas são ordenadas por prioridade
    - Problemas são decompostos adequadamente
    - Engine executa planos corretamente

Estrutura de Testes:
    - TestTaskPlanner: Testes do planejador
    - TestProblemDecomposer: Testes do decompositor
    - TestExecutionEngine: Testes do engine de execução

Estratégias de Planejamento:
    - SEQUENTIAL: Execução sequencial
    - PARALLEL: Execução paralela quando possível
    - DEPENDENCY_ORDER: Ordenado por dependências
    - PRIORITY_ORDER: Ordenado por prioridade

Estratégias de Decomposição:
    - HIERARCHICAL: Decomposição hierárquica
    - FUNCTIONAL: Por funcionalidade
    - SEQUENTIAL: Por sequência lógica
    - PARALLEL: Por paralelismo

Modos de Execução:
    - SEQUENTIAL: Execução sequencial
    - PARALLEL: Execução paralela
    - HYBRID: Híbrido (paralelo quando possível)

Exemplo de Uso:
    ```python
    def test_planning():
        planner = TaskPlanner()
        plan = planner.create_plan("Objective", tasks, PlanStrategy.SEQUENTIAL)

        decomposer = ProblemDecomposer()
        components = decomposer.decompose(problem, DecompositionStrategy.HIERARCHICAL)
    ```

Dependências:
    - pytest: Framework de testes
    - unittest.mock: Para mocking de orchestrator
    - task_planner: Sistema de planejamento
    - problem_decomposer: Sistema de decomposição
    - execution_engine: Engine de execução
"""

from aura_cli.core.agents.agent_base import AgentTask
from aura_cli.core.agents.planning.execution_engine import (
    ExecutionEngine,
    ExecutionMode,
)
from aura_cli.core.agents.planning.problem_decomposer import (
    DecompositionStrategy,
    ProblemDecomposer,
)
from aura_cli.core.agents.planning.task_planner import PlanStrategy, TaskPlanner


class TestTaskPlanner:
    """Testes para TaskPlanner."""

    def test_planner_initialization(self):
        """Testa inicialização do planejador."""
        planner = TaskPlanner()

        assert planner is not None

    def test_create_plan_sequential(self):
        """Testa criação de plano sequencial."""
        planner = TaskPlanner()

        tasks = [
            {"id": "1", "description": "Task 1", "priority": 1},
            {"id": "2", "description": "Task 2", "priority": 2},
        ]

        plan = planner.create_plan(
            "Test objective", tasks, strategy=PlanStrategy.SEQUENTIAL
        )

        assert plan is not None
        assert len(plan.tasks) == 2
        assert plan.tasks[0].id == "1"
        assert plan.tasks[1].id == "2"

    def test_create_plan_priority_ordered(self):
        """Testa criação de plano ordenado por prioridade."""
        planner = TaskPlanner()

        tasks = [
            {"id": "1", "description": "Task 1", "priority": 2},
            {"id": "2", "description": "Task 2", "priority": 1},
        ]

        plan = planner.create_plan("Test", tasks, strategy=PlanStrategy.PRIORITY_ORDER)

        # TaskPlanner ordena por prioridade com reverse=True (maior primeiro)
        # Então prioridade 2 vem antes de 1
        assert plan.tasks[0].priority == 2
        assert plan.tasks[1].priority == 1


class TestProblemDecomposer:
    """Testes para ProblemDecomposer."""

    def test_decomposer_initialization(self):
        """Testa inicialização do decompositor."""
        decomposer = ProblemDecomposer()

        assert decomposer is not None

    def test_decompose_hierarchical(self):
        """Testa decomposição hierárquica."""
        decomposer = ProblemDecomposer()

        problem = "Criar aplicação web com frontend e backend"

        components = decomposer.decompose(
            problem, strategy=DecompositionStrategy.HIERARCHICAL
        )

        assert len(components) > 0
        assert any(
            "frontend" in c.description.lower() or "backend" in c.description.lower()
            for c in components
        )


class TestExecutionEngine:
    """Testes para ExecutionEngine."""

    def test_engine_initialization(self):
        """Testa inicialização do engine."""
        from unittest.mock import Mock

        from aura_cli.core.agents.agent_orchestrator import AgentOrchestrator

        mock_orch = Mock(spec=AgentOrchestrator)
        engine = ExecutionEngine(orchestrator=mock_orch, mode=ExecutionMode.SEQUENTIAL)

        assert engine.mode == ExecutionMode.SEQUENTIAL
        assert engine.orchestrator == mock_orch

    def test_execute_plan_sequential(self):
        """Testa execução sequencial de plano."""
        from unittest.mock import Mock

        from aura_cli.core.agents.agent_orchestrator import AgentOrchestrator
        from aura_cli.core.agents.planning.task_planner import TaskPlan

        mock_orch = Mock(spec=AgentOrchestrator)
        # Mock do método distribute_task que retorna um task_id
        mock_orch.distribute_task.return_value = "task_1"

        engine = ExecutionEngine(orchestrator=mock_orch, mode=ExecutionMode.SEQUENTIAL)

        plan = TaskPlan(
            plan_id="plan_1",
            description="Test",
            strategy=PlanStrategy.SEQUENTIAL,
            tasks=[AgentTask(id="1", description="Task 1", priority=1)],
        )

        results = engine.execute_plan(plan)

        assert len(results) > 0
