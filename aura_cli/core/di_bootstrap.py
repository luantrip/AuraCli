"""
DI Container Bootstrap — Service Registration.

This module registers ALL application services into the DI container.
It is called once during application startup (from main.py or test setup).

Services are registered with lazy factories — no service is instantiated
until first resolved. This keeps startup fast.

Registration order doesn't matter for resolution (dependencies are resolved
on-demand), but is organized logically for readability.
"""

from __future__ import annotations

import threading
from typing import Any

from aura_cli.core.di import Services, get_container


def bootstrap_services() -> None:
    """
    Register all application services in the DI container.

    This function is idempotent — calling it multiple times is safe.
    Services are registered with lazy factory functions that import
    and instantiate on first resolve.
    """
    container = get_container()

    # Guard against double-registration
    if container.has(Services.CONFIG):
        return

    # ===================================================================
    # Foundation Services (no dependencies)
    # ===================================================================

    container.register(Services.CONFIG, _config_factory)
    container.register(Services.STATS, _stats_factory)
    container.register(
        Services.EVENT_BUS,
        _event_bus_factory,
        dependencies=[Services.CONFIG],
    )
    container.register(Services.SECURE_CONFIG, _secure_config_factory)

    # ===================================================================
    # LLM Services
    # ===================================================================

    container.register(
        Services.RATE_LIMITER,
        _rate_limiter_factory,
        dependencies=[Services.CONFIG],
    )
    container.register(
        Services.CIRCUIT_BREAKER_REGISTRY,
        _circuit_breaker_registry_factory,
    )
    container.register(
        Services.TASK_ROUTER,
        _task_router_factory,
        dependencies=[Services.CONFIG],
    )

    # ===================================================================
    # Memory Services
    # ===================================================================

    container.register(
        Services.MEMORY_SERVICE_REGISTRY,
        _memory_service_registry_factory,
    )
    container.register(
        Services.EMBEDDING_SERVICE,
        _embedding_service_factory,
    )
    container.register(
        Services.NOTEBOOK_SERVICE,
        _notebook_service_factory,
    )

    # ===================================================================
    # Context Services
    # ===================================================================

    container.register(
        Services.IMAGINATION_MANAGER,
        _imagination_manager_factory,
    )
    container.register(
        Services.SENTINEL_MANAGER,
        _sentinel_manager_factory,
    )
    container.register(
        Services.GRAPH_SERVICE,
        _graph_service_factory,
    )

    # ===================================================================
    # Tool Registry
    # ===================================================================

    container.register(
        Services.TOOL_REGISTRY,
        _tool_registry_factory,
        dependencies=[Services.CONFIG, Services.STATS],
    )

    # ===================================================================
    # Consciousness
    # ===================================================================

    container.register(
        Services.SKILL_RETRIEVER,
        _skill_retriever_factory,
    )
    container.register(
        Services.AGENT_RUNNER,
        _agent_runner_factory,
    )
    container.register(
        Services.CONSCIOUSNESS_MANAGER,
        _consciousness_manager_factory,
        dependencies=[Services.SKILL_RETRIEVER, Services.AGENT_RUNNER],
    )

    # ===================================================================
    # Sessions & State
    # ===================================================================

    container.register(
        Services.SESSION_STATE,
        _session_state_factory,
        dependencies=[Services.CONFIG],
    )
    container.register(
        Services.SESSION_MANAGER,
        _session_manager_factory,
    )
    container.register(Services.CHECKPOINT_MANAGER, _checkpoint_manager_factory)
    container.register(Services.TANGENT_MANAGER, _tangent_manager_factory)

    # ===================================================================
    # Quality & Infrastructure
    # ===================================================================

    container.register(Services.HOOK_MANAGER, _hook_manager_factory)
    container.register(Services.TODO_TRACKER, _todo_tracker_factory)
    container.register(Services.FORGE_MANAGER, _forge_manager_factory)


# ===========================================================================
# Factory Functions (lazy imports to keep startup fast)
# ===========================================================================


def _config_factory() -> Any:
    from aura_cli.core.config import ConfigCompat

    try:
        return ConfigCompat()
    except Exception:
        from aura_cli.core.config import Config

        return Config()


def _stats_factory() -> Any:
    from aura_cli.core.stats import StatsTracker

    return StatsTracker()


def _event_bus_factory() -> Any:
    from aura_cli.core.events.event_bus import CoreEventBus

    return CoreEventBus()


def _secure_config_factory() -> Any:
    from aura_cli.core.secure_config import SecureConfig

    return SecureConfig()


def _rate_limiter_factory() -> Any:
    from aura_cli.core.llm.rate_limiter import RateLimiter

    return RateLimiter()


def _circuit_breaker_registry_factory() -> Any:
    from aura_cli.core.llm.circuit_breaker import CircuitBreaker

    class CircuitBreakerRegistry:
        """Per-provider circuit breaker instances."""

        def __init__(self) -> None:
            self._breakers: dict[str, CircuitBreaker] = {}
            self._lock = threading.RLock()

        def get(self, provider: str) -> CircuitBreaker:
            with self._lock:
                if provider not in self._breakers:
                    self._breakers[provider] = CircuitBreaker()
                return self._breakers[provider]

        def reset_all(self) -> None:
            with self._lock:
                self._breakers.clear()

    return CircuitBreakerRegistry()


def _task_router_factory() -> Any:
    from aura_cli.core.llm.task_router import TaskRouter

    return TaskRouter()


def _memory_service_registry_factory() -> Any:
    import hashlib
    from pathlib import Path

    from aura_cli.core.memory.memory_service import MemoryService

    class MemoryServiceRegistry:
        """Per-project MemoryService instances."""

        def __init__(self) -> None:
            self._instances: dict[str, MemoryService] = {}
            self._lock = threading.Lock()

        def get(self, project_root: Path | None = None) -> MemoryService:
            if project_root is None:
                from aura_cli.core.memory.memory_service import _default_project_root

                resolved = _default_project_root()
            else:
                resolved = Path(project_root).expanduser().resolve()
            project_id = hashlib.sha1(
                str(resolved).encode(), usedforsecurity=False
            ).hexdigest()
            with self._lock:
                if project_id not in self._instances:
                    self._instances[project_id] = MemoryService(resolved)
                return self._instances[project_id]

    return MemoryServiceRegistry()


def _embedding_service_factory() -> Any:
    from aura_cli.core.embeddings.client import EmbeddingClient

    return EmbeddingClient()


def _notebook_service_factory() -> Any:
    from aura_cli.core.memory.notebook_service import get_notebook_service

    return get_notebook_service()


def _imagination_manager_factory() -> Any:
    from aura_cli.core.context.imagination_manager import ImaginationManager

    return ImaginationManager()


def _sentinel_manager_factory() -> Any:
    from pathlib import Path

    from aura_cli.core.context.sentinel_manager import SentinelManager

    return SentinelManager(Path.cwd())


def _graph_service_factory() -> Any:
    from aura_cli.core.context.graph_service import GraphService

    return GraphService()


def _tool_registry_factory() -> Any:
    from aura_cli.core.service_registry import ServiceRegistry

    return ServiceRegistry()


def _skill_retriever_factory() -> Any:
    from aura_cli.core.personas.skill_retriever import SkillRetriever

    return SkillRetriever()


def _agent_runner_factory() -> Any:
    from aura_cli.core.personas.agent_runner import AgentRunner

    return AgentRunner()


def _consciousness_manager_factory() -> Any:
    from aura_cli.core.personas.integrations import ConsciousnessManager

    return ConsciousnessManager()


def _session_state_factory() -> Any:
    from aura_cli.core.sessions.session_state import SessionStateManager

    return SessionStateManager()


def _session_manager_factory() -> Any:
    from aura_cli.core.sessions.session_manager import SessionManager

    return SessionManager()


def _checkpoint_manager_factory() -> Any:
    from aura_cli.core.checkpoint.manager import CheckpointManager

    return CheckpointManager()


def _tangent_manager_factory() -> Any:
    from aura_cli.core.tangent.manager import TangentManager

    return TangentManager()


def _hook_manager_factory() -> Any:
    from aura_cli.core.hooks.manager import HookManager

    return HookManager()


def _todo_tracker_factory() -> Any:
    from aura_cli.core.todo.todo_tracker import TodoTracker

    return TodoTracker()


def _forge_manager_factory() -> Any:
    try:
        from aura_cli.core.quality.forge_bridge import ForgeManager

        return ForgeManager()
    except Exception:
        return None
