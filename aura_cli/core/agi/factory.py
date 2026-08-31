"""
AgiAgentFactory — Creates and registers specialised agents for the AGI system.

Uses ADKAgentWrapper when available, falling back to native specialised agents
if ADK is unavailable. Enriches agents with consciousness skills and personas.
"""

import importlib
import logging
from typing import Any, Optional

from aura_cli.core.ui_bridge import UIIcons

logger = logging.getLogger(__name__)

# ADK agent type → (legacy_module, legacy_class) for fallback
_AGENT_SPECS = [
    (
        "code",
        "code_agent",
        "aura_cli.core.agents.specialized_agents.code_agent",
        "CodeAgent",
    ),
    (
        "review",
        "review_agent",
        "aura_cli.core.agents.specialized_agents.review_agent",
        "ReviewAgent",
    ),
    (
        "refactor",
        "refactor_agent",
        "aura_cli.core.agents.specialized_agents.refactor_agent",
        "RefactorAgent",
    ),
    (
        "test",
        "test_agent",
        "aura_cli.core.agents.specialized_agents.test_agent",
        "TestAgent",
    ),
]


def _create_agent(
    adk_type: str,
    agent_id: str,
    fallback_module: str,
    fallback_class: str,
    model: Optional[str] = None,
    context: Any = None,
    use_adk: bool = True,
    memory_synchronizer: Any = None,
) -> Any:
    """
    Create an agent preferring ADKAgentWrapper with native fallback.

    Returns the agent instance ready for orchestrator registration.
    """
    if use_adk:
        try:
            from aura_cli.core.agents.adk_integration import (
                create_adk_wrapper,
            )

            wrapper = create_adk_wrapper(
                agent_type=adk_type,
                agent_id=agent_id,
                model=model,
                context=context,
                memory_synchronizer=memory_synchronizer,
            )
            logger.debug(f"ADK wrapper created for {agent_id}")
            return wrapper
        except Exception as adk_err:
            logger.debug(
                f"ADK unavailable for {agent_id}: {adk_err}, using native agent"
            )

    mod = importlib.import_module(fallback_module)
    return getattr(mod, fallback_class)(agent_id=agent_id)


class AgiAgentFactory:
    """
    Factory for creating and configuring specialised agents for the AGI system.
    """

    def __init__(
        self,
        orchestrator: Any,
        communication_manager: Any,
        agi_event_adapter: Any,
        consciousness_manager: Any = None,
        model: Optional[str] = None,
        agent_memory: Any = None,
        use_adk: bool = True,
        memory_synchronizer: Any = None,
    ):
        """Initialize the instance."""
        self.orchestrator = orchestrator
        self.communication_manager = communication_manager
        self.agi_event_adapter = agi_event_adapter
        self.consciousness_manager = consciousness_manager
        self.model = model
        self.agent_memory = agent_memory
        self.use_adk = use_adk
        self.memory_synchronizer = memory_synchronizer

    def create_specialized_agents(self, prompt: str) -> None:
        """
        Create and register specialised agents in the orchestrator.

        Uses ADKAgentWrapper when available (migration path from native agents).
        Falls back to legacy agents if ADK is not available.
        Enriches agents with the consciousness manager when present.
        """
        try:
            if self.agent_memory:
                try:
                    if self.memory_synchronizer is not None:
                        self.memory_synchronizer.set_agent_memory(self.agent_memory)
                except Exception as bridge_error:
                    logger.debug(
                        f"Could not initialize memory bridge for AGI agents: {bridge_error}"
                    )

            for adk_type, agent_id, fallback_module, fallback_class in _AGENT_SPECS:
                agent = _create_agent(
                    adk_type,
                    agent_id,
                    fallback_module,
                    fallback_class,
                    model=self.model,
                    context=getattr(self.orchestrator, "context", None),
                    use_adk=self.use_adk,
                    memory_synchronizer=self.memory_synchronizer,
                )

                # Attach orchestrator context if available
                if hasattr(agent, "context") and hasattr(self.orchestrator, "context"):
                    agent.context = self.orchestrator.context

                # Consciousness enhancement (works for both ADK and legacy)
                if self.consciousness_manager:
                    try:
                        enhancement = (
                            self.consciousness_manager.enhance_specialized_agent(
                                adk_type, prompt
                            )
                        )
                        if enhancement.get("persona_config"):
                            agent.consciousness_persona = enhancement["persona_config"]
                        if enhancement.get("relevant_skills"):
                            agent.consciousness_skills = enhancement["relevant_skills"]
                    except Exception as _e:
                        pass  # silenced: {_e}

                if self.communication_manager:
                    self.communication_manager.register_agent(agent_id, "main_channel")

                if self.agent_memory:
                    memories = self.agent_memory.retrieve(agent_id, limit=10)
                    logger.debug(
                        f"Loaded {len(memories)} memories for specialized AGI agent {agent_id}"
                    )

                self.orchestrator.register_agent(agent)

            consciousness_status = (
                "com consciência ativa"
                if self.consciousness_manager
                else "sem consciência"
            )
            self.agi_event_adapter.emit_chat_message(
                sender="agent",
                content=(
                    f"› [Aura AGI] {UIIcons.SUCCESS} "
                    f"{len(self.orchestrator.agents)} agentes especializados registrados "
                    f"({consciousness_status})"
                ),
            )

        except (ImportError, AttributeError, TypeError) as e:
            logger.error(f"Error creating specialized agents: {e}", exc_info=True)
        except Exception as e:
            logger.error(
                f"Unexpected error creating specialized agents: {e}", exc_info=True
            )
            self.agi_event_adapter.emit_chat_message(
                sender="agent",
                content=f"› [Aura AGI] {UIIcons.WARNING} Some specialized agents could not be created",
            )
