"""
Tests for the consciousness system (Skills and Agents).
"""

from unittest.mock import MagicMock

import pytest

from aura_cli.core.personas.agent_runner import AgentConfig, AgentRunner
from aura_cli.core.personas.models import (
    AgentExecutionResult,
    AgentMetadata,
    SkillMatch,
    SkillMetadata,
)
from aura_cli.core.personas.skill_retriever import SkillRetriever


class TestSkillMetadata:
    def test_creation(self):
        skill = SkillMetadata(
            name="test-skill",
            description="Test description",
            version="1.0.0",
            author="Test Author",
        )
        assert skill.name == "test-skill"
        assert skill.description == "Test description"
        assert skill.version == "1.0.0"

    def test_defaults(self):
        skill = SkillMetadata(
            name="minimal",
            description="Minimal skill",
        )
        assert skill.version == "1.0.0"
        assert skill.author == "Aura Core Team"
        assert skill.filepath is None


class TestAgentMetadata:
    def test_creation(self):
        agent = AgentMetadata(
            name="test-agent",
            description="Test agent",
            model="sonnet",
            allowed_tools=["Read", "Write"],
        )
        assert agent.name == "test-agent"
        assert agent.model == "sonnet"
        assert "Read" in agent.allowed_tools

    def test_defaults(self):
        agent = AgentMetadata(
            name="minimal",
            description="Minimal agent",
        )
        assert agent.model == "sonnet"
        assert agent.allowed_tools == []


class TestSkillMatch:
    def test_creation(self):
        skill = SkillMetadata(name="test", description="test")
        match = SkillMatch(skill=skill, score=0.85, content="# Content")
        assert match.score == 0.85
        assert match.content == "# Content"


class TestAgentExecutionResult:
    def test_success(self):
        result = AgentExecutionResult(
            agent_name="test-agent",
            success=True,
            output="Result output",
        )
        assert result.success is True
        assert result.error is None

    def test_failure(self):
        result = AgentExecutionResult(
            agent_name="test-agent",
            success=False,
            output="",
            error="Something went wrong",
        )
        assert result.success is False
        assert result.error == "Something went wrong"


class TestSkillRetriever:
    @pytest.fixture
    def temp_skills_dir(self, tmp_path):
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()

        skill_file = skills_dir / "test-skill.md"
        skill_file.write_text("""---
name: Test Skill
description: A test skill for testing purposes
version: 1.0.0
---

# Test Skill Content

This is the skill content.
""")
        return skills_dir

    def test_load_skills(self, temp_skills_dir):
        retriever = SkillRetriever(skills_dir=temp_skills_dir)
        skills = retriever.list_skills()
        assert len(skills) == 1
        assert skills[0].name == "Test Skill"

    def test_get_skill_by_name(self, temp_skills_dir):
        retriever = SkillRetriever(skills_dir=temp_skills_dir)
        content = retriever.get_skill_by_name("Test Skill")
        assert content is not None
        assert "Test Skill Content" in content

    def test_get_skill_by_name_not_found(self, temp_skills_dir):
        retriever = SkillRetriever(skills_dir=temp_skills_dir)
        content = retriever.get_skill_by_name("Nonexistent Skill")
        assert content is None

    def test_keyword_matching(self, temp_skills_dir):
        retriever = SkillRetriever(skills_dir=temp_skills_dir)
        retriever._model = False  # Force keyword matching

        match = retriever.find_best_match("test skill purposes", threshold=0.1)
        assert match is not None
        assert match.skill.name == "Test Skill"

    def test_empty_skills_dir(self, tmp_path):
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()
        retriever = SkillRetriever(skills_dir=empty_dir)
        assert len(retriever.list_skills()) == 0

    def test_reload(self, temp_skills_dir):
        retriever = SkillRetriever(skills_dir=temp_skills_dir)
        initial_count = len(retriever.list_skills())

        new_skill = temp_skills_dir / "new-skill.md"
        new_skill.write_text("""---
name: New Skill
description: A new skill
---

Content
""")

        retriever.reload()
        assert len(retriever.list_skills()) == initial_count + 1


class TestAgentRunner:
    @pytest.fixture
    def temp_agents_dir(self, tmp_path):
        agents_dir = tmp_path / "agents"
        agents_dir.mkdir()

        agent_file = agents_dir / "test-agent.md"
        agent_file.write_text("""---
name: test-agent
description: A test agent
model: sonnet
allowed-tools: Read, Write
---

You are a test agent. Do testing things.
""")
        return agents_dir

    def test_load_agents(self, temp_agents_dir):
        runner = AgentRunner(agents_dir=temp_agents_dir)
        agents = runner.list_agents()
        assert len(agents) == 1
        assert agents[0].name == "test-agent"

    def test_get_agent(self, temp_agents_dir):
        runner = AgentRunner(agents_dir=temp_agents_dir)
        config = runner.get_agent("test-agent")
        assert config is not None
        assert config.name == "test-agent"
        assert config.model == "sonnet"
        assert "Read" in config.allowed_tools
        assert "Write" in config.allowed_tools
        assert "test agent" in config.system_prompt

    def test_get_agent_not_found(self, temp_agents_dir):
        runner = AgentRunner(agents_dir=temp_agents_dir)
        config = runner.get_agent("nonexistent-agent")
        assert config is None

    def test_run_sync_not_found(self, temp_agents_dir):
        runner = AgentRunner(agents_dir=temp_agents_dir)
        mock_llm = MagicMock(return_value="response")

        result = runner.run_sync("nonexistent", "input", mock_llm)
        assert result.success is False
        assert "not found" in result.error

    def test_run_sync_success(self, temp_agents_dir):
        runner = AgentRunner(agents_dir=temp_agents_dir)
        mock_llm = MagicMock(return_value="Test response")

        result = runner.run_sync("test-agent", "test input", mock_llm)
        assert result.success is True
        assert result.output == "Test response"
        assert result.execution_time is not None

    def test_run_sync_error(self, temp_agents_dir):
        runner = AgentRunner(agents_dir=temp_agents_dir)
        mock_llm = MagicMock(side_effect=Exception("LLM error"))

        result = runner.run_sync("test-agent", "test input", mock_llm)
        assert result.success is False
        assert "LLM error" in result.error

    def test_reload(self, temp_agents_dir):
        runner = AgentRunner(agents_dir=temp_agents_dir)
        initial_count = len(runner.list_agents())

        new_agent = temp_agents_dir / "new-agent.md"
        new_agent.write_text("""---
name: new-agent
description: A new agent
---

New agent prompt.
""")

        runner.reload()
        assert len(runner.list_agents()) == initial_count + 1


class TestAgentConfig:
    def test_creation(self):
        config = AgentConfig(
            name="test",
            description="Test agent",
            model="opus",
            allowed_tools=["Read"],
            system_prompt="You are a test agent.",
        )
        assert config.name == "test"
        assert config.model == "opus"
        assert config.system_prompt == "You are a test agent."

    def test_defaults(self):
        config = AgentConfig(
            name="minimal",
            description="Minimal",
        )
        assert config.model == "sonnet"
        assert config.allowed_tools == []
        assert config.system_prompt == ""
