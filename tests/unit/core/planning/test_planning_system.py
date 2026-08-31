"""Testes para planning system."""


class TestExecutionEngine:
    """Testes para execution_engine."""

    def test_execution_engine_import(self):
        """Testa importação do execution engine."""
        from aura_cli.core.agents.planning import execution_engine

        assert execution_engine is not None


class TestParallelExecutor:
    """Testes para parallel_executor."""

    def test_parallel_executor_import(self):
        """Testa importação do parallel executor."""
        from aura_cli.core.agents.planning import parallel_executor

        assert parallel_executor is not None


class TestProblemDecomposer:
    """Testes para problem_decomposer."""

    def test_problem_decomposer_import(self):
        """Testa importação do problem decomposer."""
        from aura_cli.core.agents.planning import problem_decomposer

        assert problem_decomposer is not None


class TestTaskPlanner:
    """Testes para task_planner."""

    def test_task_planner_import(self):
        """Testa importação do task planner."""
        from aura_cli.core.agents.planning import task_planner

        assert task_planner is not None


class TestTaskValidator:
    """Testes para task_validator."""

    def test_task_validator_import(self):
        """Testa importação do task validator."""
        from aura_cli.core.agents.planning import task_validator

        assert task_validator is not None
