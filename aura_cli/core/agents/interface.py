"""
Abstract Interface for Agent Backends.

Defines the contract that all agent backend implementations must follow,
allowing the execution engine to work with any backend transparently.
"""

from abc import ABC, abstractmethod
from typing import Any

from aura_cli.application.agents import AgentConfig, AgentResponse


class AgentBackend(ABC):
    """
    Abstract interface for agent backends.

    Defines the contract that all agent backend implementations must follow.
    """

    @abstractmethod
    def create_assistant(self, config: AgentConfig) -> Any:
        """
        Create an assistant agent.

        Args:
            config: Agent configuration

        Returns:
            Agent instance
        """

    @abstractmethod
    def create_user_proxy(self, config: AgentConfig) -> Any:
        """
        Create a user proxy agent.

        Args:
            config: Proxy configuration

        Returns:
            Proxy instance
        """

    @abstractmethod
    async def execute_conversation(
        self, assistant: Any, user_proxy: Any, message: str
    ) -> AgentResponse:
        """
        Execute a conversation between agent and user.

        Args:
            assistant: Assistant agent
            user_proxy: User proxy
            message: Initial message

        Returns:
            Conversation response
        """

    @abstractmethod
    def get_backend_name(self) -> str:
        """
        Get backend name.

        Returns:
            Backend identifier string
        """
