"""
Factory for creating agent backends.

Allows switching backend via configuration without modifying code.
The "native" backend is recommended as it has no external dependencies.

Usage:
    >>> from aura_cli.core.agents.factory import AgentBackendFactory
    >>> backend = AgentBackendFactory.create("native")
"""

from typing import ClassVar, Optional

from .interface import AgentBackend
from .native_backend import NativeBackend


class AgentBackendFactory:
    """
    Factory for creating agent backends.

    Supports multiple backends with "native" as default.

    Example:
        >>> backend = AgentBackendFactory.create()
        >>> backend = AgentBackendFactory.create("native")
    """

    _backends: ClassVar[dict] = {
        "native": NativeBackend,
    }

    _default_backend = "native"

    @classmethod
    def create(cls, backend_name: Optional[str] = None) -> AgentBackend:
        """
        Create an agent backend.

        Args:
            backend_name: Backend name ("native", etc.)
                         If None, uses default.

        Returns:
            AgentBackend instance

        Example:
            >>> backend = AgentBackendFactory.create("native")
        """
        name = backend_name or cls._default_backend

        if name not in cls._backends:
            available = ", ".join(cls._backends.keys())
            raise ValueError(
                f"Backend '{name}' not found. Available: {available}"
            )

        backend_class = cls._backends[name]
        return backend_class()

    @classmethod
    def register_backend(cls, name: str, backend_class: type):
        """Register a new backend."""
        cls._backends[name] = backend_class

    @classmethod
    def set_default_backend(cls, name: str):
        """Set the default backend."""
        if name not in cls._backends:
            raise ValueError(f"Backend '{name}' não registrado")
        cls._default_backend = name

    @classmethod
    def list_backends(cls) -> list:
        """Return a list of available backends."""
        return list(cls._backends.keys())
