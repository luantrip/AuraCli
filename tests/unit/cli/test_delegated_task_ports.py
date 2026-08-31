"""Adapter tests for injected delegated-task infrastructure ports."""

from aura_cli.application.agents.delegated_ports import ThreadObservation
from aura_cli.cli.delegated_tasks import DelegatedTaskManager


def manager(**ports) -> DelegatedTaskManager:
    instance = DelegatedTaskManager(**ports)
    instance.add_rehydrated_task(
        {
            "task_id": "task-1",
            "agent_type": "ops",
            "thread_name": "worker-1",
            "prompt": "deploy",
            "delegation_payload": {},
            "created_at": 1.0,
            "persisted_status": "queued",
            "snapshot_path": "/virtual/snapshot.md",
            "worker_ref": None,
        }
    )
    return instance


def test_status_uses_injected_thread_observer() -> None:
    instance = manager(
        observe_thread=lambda name: ThreadObservation("running", name == "worker-1")
    )
    status = instance.get_task_status("task-1")
    assert "status=running" in status
    assert "alive=True" in status


def test_snapshot_and_artifact_checks_use_injected_ports() -> None:
    instance = manager(
        read_snapshot=lambda path: f"content from {path}",
        snapshot_exists=lambda path: path == "/virtual/snapshot.md",
    )
    assert "content from /virtual/snapshot.md" in instance.read_task_snapshot("task-1")
    assert "snapshot_exists=True" in instance.get_task_artifacts("task-1")
