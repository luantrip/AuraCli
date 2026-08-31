"""
Aura Native Agent Integration — Lifecycle helpers for the ADK Framework.

This module provides standard entry points for instantiating and orchestrating
Native ADK Agents within the Core Infrastructure. It ensures consistent
initialization of agent contexts and configurations.
"""

from typing import Any, Optional

from aura_cli.application.agents import AgentConfig, AgentRegistry
from aura_cli.core.agents.adk_bridge import ADKAgentAdapter
from aura_cli.core.agents.adk_wrapper import ADKAgentWrapper
from aura_cli.core.agents.agent_base import AgentContext
from aura_cli.core.logger import get_logger

logger = get_logger(__name__)


def create_native_agent_wrapper(
    agent_type: str,
    agent_id: Optional[str] = None,
    model: Optional[str] = None,
    context: Optional[AgentContext] = None,
    memory_synchronizer: Any = None,
) -> ADKAgentWrapper:
    """
    Synthesizes a Native ADK Agent wrapper for the requested persona.

    Args:
        agent_type: Target persona ("code", "review", "refactor", "test", "ops").
        agent_id: Unique agent identifier.
        model: LLM model specification override.
        context: Active shared AgentContext for state persistence.

    Returns:
        ADKAgentWrapper initialized and ready for core orchestration.

    Raises:
        ValueError: If the agent_type persona is not registered.
        RuntimeError: If the Native Agent Registry is not initialized.
    """
    from aura_cli.adk.registry import ensure_adk_agents_registered
    from aura_cli.core.agents.adk_runtime import configure_core_agent_runtime

    configure_core_agent_runtime()
    ensure_adk_agents_registered()
    try:
        adk_agent = AgentRegistry.create(agent_type)
    except ValueError as exc:
        raise RuntimeError(
            "Native Agent Registry unavailable. Ensure the registry is preheated "
            "in the main thread before instantiation."
        ) from exc

    adapter = ADKAgentAdapter(adk_agent)
    agent_id = agent_id or f"{agent_type}_agent"
    config = AgentConfig(
        name=agent_id,
        role=f"Aura Native {agent_type.title()} Specialist",
        system_message=f"You are a native {agent_type} specialist operating within the Aura ecosystem.",
        llm_config={"model": model} if model else {},
    )

    adk_agent = adapter.create_assistant(config)
    wrapper = ADKAgentWrapper(
        adk_agent=adk_agent,
        agent_id=agent_id,
        model=model,
        context=context,
        memory_synchronizer=memory_synchronizer,
    )

    logger.info(f"Native Agent Wrapper materialized: {agent_type} (ID: {agent_id})")
    return wrapper


def create_adk_wrapper(
    agent_type: str,
    agent_id: Optional[str] = None,
    model: Optional[str] = None,
    context: Optional[AgentContext] = None,
    memory_synchronizer: Any = None,
) -> ADKAgentWrapper:
    """
    Create an ADKAgentWrapper for the given agent type.

    Convenience alias for create_native_agent_wrapper used by agi/factory.py
    and adk_bridge.py. Both names are canonical — prefer create_adk_wrapper
    for external callers, create_native_agent_wrapper for internal wiring.
    """
    return create_native_agent_wrapper(
        agent_type=agent_type,
        agent_id=agent_id,
        model=model,
        context=context,
        memory_synchronizer=memory_synchronizer,
    )


def is_native_adk_available() -> bool:
    """Validates the availability and initialization status of the Native ADK Framework."""
    try:
        from aura_cli.core.agents import is_adk_available as _check

        return _check()
    except Exception:
        return False
