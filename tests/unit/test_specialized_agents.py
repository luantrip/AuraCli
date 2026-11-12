"""Testes para specialized agents."""


class TestCodeAgent:
    """Testes para code_agent."""

    def test_code_agent_import(self):
        """code_agent module imports successfully."""
        from aura_cli.core.agents.specialized_agents import code_agent

        assert code_agent is not None


class TestRefactorAgent:
    """Tests for refactor_agent."""

    def test_refactor_agent_import(self):
        """refactor_agent module imports successfully."""
        from aura_cli.core.agents.specialized_agents import refactor_agent

        assert refactor_agent is not None


class TestReviewAgent:
    """Testes para review_agent."""

    def test_review_agent_import(self):
        """review_agent module imports successfully."""
        from aura_cli.core.agents.specialized_agents import review_agent

        assert review_agent is not None


class TestTestAgent:
    """Testes para test_agent."""

    def test_test_agent_import(self):
        """test_agent module imports successfully."""
        from aura_cli.core.agents.specialized_agents import tester_agent as test_agent

        assert test_agent is not None
