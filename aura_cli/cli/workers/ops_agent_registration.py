"""Concrete ADK/native registration adapter for the Ops specialist team."""

from __future__ import annotations

from dataclasses import dataclass
import logging
from typing import Any

from aura_cli.application.agents.ops_execution import OpsAgentSpec, get_ops_agent_specs


@dataclass(frozen=True)
class OpsAgentRegistrationOutcome:
    backend: str
    agent_ids: tuple[str, ...]
    adk_fallback_error: str | None = None


def _connect_agent(
    agent: Any,
    spec: OpsAgentSpec,
    *,
    orchestrator: Any,
    communication_manager: Any,
    agent_memory: Any,
    logger: logging.Logger,
) -> None:
    if communication_manager:
        communication_manager.register_agent(spec.agent_id, spec.channel_id)
    if agent_memory:
        memories = agent_memory.retrieve(spec.agent_id, limit=spec.memory_limit)
        logger.debug("Loaded %d memories for %s", len(memories), spec.agent_id)
    orchestrator.register_agent(agent)


def register_ops_agents(
    *,
    orchestrator: Any,
    communication_manager: Any,
    agent_memory: Any,
    model: str,
    use_adk: bool,
    logger: logging.Logger,
) -> OpsAgentRegistrationOutcome:
    """Prefer one ADK Ops agent and fall back to the complete native team."""
    specs = get_ops_agent_specs()
    fallback_error = None
    if use_adk:
        try:
            from aura_cli.core.agents.adk_integration import create_adk_wrapper

            spec = specs[0]
            wrapper = create_adk_wrapper(
                agent_type="ops",
                agent_id=spec.agent_id,
                model=model,
                context=orchestrator.context,
            )
            _connect_agent(
                wrapper,
                spec,
                orchestrator=orchestrator,
                communication_manager=communication_manager,
                agent_memory=agent_memory,
                logger=logger,
            )
            return OpsAgentRegistrationOutcome("adk", (spec.agent_id,))
        except Exception as error:
            fallback_error = str(error)
            logger.warning(
                "ADK Bridge unavailable for Ops: %s, using native agents",
                error,
                exc_info=True,
            )

    from aura_cli.core.agents.specialized_agents.ops_code_agent import OpsCodeAgent

    for spec in specs:
        agent = OpsCodeAgent(agent_id=spec.agent_id)
        agent.context = orchestrator.context
        _connect_agent(
            agent,
            spec,
            orchestrator=orchestrator,
            communication_manager=communication_manager,
            agent_memory=agent_memory,
            logger=logger,
        )
    return OpsAgentRegistrationOutcome(
        "native", tuple(spec.agent_id for spec in specs), fallback_error
    )


__all__ = ["OpsAgentRegistrationOutcome", "register_ops_agents"]
