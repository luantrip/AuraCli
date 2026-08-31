"""
Golden-path integration tests for the DI container and service pipeline.

These tests verify that the complete service resolution chain works correctly.
They serve as a SAFETY NET during the architectural refactoring — if these pass,
the core wiring is intact.

Tests are ordered from foundation to application-level:
1. Container mechanics (register, resolve, override, reset)
2. Foundation services (config, stats, event_bus)
3. LLM service chain (rate_limiter, circuit_breaker, task_router)
4. Memory services (memory_service_registry, notebook)
5. Tool registry (registration, resolution, execution)
6. Full pipeline (LLM mock → tool_calls → tool execution → result)
"""

import threading
from unittest.mock import MagicMock, Mock

import pytest

from aura_cli.core.di import Container, Lifecycle, Services, get_container, reset

# ===========================================================================
# Fixture: Fresh container for each test
# ===========================================================================


@pytest.fixture(autouse=True)
def fresh_container():
    """Reset the global container before and after each test."""
    reset()
    yield
    reset()


@pytest.fixture
def container():
    """Provide a fresh isolated container (not the global one)."""
    return Container()


# ===========================================================================
# 1. Container Mechanics
# ===========================================================================


class TestContainerMechanics:
    """Test the DI container itself."""

    def test_register_and_resolve_singleton(self, container):
        """Singleton factory is called once, same instance returned."""
        call_count = 0

        def factory():
            nonlocal call_count
            call_count += 1
            return {"value": 42}

        container.register("test_service", factory, Lifecycle.SINGLETON)

        result1 = container.resolve("test_service")
        result2 = container.resolve("test_service")

        assert result1 is result2
        assert result1["value"] == 42
        assert call_count == 1

    def test_register_and_resolve_transient(self, container):
        """Transient factory is called each time, different instances."""

        def factory():
            return {"value": 42}

        container.register("test_service", factory, Lifecycle.TRANSIENT)

        result1 = container.resolve("test_service")
        result2 = container.resolve("test_service")

        assert result1 is not result2
        assert result1 == result2

    def test_resolve_unknown_service_raises(self, container):
        """Resolving unregistered service raises KeyError."""
        with pytest.raises(KeyError, match="not registered"):
            container.resolve("nonexistent")

    def test_override_replaces_factory(self, container):
        """Override returns the provided instance instead of factory result."""
        container.register("svc", lambda: "real")
        container.override("svc", "mock")

        assert container.resolve("svc") == "mock"

    def test_reset_single_service(self, container):
        """Reset a specific service clears its instance."""
        container.register("svc", lambda: object())
        first = container.resolve("svc")
        container.reset("svc")
        second = container.resolve("svc")

        assert first is not second

    def test_reset_all(self, container):
        """Reset without args clears everything."""
        container.register("a", lambda: object())
        container.register("b", lambda: object())
        container.override("a", "override")

        container.resolve("b")
        container.reset()

        # Override should be gone
        assert container.resolve("a") != "override"
        # Instance should be fresh
        b1 = container.resolve("b")
        container.reset()
        b2 = container.resolve("b")
        assert b1 is not b2

    def test_circular_dependency_detected(self, container):
        """Circular dependencies raise RuntimeError."""
        container.register("a", lambda c: c.resolve("b"), dependencies=["b"])
        container.register("b", lambda c: c.resolve("a"), dependencies=["a"])

        with pytest.raises(RuntimeError, match="Circular dependency"):
            container.resolve("a")

    def test_dependency_ordering(self, container):
        """Dependencies are resolved before the dependent service."""
        order = []

        def factory_a():
            order.append("a")
            return "A"

        def factory_b(c):
            order.append("b")
            return f"B+{c.resolve('a')}"

        container.register("a", factory_a)
        container.register("b", factory_b, dependencies=["a"])

        result = container.resolve("b")
        assert result == "B+A"
        assert order == ["a", "b"]

    def test_thread_safety(self, container):
        """Concurrent resolution of the same singleton is safe."""
        call_count = 0
        lock = threading.Lock()

        def slow_factory():
            nonlocal call_count
            import time

            time.sleep(0.01)
            with lock:
                call_count += 1
            return object()

        container.register("slow", slow_factory)

        results = []
        threads = []
        for _ in range(10):
            t = threading.Thread(
                target=lambda: results.append(container.resolve("slow"))
            )
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        # All threads got the same instance
        assert all(r is results[0] for r in results)
        # Factory was called exactly once
        assert call_count == 1

    def test_services_enum_as_key(self, container):
        """Services enum values work as registration keys."""
        container.register(Services.CONFIG, lambda: {"model": "gemini"})
        result = container.resolve(Services.CONFIG)
        assert result["model"] == "gemini"

    def test_has_check(self, container):
        """has() returns correct registration status."""
        assert not container.has("svc")
        container.register("svc", lambda: None)
        assert container.has("svc")

    def test_is_resolved_check(self, container):
        """is_resolved() tracks instantiation state."""
        container.register("svc", lambda: object())
        assert not container.is_resolved("svc")
        container.resolve("svc")
        assert container.is_resolved("svc")

    def test_shutdown_hooks(self, container):
        """Shutdown hooks are called in reverse order."""
        order = []
        container.register_shutdown_hook(lambda: order.append(1))
        container.register_shutdown_hook(lambda: order.append(2))
        container.register_shutdown_hook(lambda: order.append(3))

        container.shutdown()
        assert order == [3, 2, 1]

    def test_factory_receives_container(self, container):
        """Factory can receive the container for resolving dependencies."""
        container.register("dep", lambda: 42)
        container.register("svc", lambda c: c.resolve("dep") * 2)

        assert container.resolve("svc") == 84

    def test_internal_type_error_is_not_retried_without_container(self, container):
        """A factory bug must propagate without executing the factory twice."""
        factory = Mock(side_effect=TypeError("internal bug"))
        container.register("broken", factory)

        with pytest.raises(TypeError, match="internal bug"):
            container.resolve("broken")

        factory.assert_called_once_with(container)


# ===========================================================================
# 2. Foundation Services
# ===========================================================================


class TestFoundationServices:
    """Test that foundation services can be bootstrapped and resolved."""

    def test_bootstrap_registers_all_services(self):
        """bootstrap_services() registers all expected services."""
        from aura_cli.core.di_bootstrap import bootstrap_services

        container = get_container()
        bootstrap_services()

        # Check core services are registered
        assert container.has(Services.CONFIG)
        assert container.has(Services.STATS)
        assert container.has(Services.EVENT_BUS)
        assert container.has(Services.RATE_LIMITER)
        assert container.has(Services.TOOL_REGISTRY)
        assert container.has(Services.MEMORY_SERVICE_REGISTRY)

    def test_bootstrap_is_idempotent(self):
        """Calling bootstrap twice doesn't double-register."""
        from aura_cli.core.di_bootstrap import bootstrap_services

        bootstrap_services()
        bootstrap_services()  # Should not raise

        container = get_container()
        assert container.has(Services.CONFIG)

    def test_every_registered_factory_resolves(self, tmp_path, monkeypatch):
        """The production composition graph has no broken factory contracts."""
        from aura_cli.core.di_bootstrap import bootstrap_services

        monkeypatch.chdir(tmp_path)
        bootstrap_services()
        container = get_container()

        resolved = {name: container.resolve(name) for name in container.registered}

        assert len(resolved) == 24
        assert all(service is not None for service in resolved.values())

    def test_unregistered_services_are_explicitly_known(self):
        """Guard the gap between the Services enum and what bootstrap registers.

        The Services enum documents intended service identifiers, but not all of
        them are wired into bootstrap_services() yet. Resolving an unregistered
        service raises KeyError, so we pin the exact set of not-yet-registered
        members here: adding a new enum value without a factory (or registering a
        previously-missing one) must update this list deliberately, preventing a
        silent runtime KeyError from creeping in.
        """
        from aura_cli.core.di_bootstrap import bootstrap_services

        bootstrap_services()
        container = get_container()

        registered = {str(name) for name in container.registered}
        enum_keys = {str(member) for member in Services}
        not_registered = enum_keys - registered

        expected_not_registered = {
            "Services.AGENT_COMMUNICATION",
            "Services.AGENT_FACTORY",
            "Services.AGENT_ORCHESTRATOR",
            "Services.COGNITIVE_REFINER",
            "Services.LLM_CLIENT",
            "Services.LOGGER_FACTORY",
            "Services.MODEL_PROFILES",
            "Services.PROJECT_INDEXER",
            "Services.VECTOR_STORE_FACTORY",
        }
        assert not_registered == expected_not_registered

        # Each unregistered service must fail loudly (never resolve to a bad value).
        for key in not_registered:
            member = next(m for m in Services if str(m) == key)
            with pytest.raises(KeyError):
                container.resolve(member)

    def test_config_resolves(self):
        """Config service resolves to a valid config manager."""
        from aura_cli.core.di_bootstrap import bootstrap_services

        bootstrap_services()
        config = get_container().resolve(Services.CONFIG)

        assert config is not None
        assert hasattr(config, "get")

    def test_stats_resolves(self):
        """Stats service resolves to a StatsTracker."""
        from aura_cli.core.di_bootstrap import bootstrap_services

        bootstrap_services()
        stats = get_container().resolve(Services.STATS)

        assert stats is not None
        assert hasattr(stats, "track_tool_usage")

    def test_event_bus_resolves(self):
        """EventBus resolves and supports subscribe/publish."""
        from aura_cli.core.di_bootstrap import bootstrap_services

        bootstrap_services()
        bus = get_container().resolve(Services.EVENT_BUS)

        assert bus is not None
        assert hasattr(bus, "subscribe")
        assert hasattr(bus, "publish")


# ===========================================================================
# 3. LLM Services
# ===========================================================================


class TestLLMServices:
    """Test LLM service resolution and keyed registries."""

    def test_rate_limiter_resolves(self):
        """RateLimiter resolves as singleton."""
        from aura_cli.core.di_bootstrap import bootstrap_services

        bootstrap_services()
        container = get_container()

        rl1 = container.resolve(Services.RATE_LIMITER)
        rl2 = container.resolve(Services.RATE_LIMITER)

        assert rl1 is rl2
        assert hasattr(rl1, "wait_if_needed") or hasattr(rl1, "acquire")

    def test_circuit_breaker_registry_per_provider(self):
        """CircuitBreakerRegistry provides per-provider instances."""
        from aura_cli.core.di_bootstrap import bootstrap_services

        bootstrap_services()
        registry = get_container().resolve(Services.CIRCUIT_BREAKER_REGISTRY)

        cb_google = registry.get("google")
        cb_openai = registry.get("openai")
        cb_google2 = registry.get("google")

        assert cb_google is not cb_openai
        assert cb_google is cb_google2

    def test_task_router_resolves(self):
        """TaskRouter resolves as singleton."""
        from aura_cli.core.di_bootstrap import bootstrap_services

        bootstrap_services()
        router = get_container().resolve(Services.TASK_ROUTER)

        assert router is not None
        assert hasattr(router, "route") or hasattr(router, "classify")


# ===========================================================================
# 4. Memory Services
# ===========================================================================


class TestMemoryServices:
    """Test memory service resolution."""

    def test_memory_service_registry_per_project(self, tmp_path):
        """MemoryServiceRegistry provides per-project instances."""
        from aura_cli.core.di_bootstrap import bootstrap_services

        bootstrap_services()
        registry = get_container().resolve(Services.MEMORY_SERVICE_REGISTRY)

        project_a = tmp_path / "project_a"
        project_a.mkdir()
        project_b = tmp_path / "project_b"
        project_b.mkdir()

        ms_a = registry.get(project_a)
        ms_b = registry.get(project_b)
        ms_a2 = registry.get(project_a)

        assert ms_a is not ms_b
        assert ms_a is ms_a2


# ===========================================================================
# 5. Override for Testing
# ===========================================================================


class TestOverridePatterns:
    """Test that services can be properly overridden for testing."""

    def test_override_config(self):
        """Config can be overridden with a mock."""
        from aura_cli.core.di_bootstrap import bootstrap_services

        bootstrap_services()
        container = get_container()

        mock_config = MagicMock()
        mock_config.get.return_value = "test_value"

        container.override(Services.CONFIG, mock_config)

        config = container.resolve(Services.CONFIG)
        assert config.get("anything") == "test_value"

    def test_override_reset_restores_real(self):
        """After reset, real factory is used again."""
        from aura_cli.core.di_bootstrap import bootstrap_services

        bootstrap_services()
        container = get_container()

        container.override(Services.STATS, "fake")
        assert container.resolve(Services.STATS) == "fake"

        container.reset(Services.STATS)
        stats = container.resolve(Services.STATS)
        assert stats != "fake"
        assert hasattr(stats, "track_tool_usage")


# ===========================================================================
# 6. Full Pipeline (Golden Path)
# ===========================================================================


class TestGoldenPathPipeline:
    """
    Test the complete pipeline: service resolution → tool execution.

    These tests verify that the DI wiring correctly connects:
    container → tool_registry → tool resolution → tool execution → result
    """

    def test_tool_registry_resolves_and_has_tools(self):
        """ToolRegistry resolves and contains registered tools."""
        from aura_cli.core.di_bootstrap import bootstrap_services

        bootstrap_services()
        registry = get_container().resolve(Services.TOOL_REGISTRY)

        assert registry is not None
        # Should have tools registered after bootstrap
        tools = registry.get_all_tools()
        assert len(tools) > 0

    def test_tool_execution_via_registry(self, tmp_path):
        """A tool can be executed through the registry."""
        from aura_cli.core.di_bootstrap import bootstrap_services

        bootstrap_services()
        registry = get_container().resolve(Services.TOOL_REGISTRY)

        # Create a test file to read
        test_file = tmp_path / "test.txt"
        test_file.write_text("hello world")

        # The read_file tool should be registered
        if registry.get_tool("read_file"):
            result = registry.execute_tool("read_file", {"path": str(test_file)})
            assert "hello world" in str(result)
