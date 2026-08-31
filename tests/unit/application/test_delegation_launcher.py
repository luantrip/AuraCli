"""Application tests for delegated worker launch coordination."""

from pathlib import Path
from types import SimpleNamespace

from aura_cli.application.agents.delegation import (
    DelegationLaunchStatus,
    prepare_delegation,
)
from aura_cli.application.agents.delegation_launcher import DelegationLaunchCoordinator


def plan():
    return prepare_delegation(
        "deploy",
        agent_type="ops",
        conversation_history=[],
        project_root=Path("/work"),
        final_model="local",
        constitution=None,
        mode="git",
    )


def test_launch_registers_metadata_and_returns_opaque_handles() -> None:
    registrations: list[dict] = []
    worker = SimpleNamespace(task_id="task-1")
    thread = SimpleNamespace(name="thread-1")
    coordinator = DelegationLaunchCoordinator(lambda **data: registrations.append(data))

    result = coordinator.launch(
        plan(),
        model="local",
        credentials={"KEY": "value"},
        factory=lambda prepared, model, credentials: (worker, thread),
    )

    assert result.outcome.status is DelegationLaunchStatus.STARTED
    assert result.worker is worker and result.thread is thread
    assert registrations[0]["task_id"] == "task-1"
    assert registrations[0]["mode"] == "git"
    assert registrations[0]["delegation_payload"]["delegation_mode"] == "git"


def test_factory_failure_does_not_register_partial_task() -> None:
    registrations: list[dict] = []
    coordinator = DelegationLaunchCoordinator(lambda **data: registrations.append(data))

    def fail(*_args):
        raise RuntimeError("factory unavailable")

    result = coordinator.launch(plan(), model="local", credentials={}, factory=fail)

    assert result.outcome.status is DelegationLaunchStatus.FAILED
    assert result.outcome.error == "factory unavailable"
    assert result.worker is None and result.thread is None
    assert registrations == []
