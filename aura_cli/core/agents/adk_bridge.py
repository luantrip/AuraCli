"""Translate public ADK agents into Core execution contracts.

``ADKConfigAdapter`` and ``ADKResponseAdapter`` translate schemas,
``ADKAgentAdapter`` implements the conversational Core backend, and
``ADKBridgeFactory`` registers adapters in the application agent registry.
Lifecycle construction remains in ``adk_integration``; the synchronous
``AgentBase`` boundary remains isolated in ``adk_wrapper``.
"""

from __future__ import annotations

import logging
import threading
from typing import TYPE_CHECKING, Any, ClassVar, Dict, List

if TYPE_CHECKING:
    from aura_cli.adk import Agent
    from aura_cli.adk import AgentConfig as ADKConfig
    from aura_cli.adk import AgentResponse as ADKResponse

from aura_cli.application.agents import AgentRegistry
from aura_cli.core.agents.interface import AgentBackend
from aura_cli.core.agents.interface import AgentConfig as CoreConfig
from aura_cli.core.agents.interface import AgentResponse as CoreResponse

logger = logging.getLogger(__name__)


def _get_adk_agent():
    """Lazily import and return the ADK agent class."""
    from aura_cli.adk import Agent

    return Agent


def _get_adk_config():
    """Lazily import and return the ADK config class."""
    from aura_cli.adk import AgentConfig

    return AgentConfig


def _get_adk_response():
    """Lazily import and return the ADK response class."""
    from aura_cli.adk import AgentResponse

    return AgentResponse


class ADKConfigAdapter:
    """Translates configuration schemas between ADK and Core formats."""

    @staticmethod
    def to_core(adk_config: ADKConfig) -> CoreConfig:
        """Converts ADK config to Core config."""
        return CoreConfig(
            name=adk_config.name,
            role=adk_config.description or "assistant",
            system_message=adk_config.system_prompt,
            llm_config={
                "model": adk_config.model,
                "temperature": adk_config.temperature,
                "max_tokens": adk_config.max_tokens,
            },
            tools=[],
            max_consecutive_auto_reply=adk_config.max_iterations,
            human_input_mode="NEVER",
        )

    @staticmethod
    def from_core(core_config: CoreConfig) -> ADKConfig:
        """Converts Core config to ADK config."""
        ADKConfig = _get_adk_config()
        llm_config = core_config.llm_config or {}
        return ADKConfig(
            name=core_config.name,
            description=core_config.role,
            system_prompt=core_config.system_message,
            model=llm_config.get("model", "gpt-4o"),
            temperature=llm_config.get("temperature", 0.7),
            max_tokens=llm_config.get("max_tokens", 4096),
            max_iterations=core_config.max_consecutive_auto_reply,
        )

    # Aliases removed — use to_core / from_core directly.


class ADKResponseAdapter:
    """Translates response envelopes between ADK and Core formats."""

    @staticmethod
    def to_core(adk_response: ADKResponse) -> CoreResponse:
        """Converts ADK response to Core response."""
        return CoreResponse(
            content=adk_response.content,
            metadata=adk_response.metadata,
            success=adk_response.success,
            error=adk_response.error,
        )

    @staticmethod
    def from_core(core_response: CoreResponse) -> ADKResponse:
        """Converts Core response to ADK response."""
        ADKResponse = _get_adk_response()
        return ADKResponse(
            content=core_response.content,
            metadata=core_response.metadata,
            success=core_response.success,
            error=core_response.error,
        )

    # Aliases removed — use to_core / from_core directly.


class ADKAgentAdapter(AgentBackend):
    """
    Adapter that executes ADK Agents within the Core Service Architecture.

    Implements AgentBackend so ADK agents can be used by AgiExecutionEngine
    and other core components without modification.
    """

    def __init__(self, adk_agent: Agent):
        """Initialize the widget."""
        self.adk_agent = adk_agent
        self._assistant: Any = None
        self._user_proxy: Any = None
        logger.info(f"ADKAgentAdapter initialized for: {adk_agent.config.name}")

    def create_assistant(self, config: CoreConfig) -> Any:
        """Create an ADK assistant agent instance."""
        self.adk_agent.config = config
        self._assistant = self.adk_agent
        logger.debug(f"ADK assistant configured: {config.name}")
        return self.adk_agent

    def create_user_proxy(self, config: CoreConfig) -> Any:
        """Create an ADK user proxy agent instance."""
        self._user_proxy = {"name": config.name, "role": "user"}
        return self._user_proxy

    async def execute_conversation(
        self, assistant: Any, user_proxy: Any, message: str
    ) -> CoreResponse:
        """Execute a multi-turn conversation via ADK."""
        try:
            logger.debug(f"Executing ADK agent: {message[:50]}...")
            adk_response = await self.adk_agent.execute(message)
            return adk_response
        except Exception as e:
            logger.error(f"ADK execution error: {e}", exc_info=True)
            return CoreResponse(
                content="",
                metadata={"error": str(e)},
                success=False,
                error=str(e),
            )

    def get_backend_name(self) -> str:
        """Return the backend identifier string."""
        return f"ADK:{self.adk_agent.config.name}"


class ADKBridgeFactory:
    """
    Registry and factory for ADK agent adapters.

    Maintains a registry of specialized ADK agents and provides
    unified access for core service consumption.
    """

    _registry: ClassVar[Dict[str, type]] = {}

    @classmethod
    def register(cls, name: str, agent_class: type) -> None:
        """Register an ADK agent class by name."""
        cls._registry[name] = agent_class
        AgentRegistry.register(name, agent_class)
        logger.info(f"ADK agent registered: {name}")

    @classmethod
    def create_adapter(cls, name: str, **kwargs) -> ADKAgentAdapter:
        """
        Create an ADKAgentAdapter for the named agent.

        Args:
            name: Registered agent name.
            **kwargs: Passed to the agent constructor.

        Returns:
            ADKAgentAdapter ready for use.

        Raises:
            ValueError: If agent name is not registered.
            RuntimeError: If called from a worker thread before main-thread init.
        """
        if threading.current_thread() is threading.main_thread():
            _ensure_registry()
        elif not _registry_ready and name not in cls._registry:
            raise RuntimeError(
                f"ADK agent '{name}' not available in worker thread. "
                "Call ADKBridgeFactory.ensure_registered() from the main thread first."
            )

        if name not in cls._registry:
            raise ValueError(
                f"ADK agent '{name}' não registrado. "
                f"Disponíveis: {list(cls._registry.keys())}"
            )

        agent = cls._registry[name](**kwargs)
        return ADKAgentAdapter(agent)

    @classmethod
    def ensure_registered(cls) -> None:
        """Pre-heat the registry. Call from main thread before starting workers."""
        _ensure_registry()

    @classmethod
    def list_registered(cls) -> List[str]:
        """Return list of registered agent names."""
        return list(cls._registry.keys())


_registry_ready = False
_registry_lock = threading.Lock()


def _ensure_registry() -> None:
    """Bootstrap the ADK agent registry. Must be called from the main thread."""
    global _registry_ready

    with _registry_lock:
        if _registry_ready:
            return

        if threading.current_thread() is not threading.main_thread():
            logger.debug("ADK registry init deferred — not in main thread")
            return

        try:
            from aura_cli.adk.registry import ensure_adk_agents_registered
            from aura_cli.core.agents.adk_runtime import configure_core_agent_runtime

            configure_core_agent_runtime()
            ensure_adk_agents_registered()
            for name in AgentRegistry.names():
                ADKBridgeFactory._registry[name] = AgentRegistry.get(name)

            logger.info("ADK agent registry initialized")
            _registry_ready = True
        except ImportError as e:
            logger.warning(f"Could not initialize ADK registry: {e}")
        except Exception as e:
            logger.error(f"ADK registry initialization error: {e}", exc_info=True)


try:
    from aura_cli.core.agents.adk_integration import (
        create_adk_wrapper,
    )
    from aura_cli.core.agents.adk_wrapper import ADKAgentWrapper
except ImportError:
    ADKAgentWrapper = None  # type: ignore[assignment,misc]
    create_adk_wrapper = None  # type: ignore[assignment]

__all__ = [
    "ADKAgentAdapter",
    "ADKAgentWrapper",
    "ADKBridgeFactory",
    "ADKConfigAdapter",
    "ADKResponseAdapter",
    "create_adk_wrapper",
]
