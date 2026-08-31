"""Personas package — skills, specialist agents and consciousness integration.

Skills (.md files with YAML frontmatter) are indexed and injected into
agent prompts based on context. Agent personas define role-specific prompts
and allowed tools. ConsciousnessManager orchestrates both.
"""

from aura_cli.core.personas.agent_runner import (
    AgentConfig,
    AgentRunner,
    get_agent_runner,
)
from aura_cli.core.personas.integrations import (
    ConsciousnessManager,
    get_consciousness_manager,
)
from aura_cli.core.personas.models import (
    AgentExecutionResult,
    AgentMetadata,
    SkillMatch,
    SkillMetadata,
)
from aura_cli.core.personas.skill_retriever import SkillRetriever, get_skill_retriever

__all__ = [
    "AgentConfig",
    "AgentExecutionResult",
    "AgentMetadata",
    "AgentRunner",
    "ConsciousnessManager",
    "SkillMatch",
    "SkillMetadata",
    "SkillRetriever",
    "get_agent_runner",
    "get_consciousness_manager",
    "get_skill_retriever",
]
