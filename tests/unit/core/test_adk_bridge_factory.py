"""Testes para ADKBridgeFactory — TEST-NEW-06."""

from unittest.mock import MagicMock

import pytest

from aura_cli.core.agents.adk_bridge import ADKAgentAdapter, ADKBridgeFactory


class _FakeAgent:
    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.config = MagicMock()
        self.config.name = "fake-agent"

    def run(self, prompt):
        return f"result:{prompt}"


class TestADKBridgeFactory:
    def setup_method(self):
        # Clean registry before each test
        ADKBridgeFactory._registry.clear()

    def test_register_adds_to_registry(self):
        ADKBridgeFactory.register("fake", _FakeAgent)
        assert "fake" in ADKBridgeFactory.list_registered()

    def test_list_registered_empty(self):
        assert ADKBridgeFactory.list_registered() == []

    def test_list_registered_after_register(self):
        ADKBridgeFactory.register("a", _FakeAgent)
        ADKBridgeFactory.register("b", _FakeAgent)
        names = ADKBridgeFactory.list_registered()
        assert "a" in names and "b" in names

    def test_create_adapter_returns_adapter(self):
        ADKBridgeFactory.register("fake", _FakeAgent)
        adapter = ADKBridgeFactory.create_adapter("fake")
        assert isinstance(adapter, ADKAgentAdapter)

    def test_create_adapter_unknown_raises_value_error(self):
        with pytest.raises(ValueError, match="não registrado"):
            ADKBridgeFactory.create_adapter("nonexistent")

    def test_create_adapter_passes_kwargs(self):
        ADKBridgeFactory.register("fake", _FakeAgent)
        adapter = ADKBridgeFactory.create_adapter("fake", foo="bar")
        assert adapter.adk_agent.kwargs.get("foo") == "bar"

    def test_register_overwrites_existing(self):
        class AgentV1:
            def __init__(self, **kw):
                self.config = MagicMock()
                self.config.name = "v1"

        class AgentV2:
            def __init__(self, **kw):
                self.config = MagicMock()
                self.config.name = "v2"

        ADKBridgeFactory.register("agent", AgentV1)
        ADKBridgeFactory.register("agent", AgentV2)
        adapter = ADKBridgeFactory.create_adapter("agent")
        assert isinstance(adapter.adk_agent, AgentV2)

    def test_ensure_registered_no_crash(self):
        ADKBridgeFactory.ensure_registered()  # must not raise
