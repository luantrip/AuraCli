"""Testes para edit system."""


class TestEditExecutor:
    """Testes para edit_executor."""

    def test_edit_executor_import(self):
        """Testa importação do módulo edit_executor."""
        from aura_cli.core.edit import edit_executor

        assert edit_executor is not None


class TestEditHistory:
    """Testes para edit_history."""

    def test_edit_history_import(self):
        """Testa importação do módulo edit_history."""
        from aura_cli.core.edit import edit_history

        assert edit_history is not None


class TestEditPlanner:
    """Testes para edit_planner."""

    def test_edit_planner_import(self):
        """Testa importação do módulo edit_planner."""
        from aura_cli.core.edit import edit_planner

        assert edit_planner is not None


class TestEditValidator:
    """Testes para edit_validator."""

    def test_edit_validator_import(self):
        """Testa importação do módulo edit_validator."""
        from aura_cli.core.edit import edit_validator

        assert edit_validator is not None


class TestMultiEdit:
    """Testes para multi_edit."""

    def test_multi_edit_import(self):
        """Testa importação do módulo multi_edit."""
        from aura_cli.core.edit import multi_edit

        assert multi_edit is not None
