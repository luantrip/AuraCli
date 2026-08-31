"""Concrete composition of infrastructure shared by advanced CLI workers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable


@dataclass(frozen=True)
class AdvancedWorkerRuntime:
    orchestrator: Any
    communication_manager: Any
    workflow_executor: Any
    agent_memory: Any


def initialize_advanced_worker_runtime(
    *,
    channel_id: str,
    channel_name: str,
    memory_storage_path: str | None = None,
    orchestrator: Any = None,
    communication_manager: Any = None,
    workflow_executor: Any = None,
    agent_memory: Any = None,
    on_initialized: Callable[[str], None] | None = None,
) -> AdvancedWorkerRuntime:
    """Create missing shared services while preserving injected instances."""
    notify = on_initialized or (lambda _component: None)
    if orchestrator is None:
        from aura_cli.core.agents.agent_orchestrator import (
            AgentOrchestrator,
            OrchestrationStrategy,
        )

        orchestrator = AgentOrchestrator(
            strategy=OrchestrationStrategy(
                parallel=True,
                max_concurrent=3,
                priority_ordering=True,
                load_balancing=True,
            )
        )
        notify("orchestrator")
    if communication_manager is None:
        from aura_cli.core.agents.agent_communication import CommunicationManager

        communication_manager = CommunicationManager()
        communication_manager.create_channel(channel_id, channel_name)
        notify("communication")
    if workflow_executor is None:
        from aura_cli.core.agents.agent_workflow import WorkflowExecutor

        workflow_executor = WorkflowExecutor(orchestrator)
        notify("workflow")
    if agent_memory is None:
        from aura_cli.core.agents.agent_memory import AgentMemory

        agent_memory = (
            AgentMemory(storage_path=memory_storage_path)
            if memory_storage_path is not None
            else AgentMemory()
        )
        notify("memory")
    return AdvancedWorkerRuntime(
        orchestrator=orchestrator,
        communication_manager=communication_manager,
        workflow_executor=workflow_executor,
        agent_memory=agent_memory,
    )


__all__ = ["AdvancedWorkerRuntime", "initialize_advanced_worker_runtime"]
