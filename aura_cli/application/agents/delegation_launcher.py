"""Application coordinator for launching and registering delegated workers."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Protocol

from aura_cli.application.agents.delegation import (
    DelegationLaunchOutcome,
    DelegationLaunchStatus,
    DelegationPlan,
)


class DelegatedWorkerHandle(Protocol):
    task_id: str


class DelegatedThreadHandle(Protocol):
    name: str


WorkerFactory = Callable[
    [DelegationPlan, str, Mapping[str, str]],
    tuple[DelegatedWorkerHandle, DelegatedThreadHandle],
]
RegisterDelegatedTask = Callable[..., None]


@dataclass(frozen=True)
class DelegationLaunchResult:
    """Outcome plus opaque infrastructure handles owned by the adapter."""

    outcome: DelegationLaunchOutcome
    worker: DelegatedWorkerHandle | None = None
    thread: DelegatedThreadHandle | None = None


class DelegationLaunchCoordinator:
    """Launch a prepared delegation and atomically register its metadata."""

    def __init__(self, register_task: RegisterDelegatedTask) -> None:
        self._register_task = register_task

    def launch(
        self,
        plan: DelegationPlan,
        *,
        model: str,
        credentials: Mapping[str, str],
        factory: WorkerFactory,
    ) -> DelegationLaunchResult:
        try:
            worker, thread = factory(plan, model, credentials)
            task_id = str(getattr(worker, "task_id", "unknown"))
            thread_name = str(getattr(thread, "name", "unknown"))
            self._register_task(
                agent_type=plan.agent_type,
                task_id=task_id,
                thread_name=thread_name,
                prompt=plan.request,
                delegation_payload=plan.payload,
                mode=plan.mode,
                worker_ref=worker,
            )
            return DelegationLaunchResult(
                DelegationLaunchOutcome(
                    DelegationLaunchStatus.STARTED,
                    plan.agent_type,
                    request=plan.request,
                    mode=plan.mode,
                    task_id=task_id,
                    thread_name=thread_name,
                ),
                worker,
                thread,
            )
        except Exception as error:
            return DelegationLaunchResult(
                DelegationLaunchOutcome(
                    DelegationLaunchStatus.FAILED,
                    plan.agent_type,
                    request=plan.request,
                    mode=plan.mode,
                    error=str(error),
                )
            )


__all__ = [
    "DelegatedThreadHandle",
    "DelegatedWorkerHandle",
    "DelegationLaunchCoordinator",
    "DelegationLaunchResult",
    "RegisterDelegatedTask",
    "WorkerFactory",
]
