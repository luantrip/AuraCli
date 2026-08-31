"""Composition adapter connecting ADK agents to Core infrastructure."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from aura_cli.application.agents import (
    AgentRuntimeServices,
    configure_agent_runtime,
)


def _build_tool_schemas(tool_names: Sequence[str]) -> list[dict[str, Any]]:
    from aura_cli.core.llm.tool_schemas import create_tool_schemas
    from aura_cli.core.service_registry import get_tools_dict

    available = get_tools_dict()
    selected = [available[name] for name in tool_names if name in available]
    return create_tool_schemas(selected) if selected else []  # type: ignore[arg-type]


def configure_core_agent_runtime() -> None:
    """Install Core implementations behind the neutral agent runtime contract."""
    from aura_cli.core.llm.base import query_with_fallback
    from aura_cli.core.memory.memory_service import get_memory_service
    from aura_cli.core.memory.vector_store import create_vector_store
    from aura_cli.core.personas.agent_runner import get_agent_runner

    def load_persona(name: str) -> Any:
        return get_agent_runner().get_agent(name)

    def recall_memory(query: str, limit: int) -> list[dict[str, Any]]:
        return get_memory_service().recall(query, limit)

    configure_agent_runtime(
        AgentRuntimeServices(
            query_llm=query_with_fallback,
            load_persona=load_persona,
            build_tool_schemas=_build_tool_schemas,
            recall_memory=recall_memory,
            create_vector_store=create_vector_store,
        )
    )
