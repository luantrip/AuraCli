"""
Aura Agent Development Kit (ADK).
"""

__version__ = "0.2.0"
__author__ = "Aura CLI Team"

import logging
import threading
from typing import Any

logger = logging.getLogger(__name__)

from aura_cli.adk.agent import (
    Agent,
    AgentCapability,
    AgentConfig,
    AgentResponse,
    AgentState,
    CompositeAgent,
    create_agent,
    get_agent_class,
    list_agents,
    register_agent,
)
from aura_cli.adk.deprecations import DEPRECATIONS, Deprecation
from aura_cli.adk.memory import (
    ConversationMemory,
    Memory,
    MemoryEntry,
    MemoryStore,
    PersistentMemory,
    VectorMemory,
    create_memory,
)
from aura_cli.adk.metrics import AgentMetrics, MetricsCollector, PerformanceTracker

_specialized_agents_cache: dict[str, Any] = {}
_specialized_agents_lock = threading.Lock()


def _get_specialized_agent(name: str):
    """Get a specialized agent class, loading lazily if needed."""
    if name in _specialized_agents_cache:
        return _specialized_agents_cache[name]

    with _specialized_agents_lock:
        if name in _specialized_agents_cache:
            return _specialized_agents_cache[name]

        try:
            from aura_cli.adk.specialized import (
                CodeAgent as _CodeAgent,
            )
            from aura_cli.adk.specialized import (
                RefactorAgent as _RefactorAgent,
            )
            from aura_cli.adk.specialized import (
                ReviewAgent as _ReviewAgent,
            )
            from aura_cli.adk.specialized import (
                TestAgent as _TestAgent,
            )

            _specialized_agents_cache["CodeAgent"] = _CodeAgent
            _specialized_agents_cache["RefactorAgent"] = _RefactorAgent
            _specialized_agents_cache["ReviewAgent"] = _ReviewAgent
            _specialized_agents_cache["TestAgent"] = _TestAgent

            try:
                from aura_cli.adk.specialized import OpsAgent as _OpsAgent

                _specialized_agents_cache["OpsAgent"] = _OpsAgent
            except ImportError as _e:
                logger.debug("OpsAgent not available (optional): %s", _e)

            try:
                from aura_cli.adk.specialized import PlanningAgent as _PlanningAgent

                _specialized_agents_cache["PlanningAgent"] = _PlanningAgent
            except ImportError as _e:
                logger.debug("PlanningAgent not available (optional): %s", _e)

            if name in _specialized_agents_cache:
                return _specialized_agents_cache[name]
        except Exception as e:
            logger.warning(f"Failed to import specialized agent {name}: {e}")
            _specialized_agents_cache[name] = None
            return None

        logger.warning(f"Specialized agent {name} not found")
        _specialized_agents_cache[name] = None
        return None


class _LazyAgentProxy:
    """Proxy that loads the real agent class on first use to break circular imports."""

    def __init__(self, agent_name: str):
        """Initialize the instance."""
        self._agent_name = agent_name
        self._agent_class = None

    def _ensure_loaded(self):
        if self._agent_class is None:
            self._agent_class = _get_specialized_agent(self._agent_name)
            if self._agent_class is None:
                raise RuntimeError(
                    f"Cannot load {self._agent_name}: "
                    "Import must happen in main thread or agent not available"
                )

    def __call__(self, *args, **kwargs):
        self._ensure_loaded()
        return self._agent_class(*args, **kwargs)

    def __getattr__(self, name):
        self._ensure_loaded()
        return getattr(self._agent_class, name)

    def __repr__(self):
        if self._agent_class is None:
            return f"<LazyProxy for {self._agent_name} (not loaded)>"
        return f"<LazyProxy for {self._agent_name} (loaded)>"


CodeAgent = _LazyAgentProxy("CodeAgent")
RefactorAgent = _LazyAgentProxy("RefactorAgent")
ReviewAgent = _LazyAgentProxy("ReviewAgent")
TestAgent = _LazyAgentProxy("TestAgent")
OpsAgent = _LazyAgentProxy("OpsAgent")
PlanningAgent = _LazyAgentProxy("PlanningAgent")


from aura_cli.adk.tools import (
    Tool,
    ToolCategory,
    ToolRegistry,
    ToolResult,
    ToolSchema,
    get_tool_registry,
    reset_tool_registry,
    tool,
)
from aura_cli.adk.workflow import (
    StepState,
    Workflow,
    WorkflowBuilder,
    WorkflowResult,
    WorkflowState,
    WorkflowStep,
    create_workflow,
)

__all__ = [
    "DEPRECATIONS",
    "Agent",
    "AgentCapability",
    "AgentConfig",
    "AgentMetrics",
    "AgentResponse",
    "AgentState",
    "CodeAgent",
    "CompositeAgent",
    "ConversationMemory",
    "Deprecation",
    "Memory",
    "MemoryEntry",
    "MemoryStore",
    "MetricsCollector",
    "OpsAgent",
    "PerformanceTracker",
    "PersistentMemory",
    "PlanningAgent",
    "RefactorAgent",
    "ReviewAgent",
    "StepState",
    "TestAgent",
    "Tool",
    "ToolCategory",
    "ToolRegistry",
    "ToolResult",
    "ToolSchema",
    "VectorMemory",
    "Workflow",
    "WorkflowBuilder",
    "WorkflowResult",
    "WorkflowState",
    "WorkflowStep",
    "__version__",
    "create_agent",
    "create_memory",
    "create_workflow",
    "get_agent_class",
    "get_tool_registry",
    "list_agents",
    "register_agent",
    "reset_tool_registry",
    "tool",
]
