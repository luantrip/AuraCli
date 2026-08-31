"""Thread-safe registry for agent implementations supplied by adapters."""

from __future__ import annotations

import threading
from typing import Any, ClassVar


class AgentRegistry:
    """Store agent classes without depending on ADK or Core implementations."""

    _agents: ClassVar[dict[str, type]] = {}
    _lock: ClassVar[threading.RLock] = threading.RLock()

    @classmethod
    def register(cls, name: str, agent_class: type) -> None:
        if not name or not isinstance(name, str):
            raise ValueError("Agent name must be a non-empty string")
        if not isinstance(agent_class, type):
            raise TypeError("Agent implementation must be a class")
        with cls._lock:
            cls._agents[name] = agent_class

    @classmethod
    def create(cls, name: str, **kwargs: Any) -> Any:
        return cls.get(name)(**kwargs)

    @classmethod
    def get(cls, name: str) -> type:
        """Return a registered implementation without instantiating it."""
        with cls._lock:
            agent_class = cls._agents.get(name)
            available = sorted(cls._agents)
        if agent_class is None:
            raise ValueError(f"Agent '{name}' not registered. Available: {available}")
        return agent_class

    @classmethod
    def names(cls) -> list[str]:
        with cls._lock:
            return sorted(cls._agents)

    @classmethod
    def clear(cls) -> None:
        with cls._lock:
            cls._agents.clear()
