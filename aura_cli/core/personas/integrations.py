"""
Aura Consciousness Orchestration Layer.

This module orchestrates the synergy between the Cognitive Augmented system (skills)
and the Native ADK Agent Framework. It enables dynamic knowledge injection,
semantic skill retrieval, and persona-driven agent enhancement.

Key Responsibilities:
    - Cognitive Augmentation: Injecting specialized knowledge (skills) into agents.
    - Persona Orchestration: Managing specialized agent personas for focused tasks.
    - Semantic Contextualization: Retrieving relevant skills based on user intent.
"""

import logging
from typing import Any, Dict, List, Optional

from aura_cli.core.personas.agent_runner import (
    AgentConfig,
    AgentRunner,
    get_agent_runner,
)
from aura_cli.core.personas.models import AgentMetadata, SkillMatch, SkillMetadata
from aura_cli.core.personas.skill_retriever import SkillRetriever, get_skill_retriever

logger = logging.getLogger(__name__)


class ConsciousnessManager:
    """
    Central Authority for the Aura Consciousness Ecosystem.

    This singleton orchestrates the integration of advanced knowledge (skills)
    and specialized personas into the core execution engine.

    Capabilities:
    - Intent-based Semantic Skill Retrieval.
    - Contextualized System Message Synthesis.
    - Native Agent Persona Augmentation.
    - Domain-specific Knowledge Injection for specialized tasks.

    Implementation Note:
        Designed for thread-safe access to shared cognitive resources.
    """

    _instance: Optional["ConsciousnessManager"] = None

    def __new__(cls) -> "ConsciousnessManager":
        """Enforce singleton pattern."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        """Initialize the instance."""
        if self._initialized:
            return

        self._skill_retriever: Optional[SkillRetriever] = None
        self._agent_runner: Optional[AgentRunner] = None
        self._cognitive_cache: Dict[str, str] = {}
        self._active_context: Dict[str, Any] = {}
        self._initialized = True

        logger.info("Aura ConsciousnessManager successfully initialized")

    @property
    def skill_retriever(self) -> SkillRetriever:
        """Lazy-resolves the semantic skill retrieval engine."""
        if self._skill_retriever is None:
            self._skill_retriever = get_skill_retriever()
        return self._skill_retriever

    @property
    def agent_runner(self) -> AgentRunner:
        """Lazy-resolves the persona management engine."""
        if self._agent_runner is None:
            self._agent_runner = get_agent_runner()
        return self._agent_runner

    def find_relevant_skills(
        self,
        query: str,
        max_skills: int = 3,
        threshold: float = 0.3,
    ) -> List[SkillMatch]:
        """
        Executes a semantic search for skills relevant to the provided context.

        Args:
            query: Semantic target for skill matching.
            max_skills: Horizontal limit for skill retrieval.
            threshold: Minimum cosine similarity for inclusion.

        Returns:
            A prioritized list of SkillMatch candidates.
        """
        matches = self.skill_retriever.find_all_matches(
            query=query,
            limit=max_skills,
            threshold=threshold,
        )

        if matches:
            logger.info(
                f"Resolved {len(matches)} cognitive matches for: {query[:50]}..."
            )
            for match in matches:
                logger.debug(f"  - {match.skill.name} (confidence: {match.score:.2f})")

        return matches

    def get_skill_content(self, skill_name: str) -> Optional[str]:
        """
        Retrieves full content for a given skill, utilizing an internal cognitive cache.

        Args:
            skill_name: Unique identifier for the skill.

        Returns:
            The raw content of the skill, or None if unresolved.
        """
        if skill_name in self._cognitive_cache:
            return self._cognitive_cache[skill_name]

        content = self.skill_retriever.get_skill_by_name(skill_name)
        if content:
            self._cognitive_cache[skill_name] = content
        return content

    def list_available_skills(self) -> List[SkillMetadata]:
        """Provides a catalog of all registered cognitive skills."""
        return self.skill_retriever.list_skills()

    def list_available_agents(self) -> List[AgentMetadata]:
        """Provides a catalog of all registered agent personas."""
        return self.agent_runner.list_agents()

    def get_agent_config(self, agent_name: str) -> Optional[AgentConfig]:
        """
        Resolves the configuration schema for a specific agent persona.

        Args:
            agent_name: Unique identifier for the agent persona.
        """
        return self.agent_runner.get_agent(agent_name)

    def build_enhanced_system_message(
        self,
        base_prompt: str,
        user_query: Optional[str] = None,
        include_skills: bool = True,
        max_skills: int = 2,
        skill_threshold: float = 0.3,
        agent_persona: Optional[str] = None,
    ) -> str:
        """
        Synthesizes an augmented system message through dynamic context injection.

        Process:
        1. Foundations: Initializes with the core base prompt.
        2. Knowledge Injection: Augments with relevant semantic skills.
        3. Persona Overlay: Applies specific persona instructions if requested.
        """
        parts = [base_prompt]

        if include_skills and user_query:
            skills_section = self._build_skills_section(
                user_query, max_skills, skill_threshold
            )
            if skills_section:
                parts.append(skills_section)

        if agent_persona:
            persona_section = self._build_persona_section(agent_persona)
            if persona_section:
                parts.append(persona_section)

        augmented_message = "\n\n".join(parts)

        logger.debug(
            f"Augmented system message generated: {len(augmented_message)} characters"
        )
        return augmented_message

    def get_skills_section(
        self,
        query: str,
        max_skills: int = 2,
        threshold: float = 0.35,
    ) -> Optional[str]:
        """
        Constructs a standalone 'Augmented Knowledge' section for a given query intent.
        """
        try:
            from aura_cli.core.config import get_config_manager

            threshold = float(
                get_config_manager().get("consciousness_threshold") or threshold
            )
        except Exception as _e:
            pass  # silenced: {_e}
        return self._build_skills_section(query, max_skills, threshold)

    def _build_skills_section(
        self,
        query: str,
        max_skills: int,
        threshold: float,
    ) -> Optional[str]:
        """Internal synthesizer for the cognitive skills section."""
        matches = self.find_relevant_skills(query, max_skills, threshold)

        if not matches:
            return None

        skills_content = []
        for match in matches:
            content = self._extract_skill_content(match.content)
            skills_content.append(
                f"### {match.skill.name} (relevance: {match.score:.0%})\n{content}"
            )

        return (
            "## 📚 Augmented Knowledge Base\n\n"
            "Leverage the following context to guide your execution:\n\n"
            + "\n\n---\n\n".join(skills_content)
        )

    def _extract_skill_content(self, raw_content: str, max_chars: int = 3000) -> str:
        """Normalized extraction of skill body, stripping metadata headers."""
        if not raw_content.startswith("---"):
            body = raw_content
        else:
            parts = raw_content.split("---", 2)
            body = parts[2].strip() if len(parts) >= 3 else raw_content

        if len(body) > max_chars:
            body = body[:max_chars] + "\n\n*[conteúdo truncado para economizar tokens]*"
        return body

    def _build_persona_section(self, agent_name: str) -> Optional[str]:
        """Internal synthesizer for the persona overlay section."""
        config = self.get_agent_config(agent_name)

        if not config:
            logger.warning(f"Persona resolution failed for: {agent_name}")
            return None

        return (
            f"## 🎭 Active Persona: {config.name}\n\n"
            f"**Definition**: {config.description}\n\n"
            f"**Execution Constraints**:\n{config.system_prompt}"
        )

    def enhance_native_agent(
        self,
        agent_type: str,
        task_description: str,
    ) -> Dict[str, Any]:
        """
        Generates cognitive enhancement metadata for a native ADK agent.

        Args:
            agent_type: Target agent classification (code, review, refactor, test).
            task_description: Semantic description of the current objective.

        Returns:
            A metadata dictionary containing semantic matches, persona overlays,
            and task-specific cognitive hints.
        """
        result: Dict[str, Any] = {
            "relevant_skills": [],
            "persona_config": None,
            "context_hints": [],
        }

        agent_persona_map = {
            "code": None,
            "review": "code-reviewer-agent",
            "refactor": "code-refactor-agent",
            "test": "test-writer-agent",
            "ops": "ops-agent",
        }

        matches = self.find_relevant_skills(task_description, max_skills=2)
        if matches:
            result["relevant_skills"] = [
                {
                    "name": m.skill.name,
                    "content": self._extract_skill_content(m.content),
                    "score": m.score,
                }
                for m in matches
            ]

        persona_name = agent_persona_map.get(agent_type)
        if persona_name:
            config = self.get_agent_config(persona_name)
            if config:
                result["persona_config"] = {
                    "name": config.name,
                    "description": config.description,
                    "system_prompt": config.system_prompt,
                    "model": config.model,
                    "allowed_tools": config.allowed_tools,
                }

        result["context_hints"] = self._generate_cognitive_hints(
            agent_type, task_description
        )

        return result

    def _generate_cognitive_hints(
        self,
        agent_type: str,
        task_description: str,
    ) -> List[str]:
        """Synthesizes task-aware cognitive hints to optimize agent output."""
        hints = []
        task_lower = task_description.lower()

        if agent_type == "review":
            if "security" in task_lower:
                hints.append(
                    "Prioritize security-critical code paths and sensitive data flow."
                )
            if "performance" in task_lower:
                hints.append(
                    "Analyze for algorithmic efficiency, resource leaks, and async-blocking patterns."
                )

        elif agent_type == "refactor":
            if "clean" in task_lower or "quality" in task_lower:
                hints.append(
                    "Enforce Clean Code standards: semantic naming, SRP, and function atomicity."
                )
            if "solid" in task_lower:
                hints.append(
                    "Validate compliance with SOLID principles, prioritizing decoupling and interface segregation."
                )

        elif agent_type == "test":
            if "unit" in task_lower:
                hints.append(
                    "Design isolated unit tests with robust mocking strategies."
                )
            if "integration" in task_lower:
                hints.append(
                    "Construct scenarios verifying cross-component interactions and boundary conditions."
                )

        return hints

    def set_session_context(self, key: str, value: Any) -> None:
        """Stores a contextual variable for the active session."""
        self._active_context[key] = value

    def get_session_context(self, key: str, default: Any = None) -> Any:
        """Retrieves a contextual variable from the active session."""
        return self._active_context.get(key, default)

    def flush_context(self) -> None:
        """Clears all session-specific cognitive context."""
        self._active_context.clear()

    def reload_cognitive_base(self) -> None:
        """Performs a full refresh of the cognitive base (skills and personas) from persistent storage."""
        self._cognitive_cache.clear()
        self.skill_retriever.reload()
        self.agent_runner.reload()
        logger.info("Aura Cognitive Base successfully reloaded")


_manager: Optional[ConsciousnessManager] = None


def get_consciousness_manager() -> ConsciousnessManager:
    """Returns the singleton ConsciousnessManager instance."""
    # Try DI container first (preferred path)
    try:
        from aura_cli.core.di import Services, get_container

        container = get_container()
        if container.has(Services.CONSCIOUSNESS_MANAGER):
            return container.resolve(Services.CONSCIOUSNESS_MANAGER)
    except Exception:
        pass

    # Fallback to legacy singleton
    global _manager
    if _manager is None:
        _manager = ConsciousnessManager()
    return _manager
