"""Exercise lifecycle reduction, audit symmetry, and worker outcome contracts."""

from __future__ import annotations

import json
import os
from pathlib import Path

from aura_cli.application.agents.events import AgiEvent, AgiEventType
from aura_cli.application.agents.operational_feedback import (
    build_operational_trail,
    describe_operational_event,
)
from aura_cli.application.agents.worker_lifecycle import (
    build_worker_error_payload,
    build_worker_success_payload,
    normalize_worker_outcome,
)
from aura_cli.application.presentation.agent_event_reducer import AgentEventStateReducer
from aura_cli.application.presentation.lifecycle_audit import audit_event_lifecycles
from aura_cli.tui.core.sync_store import SyncStore


def make_event(event_type: AgiEventType, timestamp: float, data: dict, task_id: str = "task") -> AgiEvent:
    return AgiEvent(type=event_type, task_id=task_id, timestamp=timestamp, data=data)


def check_event_reducer() -> dict[str, object]:
    store = SyncStore()
    reducer = AgentEventStateReducer(store)
    events = [
        make_event(AgiEventType.TASK_START, 1, {"description": "Build"}),
        make_event(
            AgiEventType.SUBTASK_START,
            2,
            {"description": "Inspect"},
            task_id="subtask",
        ),
        make_event(
            AgiEventType.TOOL_EXECUTING,
            3,
            {
                "tool_name": "run_shell",
                "tool_args": {"command": "echo ok", "api_key": "secret-value"},
                "execution_id": "tool-1",
            },
        ),
        make_event(
            AgiEventType.TOOL_RESULT,
            4,
            {"tool_name": "run_shell", "success": True, "result": "ok", "execution_id": "tool-1"},
        ),
        make_event(
            AgiEventType.APPROVAL_REQUESTED,
            5,
            {"request_id": "approval-1", "action": "deploy", "message": "Deploy?"},
        ),
        make_event(
            AgiEventType.APPROVAL_RESOLVED,
            6,
            {"request_id": "approval-1", "action": "deploy", "status": "approved"},
        ),
        make_event(
            AgiEventType.CHECKPOINT_CREATED,
            7,
            {"name": "before-deploy", "artifacts": ["checkpoint://1"]},
        ),
        make_event(AgiEventType.TASK_COMPLETE, 8, {"success": True, "result": "done"}),
    ]
    for event in events:
        reduction = reducer.reduce(event)
        assert reduction is not None
    task = store.get_task("task")
    assert task is not None and task["status"] == "completed"
    assert task["checkpoints"][0]["name"] == "before-deploy"
    assert task["children"]["tool-1"]["status"] == "completed"
    stale = reducer.reduce(make_event(AgiEventType.TASK_UPDATE, 0, {"status": "running"}))
    assert stale.hide_thinking is False and store.get_task("task")["status"] == "completed"
    tool_chat = reducer.reduce(events[2]).chat
    assert tool_chat is not None and "secret-value" not in tool_chat.content
    return {"status": task["status"], "children": len(task["children"]), "checkpoint": task["checkpoints"][0]["name"]}


def check_lifecycle_and_feedback() -> dict[str, object]:
    events = [
        make_event(AgiEventType.TASK_START, 1, {"description": "Build"}),
        make_event(AgiEventType.TASK_INTERRUPTED, 2, {"reason": "timeout", "resumable": True}),
        make_event(AgiEventType.EXTERNAL_WAIT_ENDED, 3, {"message": "ready"}),
        make_event(AgiEventType.TASK_COMPLETE, 4, {"success": True, "result": "done"}),
    ]
    audit = audit_event_lifecycles(events)
    assert audit.is_symmetric and audit.started == ("task",) and audit.terminal == ("task",)
    feedback = [describe_operational_event(event) for event in events]
    assert all(item is not None for item in feedback)
    trail = build_operational_trail(events, limit=3)
    assert len(trail.lines) == 3 and "# Aura Operational Trail" in trail.export_text()
    return {"symmetric": audit.is_symmetric, "trail_lines": len(trail.lines), "levels": [item.level for item in feedback if item]}


def check_worker_outcomes() -> dict[str, object]:
    success = build_worker_success_payload(
        {"result": "done", "generated_files": ["a.py"]},
        task_id="worker-1",
        completed_at=10,
        delegation_payload=None,
        snapshot_path="snapshot.md",
        mode="agi",
        generated_files=["a.py"],
        edited_files=["b.py"],
        analyzed_files=["a.py"],
    )
    error = build_worker_error_payload(
        "approval required",
        task_id="worker-2",
        prompt="deploy",
        completed_at=11,
        fallback_reason="human_approval_required",
        delegation_payload=None,
        snapshot_path=None,
    )
    invalid = normalize_worker_outcome(
        {"status": "still_running", "result": "partial"},
        task_id="worker-3",
        started_at=12,
        finished_at=13,
    )
    assert success["files_touched"] == ["a.py", "b.py"]
    assert error["status"] == "error" and error["finished_at"] == 11
    assert invalid["status"] == "error" and invalid["error_code"] == "invalid_terminal_status"
    return {"success_files": success["files_touched"], "error_code": invalid["error_code"]}


def main() -> None:
    report = {
        "contract": "aura-realtime-lifecycle-v1",
        "checks": {
            "event_reducer": check_event_reducer(),
            "lifecycle_feedback": check_lifecycle_and_feedback(),
            "worker_outcomes": check_worker_outcomes(),
        },
        "aura_home": os.environ.get("AURA_HOME", ""),
        "status": "READY",
    }
    root = Path(os.environ.get("AURA_HOME", "."))
    root.mkdir(parents=True, exist_ok=True)
    (root / "realtime-lifecycle-probe.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print("LIFECYCLE_READY")
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
