"""Unified dependency injection container for Aura CLI.

Replaces scattered module-level singletons with a centralized, testable
service registry. Supports SINGLETON and TRANSIENT lifecycles, keyed
service registries, lazy init, and test overrides via container.override()
/ container.reset(). Service names are defined in the Services enum.
"""

from __future__ import annotations

import contextlib
from enum import Enum
import inspect
import threading
from typing import Any, Callable, Dict, List, Optional, Set, TypeVar

T = TypeVar("T")


class Lifecycle(Enum):
    """Service lifecycle modes."""

    SINGLETON = "singleton"
    TRANSIENT = "transient"


class Services(str, Enum):
    """
    Canonical service identifiers.

    These names provide compile-time safety and IDE autocomplete for services
    resolved via the container. Most are wired in ``di_bootstrap.bootstrap_services()``;
    a few identifiers are declared for planned/optional subsystems that are not yet
    registered (resolving those raises ``KeyError``). The exact set of not-yet-registered
    members is pinned by ``test_unregistered_services_are_explicitly_known`` to prevent
    silent drift.
    """

    # === Foundation ===
    CONFIG = "config"
    LOGGER_FACTORY = "logger_factory"
    STATS = "stats"
    EVENT_BUS = "event_bus"

    # === LLM ===
    LLM_CLIENT = "llm_client"
    RATE_LIMITER = "rate_limiter"
    CIRCUIT_BREAKER_REGISTRY = "circuit_breaker_registry"
    TASK_ROUTER = "task_router"
    MODEL_PROFILES = "model_profiles"

    # === Memory ===
    MEMORY_SERVICE_REGISTRY = "memory_service_registry"
    VECTOR_STORE_FACTORY = "vector_store_factory"
    NOTEBOOK_SERVICE = "notebook_service"
    COGNITIVE_REFINER = "cognitive_refiner"

    # === Context ===
    PROJECT_INDEXER = "project_indexer"
    SENTINEL_MANAGER = "sentinel_manager"
    IMAGINATION_MANAGER = "imagination_manager"
    GRAPH_SERVICE = "graph_service"

    # === Tools ===
    TOOL_REGISTRY = "tool_registry"

    # === Agents ===
    AGENT_ORCHESTRATOR = "agent_orchestrator"
    AGENT_FACTORY = "agent_factory"
    AGENT_COMMUNICATION = "agent_communication"

    # === Consciousness ===
    CONSCIOUSNESS_MANAGER = "consciousness_manager"
    SKILL_RETRIEVER = "skill_retriever"
    AGENT_RUNNER = "agent_runner"

    # === Sessions & State ===
    SESSION_MANAGER = "session_manager"
    SESSION_STATE = "session_state"
    CHECKPOINT_MANAGER = "checkpoint_manager"
    TANGENT_MANAGER = "tangent_manager"

    # === Quality ===
    FORGE_MANAGER = "forge_manager"

    # === Infrastructure ===
    SECURE_CONFIG = "secure_config"
    HOOK_MANAGER = "hook_manager"
    TODO_TRACKER = "todo_tracker"
    EMBEDDING_SERVICE = "embedding_service"


class _ServiceDescriptor:
    """Internal descriptor for a registered service."""

    __slots__ = ("dependencies", "factory", "instance", "lifecycle")

    def __init__(
        self,
        factory: Callable[..., Any],
        lifecycle: Lifecycle = Lifecycle.SINGLETON,
        dependencies: Optional[List[str]] = None,
    ):
        self.factory = factory
        self.lifecycle = lifecycle
        self.instance: Optional[Any] = None
        self.dependencies = dependencies or []


class Container:
    """
    Thread-safe dependency injection container.

    Supports singleton and transient lifecycles, keyed registries,
    override for testing, and dependency-ordered initialization.
    """

    def __init__(self) -> None:
        self._services: Dict[str, _ServiceDescriptor] = {}
        self._lock = threading.RLock()
        self._overrides: Dict[str, Any] = {}
        self._initializing: Set[str] = set()
        self._shutdown_hooks: List[Callable[[], None]] = []

    def register(
        self,
        name: str | Services,
        factory: Callable[..., Any],
        lifecycle: Lifecycle = Lifecycle.SINGLETON,
        dependencies: Optional[List[str | Services]] = None,
    ) -> None:
        """
        Register a service factory.

        Args:
            name: Service identifier (use Services enum).
            factory: Callable that creates the service instance.
                     Receives the container as first argument if it accepts one.
            lifecycle: SINGLETON (one instance) or TRANSIENT (new each time).
            dependencies: List of service names this service depends on.
                          Used for initialization ordering and cycle detection.
        """
        key = str(name)
        dep_keys = [str(d) for d in dependencies] if dependencies else []

        with self._lock:
            self._services[key] = _ServiceDescriptor(
                factory=factory,
                lifecycle=lifecycle,
                dependencies=dep_keys,
            )

    def resolve(self, name: str | Services) -> Any:
        """
        Resolve a service instance.

        For SINGLETON lifecycle: returns cached instance (creates on first call).
        For TRANSIENT lifecycle: creates a new instance each call.

        Raises:
            KeyError: If service is not registered.
            RuntimeError: If circular dependency detected.
        """
        key = str(name)

        # Check overrides first (no lock needed — overrides are set in test setup)
        if key in self._overrides:
            return self._overrides[key]

        with self._lock:
            if key not in self._services:
                raise KeyError(
                    f"Service '{key}' is not registered. "
                    f"Available: {list(self._services.keys())}"
                )

            descriptor = self._services[key]

            # Transient: always create new
            if descriptor.lifecycle == Lifecycle.TRANSIENT:
                return self._create_instance(key, descriptor)

            # Singleton: double-checked pattern
            if descriptor.instance is not None:
                return descriptor.instance

            instance = self._create_instance(key, descriptor)
            descriptor.instance = instance
            return instance

    def _create_instance(self, key: str, descriptor: _ServiceDescriptor) -> Any:
        """Create a service instance, detecting circular dependencies."""
        if key in self._initializing:
            cycle = " → ".join(self._initializing) + f" → {key}"
            raise RuntimeError(f"Circular dependency detected: {cycle}")

        self._initializing.add(key)
        try:
            # Resolve dependencies first
            for dep_key in descriptor.dependencies:
                if dep_key in self._services:
                    self.resolve(dep_key)

            # Decide from the callable signature; never reinterpret a TypeError
            # raised *inside* a factory as an argument mismatch and call it twice.
            try:
                inspect.signature(descriptor.factory).bind(self)
            except (TypeError, ValueError):
                return descriptor.factory()
            return descriptor.factory(self)
        finally:
            self._initializing.discard(key)

    def override(self, name: str | Services, instance: Any) -> None:
        """
        Override a service with a specific instance (for testing).

        Overrides take priority over registered factories.
        Call reset() to remove all overrides.
        """
        self._overrides[str(name)] = instance

    def reset(self, name: Optional[str | Services] = None) -> None:
        """
        Reset service instances and overrides.

        Args:
            name: If provided, reset only this service.
                  If None, reset ALL services and overrides.
        """
        with self._lock:
            if name is not None:
                key = str(name)
                self._overrides.pop(key, None)
                if key in self._services:
                    self._services[key].instance = None
            else:
                self._overrides.clear()
                for descriptor in self._services.values():
                    descriptor.instance = None

    def has(self, name: str | Services) -> bool:
        """Check if a service is registered."""
        return str(name) in self._services

    def is_resolved(self, name: str | Services) -> bool:
        """Check if a singleton service has been instantiated."""
        key = str(name)
        if key in self._overrides:
            return True
        if key in self._services:
            return self._services[key].instance is not None
        return False

    @property
    def registered(self) -> List[str]:
        """List all registered service names."""
        return list(self._services.keys())

    def register_shutdown_hook(self, hook: Callable[[], None]) -> None:
        """Register a callable to be invoked during shutdown."""
        self._shutdown_hooks.append(hook)

    def shutdown(self) -> None:
        """Run all shutdown hooks and clear instances."""
        for hook in reversed(self._shutdown_hooks):
            with contextlib.suppress(Exception):
                hook()  # Best-effort cleanup
        self._shutdown_hooks.clear()
        self.reset()


# ===========================================================================
# Global Container Instance
# ===========================================================================

_container = Container()


def get_container() -> Container:
    """Get the global DI container."""
    return _container


# ===========================================================================
# Convenience Functions (module-level API)
# ===========================================================================


def register(
    name: str | Services,
    factory: Callable[..., Any],
    lifecycle: Lifecycle = Lifecycle.SINGLETON,
    dependencies: Optional[List[str | Services]] = None,
) -> None:
    """Register a service in the global container."""
    _container.register(name, factory, lifecycle, dependencies)


def resolve(name: str | Services) -> Any:
    """Resolve a service from the global container."""
    return _container.resolve(name)


def override(name: str | Services, instance: Any) -> None:
    """Override a service in the global container (for testing)."""
    _container.override(name, instance)


def reset(name: Optional[str | Services] = None) -> None:
    """Reset the global container."""
    _container.reset(name)
