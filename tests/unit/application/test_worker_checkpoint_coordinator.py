from types import SimpleNamespace
from unittest.mock import Mock

from aura_cli.application.workspace.checkpoint_coordinator import (
    WorkerCheckpointCoordinator,
)


def test_checkpoint_lifecycle_uses_injected_ports() -> None:
    manager = Mock(initialized=False)
    manager.create.return_value = SimpleNamespace(commit_hash="abc123")
    manager.restore.return_value = ["one.py", "two.py"]
    statuses: list[str] = []
    coordinator = WorkerCheckpointCoordinator(
        "agi_worker",
        checkpoint_manager=manager,
        status_publisher=statuses.append,
    )

    coordinator.initialize()
    assert coordinator.create_initial_checkpoint("start") == "abc123"
    assert coordinator.restore_on_failure() is True

    manager.init.assert_called_once_with()
    manager.create.assert_called_once_with("agi_worker start")
    manager.restore.assert_called_once_with("abc123")
    assert statuses == [
        "📸 Checkpoint created: abc123",
        "▲ Restored to checkpoint abc123 (2 files)",
    ]


def test_task_checkpoint_and_hook_context_are_coordinated() -> None:
    manager = Mock(initialized=True)
    manager.create.return_value = SimpleNamespace(commit_hash="before123")
    hooks: list[tuple[str, dict[str, object]]] = []
    coordinator = WorkerCheckpointCoordinator(
        "ops_worker",
        checkpoint_manager=manager,
        hook_publisher=lambda event, context: hooks.append((event, dict(context))),
        clock=lambda: 42.0,
    )

    coordinator.initialize()
    assert coordinator.create_checkpoint_before_task("edit config") == "before123"
    coordinator.trigger_hook("task-start", {"task": "edit config"})

    manager.create.assert_called_once_with("Before: edit config")
    assert hooks == [
        (
            "task-start",
            {
                "task": "edit config",
                "worker_name": "ops_worker",
                "timestamp": 42.0,
            },
        )
    ]


def test_unconfigured_coordinator_is_a_safe_noop() -> None:
    coordinator = WorkerCheckpointCoordinator("worker")

    assert coordinator.create_initial_checkpoint() is None
    assert coordinator.create_checkpoint_before_task("anything") is None
    assert coordinator.restore_on_failure() is False
    coordinator.trigger_hook("error")
