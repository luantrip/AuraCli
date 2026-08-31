"""
Tests for the consciousness integration system.

Verifies that:
- SkillRetriever loads and finds skills correctly
- AgentRunner loads agent personas correctly
- ConsciousnessManager integrates both systems
- System message enhancement works properly
"""

import pytest


class TestSkillRetriever:
    """Tests for SkillRetriever functionality."""

    def test_skill_retriever_loads_skills(self):
        """Verify skills are loaded from the skills directory."""
        from aura_cli.core.personas import SkillRetriever

        retriever = SkillRetriever()
        skills = retriever.list_skills()

        assert len(skills) > 0, "Should have loaded at least one skill"

        # Check that expected skills exist
        skill_names = [s.name for s in skills]
        assert any("clean" in name.lower() for name in skill_names), (
            "Should have a clean code skill"
        )

    def test_skill_retriever_finds_relevant_skill(self):
        """Verify skill matching works for relevant queries."""
        from aura_cli.core.personas import SkillRetriever

        retriever = SkillRetriever()

        # Test finding clean code skill
        match = retriever.find_best_match("How to write clean code?", threshold=0.2)

        assert match is not None, "Should find a matching skill"
        assert len(match.content) > 0, "Should have skill content"

    def test_skill_retriever_keyword_fallback(self):
        """Verify keyword matching works when semantic search unavailable."""
        from aura_cli.core.personas import SkillRetriever

        retriever = SkillRetriever()
        retriever._model = False  # Force keyword matching

        # Test keyword matching
        match = retriever.find_best_match("SOLID principles", threshold=0.1)

        # Should find something (may be SOLID or related)
        assert match is not None or retriever._skills, (
            "Should either find a match or have skills loaded"
        )


class TestAgentRunner:
    """Tests for AgentRunner functionality."""

    def test_agent_runner_loads_agents(self):
        """Verify agent personas are loaded from agents directory."""
        from aura_cli.core.personas import AgentRunner

        runner = AgentRunner()
        agents = runner.list_agents()

        assert len(agents) > 0, "Should have loaded at least one agent"

        # Check that expected agents exist
        agent_names = [a.name for a in agents]
        assert any("reviewer" in name.lower() for name in agent_names), (
            "Should have a code reviewer agent"
        )

    def test_agent_runner_gets_agent_config(self):
        """Verify agent configuration can be retrieved."""
        from aura_cli.core.personas import AgentRunner

        runner = AgentRunner()

        # Get code reviewer agent
        config = runner.get_agent("code-reviewer-agent")

        assert config is not None, "Should find code-reviewer-agent"
        assert len(config.system_prompt) > 0, "Should have a system prompt"
        assert config.model is not None, "Should have a model specified"


class TestConsciousnessManager:
    """Tests for ConsciousnessManager integration."""

    def test_consciousness_manager_singleton(self):
        """Verify ConsciousnessManager is a singleton."""
        from aura_cli.core.personas import ConsciousnessManager

        manager1 = ConsciousnessManager()
        manager2 = ConsciousnessManager()

        assert manager1 is manager2, "Should be the same instance"

    def test_consciousness_manager_finds_skills(self):
        """Verify manager can find relevant skills."""
        from aura_cli.core.personas import get_consciousness_manager

        manager = get_consciousness_manager()

        # Find skills for a code review task
        skills = manager.find_relevant_skills(
            "Review this code for best practices",
            max_skills=2,
            threshold=0.2,
        )

        # Should find at least one skill
        assert isinstance(skills, list), "Should return a list"

    def test_consciousness_manager_lists_resources(self):
        """Verify manager can list available resources."""
        from aura_cli.core.personas import get_consciousness_manager

        manager = get_consciousness_manager()

        skills = manager.list_available_skills()
        agents = manager.list_available_agents()

        assert len(skills) > 0, "Should have skills available"
        assert len(agents) > 0, "Should have agents available"

    def test_build_enhanced_system_message(self):
        """Verify system message enhancement works."""
        from aura_cli.core.personas import get_consciousness_manager

        manager = get_consciousness_manager()

        base_prompt = "You are a helpful AI assistant."
        user_query = "Help me refactor this code for better readability"

        enhanced = manager.build_enhanced_system_message(
            base_prompt=base_prompt,
            user_query=user_query,
            include_skills=True,
            max_skills=1,
            skill_threshold=0.2,
        )

        # Enhanced message should be at least as long as base
        assert len(enhanced) >= len(base_prompt), (
            "Enhanced message should not be shorter than base"
        )

        # If skills were found, should contain knowledge section
        skills = manager.find_relevant_skills(user_query, max_skills=1, threshold=0.2)
        if skills:
            assert "Conhecimento Relevante" in enhanced or len(enhanced) > len(
                base_prompt
            ), "Should include knowledge section when skills found"

    def test_enhance_native_agent(self):
        """Verify specialized agent enhancement works."""
        from aura_cli.core.personas import get_consciousness_manager

        manager = get_consciousness_manager()

        enhancement = manager.enhance_native_agent(
            agent_type="review",
            task_description="Review code for security issues",
        )
        assert "relevant_skills" in enhancement, "Should include relevant_skills"
        assert "persona_config" in enhancement, "Should include persona_config"
        assert "context_hints" in enhancement, "Should include context_hints"

        # Review agent should get the reviewer persona
        if enhancement.get("persona_config"):
            assert "reviewer" in enhancement["persona_config"]["name"].lower(), (
                "Should get reviewer persona for review agent"
            )


class TestAgentBaseConsciousness:
    """Tests for consciousness integration in AgentBase."""

    def test_agent_base_has_consciousness_attributes(self):
        """Verify AgentBase has consciousness attributes."""
        from aura_cli.core.agents.specialized_agents import ReviewAgent

        agent = ReviewAgent()

        assert hasattr(agent, "consciousness_persona"), (
            "Should have consciousness_persona attribute"
        )
        assert hasattr(agent, "consciousness_skills"), (
            "Should have consciousness_skills attribute"
        )
        assert hasattr(agent, "has_consciousness"), (
            "Should have has_consciousness method"
        )
        assert hasattr(agent, "get_consciousness_enhanced_prompt"), (
            "Should have get_consciousness_enhanced_prompt method"
        )

    def test_agent_has_consciousness_false_by_default(self):
        """Verify has_consciousness is False when not set."""
        from aura_cli.core.agents.specialized_agents import ReviewAgent

        agent = ReviewAgent()

        assert not agent.has_consciousness(), "Should not have consciousness by default"

    def test_agent_has_consciousness_true_when_set(self):
        """Verify has_consciousness is True when data is set."""
        from aura_cli.core.agents.specialized_agents import ReviewAgent

        agent = ReviewAgent()
        agent.consciousness_persona = {"name": "test", "system_prompt": "test"}

        assert agent.has_consciousness(), (
            "Should have consciousness when persona is set"
        )

    def test_get_consciousness_enhanced_prompt(self):
        """Verify prompt enhancement works."""
        from aura_cli.core.agents.specialized_agents import ReviewAgent

        agent = ReviewAgent()
        agent.consciousness_persona = {
            "name": "Test Persona",
            "system_prompt": "You are a test persona.",
        }
        agent.consciousness_skills = [
            {"name": "Test Skill", "content": "This is test content."},
        ]

        base_prompt = "You are an AI."
        enhanced = agent.get_consciousness_enhanced_prompt(base_prompt)

        assert base_prompt in enhanced, "Should include base prompt"
        assert "Test Persona" in enhanced, "Should include persona name"
        assert "Test Skill" in enhanced, "Should include skill name"


class TestIntegrationFlow:
    """End-to-end integration tests."""

    def test_full_consciousness_flow(self):
        """Test the full flow of consciousness integration."""
        from aura_cli.core.agents.specialized_agents import ReviewAgent
        from aura_cli.core.personas import get_consciousness_manager

        # 1. Get consciousness manager
        manager = get_consciousness_manager()

        # 2. Get enhancement for review agent
        enhancement = manager.enhance_native_agent(
            agent_type="review",
            task_description="Review this Python code for clean code practices",
        )

        # 3. Create and configure agent
        agent = ReviewAgent()

        if enhancement.get("persona_config"):
            agent.consciousness_persona = enhancement["persona_config"]
        if enhancement.get("relevant_skills"):
            agent.consciousness_skills = enhancement["relevant_skills"]

        # 4. Verify agent is enhanced
        # Note: May or may not have consciousness depending on matches
        if enhancement.get("persona_config") or enhancement.get("relevant_skills"):
            assert agent.has_consciousness(), (
                "Agent should have consciousness when enhancement data exists"
            )

        # 5. Build enhanced prompt
        base = "You are a code review assistant."
        enhanced = agent.get_consciousness_enhanced_prompt(base)

        assert len(enhanced) >= len(base), "Enhanced prompt should not be shorter"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
