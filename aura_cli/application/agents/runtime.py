"""Host-provided runtime services consumed by agent implementations."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Optional, Sequence


@dataclass(frozen=True)
class AgentRuntimeServices:
    """Minimal capabilities required by specialized application agents."""

    query_llm: Callable[..., Any]
    load_persona: Callable[[str], Any]
    build_tool_schemas: Callable[[Sequence[str]], list[dict[str, Any]]]
    recall_memory: Optional[Callable[[str, int], list[dict[str, Any]]]] = None
    create_vector_store: Optional[Callable[[str, Optional[str]], Any]] = None


_runtime: Optional[AgentRuntimeServices] = None


def configure_agent_runtime(runtime: Optional[AgentRuntimeServices]) -> None:
    """Install services supplied by the process composition root."""
    global _runtime
    _runtime = runtime


def get_agent_runtime() -> AgentRuntimeServices:
    """Return configured services or fail explicitly in an uncomposed host."""
    if _runtime is None:
        raise RuntimeError("Agent runtime services have not been configured")
    return _runtime
