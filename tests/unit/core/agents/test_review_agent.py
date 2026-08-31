"""Tests for core/agents/specialized_agents/review_agent.py."""

from unittest.mock import MagicMock, patch

import pytest

with patch("aura_cli.core.agents.agent_base.AgentBase.__init__", return_value=None):
    from aura_cli.core.agents.specialized_agents.review_agent import ReviewAgent


@pytest.fixture
def agent():
    with patch("aura_cli.core.agents.agent_base.AgentBase.__init__", return_value=None):
        a = ReviewAgent.__new__(ReviewAgent)
        a.agent_id = "review_agent"
        a.name = "Review Agent"
        a.description = "test"
        a.model = None
        a.consciousness_persona = None
        a.consciousness_skills = None
    return a


class TestExecuteTask:
    def test_analyze_code(self, agent):
        task = MagicMock()
        task.parameters = {"type": "analyze_code", "file_path": "test.py"}
        with patch(
            "aura_cli.core.tools.analyze_code", return_value="analysis", create=True
        ):
            result = agent._execute_task(task)
        assert result == "analysis"

    def test_validate_syntax(self, agent):
        task = MagicMock()
        task.parameters = {
            "type": "validate_syntax",
            "content": "x=1",
            "language": "python",
        }
        with patch(
            "aura_cli.core.tools.validate_syntax", return_value="ok", create=True
        ):
            result = agent._execute_task(task)
        assert result == "ok"

    def test_unknown_type_raises(self, agent):
        task = MagicMock()
        task.parameters = {"type": "unknown_xyz"}
        with pytest.raises(ValueError, match="Unknown task type"):
            agent._execute_task(task)

    def test_analyze_code_missing_file_path(self, agent):
        task = MagicMock()
        task.parameters = {"type": "analyze_code"}
        mock_tools = MagicMock()
        with patch.dict("sys.modules", {"aura_cli.core.tools": mock_tools}):
            with pytest.raises((ValueError, ImportError)):
                agent._execute_task(task)

    def test_validate_syntax_missing_params(self, agent):
        task = MagicMock()
        task.parameters = {"type": "validate_syntax", "content": "x"}
        mock_tools = MagicMock()
        with patch.dict("sys.modules", {"aura_cli.core.tools": mock_tools}):
            with pytest.raises((ValueError, ImportError)):
                agent._execute_task(task)


class TestGetConsciousnessInsights:
    def test_no_consciousness(self, agent):
        result = agent._get_consciousness_insights("code", "file.py")
        assert result == ""

    def test_with_persona_security(self, agent):
        agent.consciousness_persona = {
            "name": "code reviewer",
            "system_prompt": "Focus on Security",
        }
        result = agent._get_consciousness_insights("code", "f.py")
        assert "segurança" in result.lower() or "Security" in result

    def test_with_persona_performance(self, agent):
        agent.consciousness_persona = {
            "name": "reviewer",
            "system_prompt": "Focus on Performance",
        }
        result = agent._get_consciousness_insights("code", "f.py")
        assert "performance" in result.lower()

    def test_with_skills(self, agent):
        agent.consciousness_skills = [{"name": "Clean Code"}, {"name": "TDD"}]
        result = agent._get_consciousness_insights("code", "f.py")
        assert "Clean Code" in result

    def test_has_consciousness_method(self, agent):
        agent.has_consciousness = lambda: False
        assert not agent.has_consciousness()


class TestGetAvailableTools:
    def test_returns_tools(self, agent):
        """_get_available_tools() deve retornar schemas OpenAI derivados do ServiceRegistry."""
        tools = agent._get_available_tools()

        assert isinstance(tools, list)
        assert len(tools) > 0

        # Cada item deve ser schema OpenAI válido
        for tool in tools:
            assert tool["type"] == "function"
            assert "name" in tool["function"]
            assert "description" in tool["function"]

        names = {t["function"]["name"] for t in tools}
        # Ferramentas de análise de código devem estar presentes
        assert "analyze_code" in names, "analyze_code deve estar no ReviewAgent"
        # Ferramentas web devem ser excluídas (fora do escopo do agente)
        assert "browse_content" not in names
        assert "web_search" not in names
