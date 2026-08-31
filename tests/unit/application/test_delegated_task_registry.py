"""Application contracts for delegated-task state and reconciliation."""

from types import SimpleNamespace

from aura_cli.application.agents.delegated_tasks import (
    DelegatedTaskRegistry,
    DelegatedTaskStatus,
)


def test_registration_copies_payload_and_uses_injected_clock() -> None:
    persisted: list[dict] = []
    payload = {"nested": {"value": 1}}
    registry = DelegatedTaskRegistry(
        lambda **data: persisted.append(data),
        clock=lambda: 42.0,
    )

    registry.register_task(
        agent_type="agi",
        task_id="task-1",
        thread_name="worker-1",
        prompt="build",
        delegation_payload=payload,
    )
    payload["nested"]["value"] = 2

    task = registry.resolve_task("task-1")
    assert task is not None
    assert task["created_at"] == 42.0
    assert task["delegation_payload"]["nested"]["value"] == 1
    assert persisted[0]["status"] == "accepted"


def test_reconciliation_persists_only_real_worker_changes() -> None:
    persisted: list[dict] = []
    worker = SimpleNamespace(
        final_result=None,
        final_error=None,
        last_snapshot_path=None,
        completed_at=None,
    )
    registry = DelegatedTaskRegistry(lambda **data: persisted.append(data))
    registry.register_task(
        agent_type="ops",
        task_id="task-1",
        thread_name="worker-1",
        prompt="deploy",
        delegation_payload={},
        worker_ref=worker,
    )
    task = registry.resolve_task("task-1")
    assert task is not None
    assert registry.reconcile_state(task) is False

    worker.final_result = {"status": "completed", "generated_files": ["a.py"]}
    worker.completed_at = 50.0
    assert registry.reconcile_state(task) is True
    assert task["persisted_status"] == "completed"
    assert len(persisted) == 2
    assert registry.reconcile_state(task) is False
    assert len(persisted) == 2


def test_rehydration_is_idempotent_and_latest_resolution_is_filterable() -> None:
    registry = DelegatedTaskRegistry()
    assert registry.add_rehydrated_task(
        {"task_id": "agi-1", "agent_type": "agi", "created_at": 1}
    )
    assert registry.add_rehydrated_task(
        {"task_id": "ops-1", "agent_type": "ops", "created_at": 2}
    )
    assert not registry.add_rehydrated_task(
        {"task_id": "ops-1", "agent_type": "ops", "created_at": 3}
    )

    assert registry.resolve_task()["task_id"] == "ops-1"
    assert registry.resolve_task(agent_type="AGI")["task_id"] == "agi-1"
    assert registry.counts().total == 2


def test_terminal_states_are_typed_and_persisted() -> None:
    persisted: list[dict] = []
    registry = DelegatedTaskRegistry(lambda **data: persisted.append(data))
    registry.register_task(
        agent_type="ops",
        task_id="task",
        thread_name="worker",
        prompt="deploy",
        delegation_payload={},
    )
    task = registry.resolve_task("task")
    assert task is not None

    assert registry.mark_terminal(
        task, DelegatedTaskStatus.TIMED_OUT, reason="60 seconds"
    )
    assert task["persisted_status"] == "timed_out"
    assert task["terminal_reason"] == "60 seconds"


def test_public_task_views_are_defensive_snapshots() -> None:
    registry = DelegatedTaskRegistry()
    registry.register_task(
        agent_type="ops",
        task_id="snapshot-task",
        thread_name="worker",
        prompt="deploy",
        delegation_payload={"nested": {"value": 1}},
    )

    task = registry.resolve_task("snapshot-task")
    assert task is not None
    task["delegation_payload"]["nested"]["value"] = 99
    task["persisted_status"] = "failed"
    tasks = registry.tasks
    tasks["snapshot-task"]["prompt"] = "mutated"

    stored = registry.resolve_task("snapshot-task")
    assert stored is not None
    assert stored["delegation_payload"]["nested"]["value"] == 1
    assert stored["persisted_status"] == "accepted"
    assert stored["prompt"] == "deploy"


def test_terminal_status_cannot_be_downgraded() -> None:
    registry = DelegatedTaskRegistry()
    registry.register_task(
        agent_type="ops",
        task_id="terminal-task",
        thread_name="worker",
        prompt="deploy",
        delegation_payload={},
    )
    task = registry.resolve_task("terminal-task")
    assert task is not None
    assert registry.mark_terminal(task, DelegatedTaskStatus.COMPLETED)
    assert not registry.update_status(task, DelegatedTaskStatus.RUNNING.value)
    assert task["persisted_status"] == DelegatedTaskStatus.COMPLETED.value


def test_duplicate_registration_does_not_replace_live_task() -> None:
    registry = DelegatedTaskRegistry()
    registry.register_task(
        agent_type="ops",
        task_id="duplicate-task",
        thread_name="worker-1",
        prompt="first",
        delegation_payload={},
    )
    registry.register_task(
        agent_type="agi",
        task_id="duplicate-task",
        thread_name="worker-2",
        prompt="second",
        delegation_payload={},
    )

    task = registry.resolve_task("duplicate-task")
    assert task is not None
    assert task["agent_type"] == "ops"
    assert task["prompt"] == "first"
