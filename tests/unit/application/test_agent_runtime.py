"""Tests for host-provided specialized-agent runtime services."""

import pytest

from aura_cli.adk.memory import ConversationMemory as AdkConversationMemory
from aura_cli.adk.memory import VectorMemory
from aura_cli.adk.specialized import CodeAgent
from aura_cli.application import agents as agents_package
from aura_cli.application.agents import (
    AgentConfig,
    AgentRuntimeServices,
    configure_agent_runtime,
    get_agent_runtime,
)
from aura_cli.application.agents import runtime as runtime_module
from aura_cli.application.workspace import ConversationMemory
from aura_cli.core.memory import ConversationMemory as CoreConversationMemory


@pytest.fixture(autouse=True)
def restore_agent_runtime():
    original = runtime_module._runtime
    yield
    configure_agent_runtime(original)


def test_uncomposed_agent_runtime_fails_explicitly() -> None:
    configure_agent_runtime(None)

    with pytest.raises(RuntimeError, match="not been configured"):
        get_agent_runtime()


@pytest.mark.asyncio
async def test_specialized_agent_uses_injected_llm_and_tool_services() -> None:
    calls = []

    def query_llm(**kwargs):
        calls.append(("query", kwargs))
        return "generated"

    configure_agent_runtime(
        AgentRuntimeServices(
            query_llm=query_llm,
            load_persona=lambda name: None,
            build_tool_schemas=lambda names: (
                calls.append(("tools", list(names))) or [{"type": "function"}]
            ),
        )
    )
    agent = CodeAgent(
        AgentConfig(
            name="code",
            tools=["read_file"],
            memory_enabled=False,
        )
    )

    result = await agent._execute_llm("inspect")

    assert result == "generated"
    assert calls[0] == ("tools", ["read_file"])
    assert calls[1][0] == "query"
    assert calls[1][1]["tools"] == [{"type": "function"}]


def test_runtime_contract_is_exported_from_agents_package() -> None:
    assert agents_package.AgentRuntimeServices is AgentRuntimeServices


def test_conversation_memory_has_one_canonical_model() -> None:
    assert CoreConversationMemory is ConversationMemory
    assert issubclass(AdkConversationMemory, ConversationMemory)


@pytest.mark.asyncio
async def test_vector_memory_uses_host_store_factory() -> None:
    class Store:
        backend_name = "fake"

        def add(self, content, metadata):
            return "entry-1"

    configure_agent_runtime(
        AgentRuntimeServices(
            query_llm=lambda **kwargs: "",
            load_persona=lambda name: None,
            build_tool_schemas=lambda names: [],
            create_vector_store=lambda collection, path: Store(),
        )
    )

    memory = VectorMemory("test")

    assert await memory.add("content") == "entry-1"


@pytest.mark.asyncio
async def test_agent_recall_uses_host_memory_port() -> None:
    configure_agent_runtime(
        AgentRuntimeServices(
            query_llm=lambda **kwargs: "",
            load_persona=lambda name: None,
            build_tool_schemas=lambda names: [],
            recall_memory=lambda query, limit: [
                {"id": "remote-1", "content": query, "metadata": {"source": "host"}}
            ],
        )
    )
    agent = CodeAgent(AgentConfig(name="code", memory_enabled=False))

    results = await agent.recall("needle", limit=2)

    assert [(item.id, item.content) for item in results] == [("remote-1", "needle")]
