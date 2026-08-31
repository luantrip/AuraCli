"""Tests for the neutral application agent registry."""

import pytest

from aura_cli.application.agents import AgentRegistry


class ExampleAgent:
    def __init__(self, value: int = 0) -> None:
        self.value = value


def test_registry_creates_registered_agent() -> None:
    AgentRegistry.clear()
    AgentRegistry.register("example", ExampleAgent)

    agent = AgentRegistry.create("example", value=7)

    assert isinstance(agent, ExampleAgent)
    assert agent.value == 7


def test_registry_rejects_unknown_agent() -> None:
    AgentRegistry.clear()
    with pytest.raises(ValueError, match="not registered"):
        AgentRegistry.create("missing")
