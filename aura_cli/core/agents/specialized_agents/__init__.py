"""Specialized agents package for Aura CLI.

Re-exports CodeAgent, TestAgent, RefactorAgent and ReviewAgent — all inherit
from AgentBase and implement domain-specific _execute_task() logic using
the function-calling tool system.
"""

from aura_cli.core.agents.specialized_agents.code_agent import CodeAgent
from aura_cli.core.agents.specialized_agents.refactor_agent import RefactorAgent
from aura_cli.core.agents.specialized_agents.review_agent import ReviewAgent
from aura_cli.core.agents.specialized_agents.test_agent import TestAgent

__all__ = [
    "CodeAgent",
    "RefactorAgent",
    "ReviewAgent",
    "TestAgent",
]
