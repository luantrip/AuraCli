from aura_cli.application.agents.worker_lifecycle import (
    build_worker_error_payload,
    build_worker_success_payload,
    get_worker_failure_supervisor_state,
    normalize_worker_outcome,
    summarize_worker_success,
)


def test_ops_success_payload_merges_and_deduplicates_artifacts() -> None:
    result = {
        "generated_files": ["new.py"],
        "files_touched": ["README.md", "new.py"],
        "workflow_result": {"status": "completed"},
    }

    payload = build_worker_success_payload(
        result,
        task_id="ops-1",
        completed_at=10.5,
        delegation_payload={"source": "chat"},
        snapshot_path="notebook/page-1",
        mode="git",
        generated_files=["fallback.py"],
        edited_files=["README.md"],
        analyzed_files=["config.toml"],
    )

    assert payload["generated_files"] == ["new.py"]
    assert payload["edited_files"] == ["README.md"]
    assert payload["files_touched"] == ["new.py", "README.md", "config.toml"]
    assert payload["completed_at"] == 10.5
    assert payload["fallback_reason"] is None


def test_agi_success_payload_does_not_invent_ops_fields() -> None:
    payload = build_worker_success_payload(
        {"result": "done"},
        task_id="agi-1",
        completed_at=20,
        delegation_payload=None,
        snapshot_path=None,
    )

    assert payload["task_id"] == "agi-1"
    assert "mode" not in payload
    assert "generated_files" not in payload
    assert summarize_worker_success(payload) == "done"


def test_error_payload_and_supervisor_state_are_shared() -> None:
    payload = build_worker_error_payload(
        "approval required",
        task_id="ops-1",
        prompt="deploy",
        completed_at=30,
        fallback_reason="human_approval_required",
        delegation_payload=None,
        snapshot_path=None,
        mode="docker",
    )

    assert payload["status"] == "error"
    assert payload["mode"] == "docker"
    assert (
        get_worker_failure_supervisor_state("human_approval_required")
        == "awaiting_human"
    )
    assert (
        get_worker_failure_supervisor_state("external_dependency") == "returned_to_chat"
    )


def test_success_summary_is_bounded() -> None:
    assert len(summarize_worker_success({"result": "x" * 300})) == 180


def test_normalize_worker_outcome_adds_shared_terminal_contract() -> None:
    outcome = normalize_worker_outcome(
        {"status": "completed", "result": "done", "domain_field": "kept"},
        task_id="task-1",
        started_at=10.0,
        finished_at=12.0,
    )

    assert outcome["status"] == "completed"
    assert outcome["task_id"] == "task-1"
    assert outcome["started_at"] == 10.0
    assert outcome["finished_at"] == 12.0
    assert outcome["completed_at"] == 12.0
    assert outcome["outcome_version"] == 1
    assert outcome["terminal"] is True
    assert outcome["domain_field"] == "kept"


def test_normalize_worker_outcome_rejects_unknown_status() -> None:
    outcome = normalize_worker_outcome(
        {"status": "still_running", "result": "partial"},
        task_id="task-2",
        started_at=20.0,
        finished_at=21.0,
    )

    assert outcome["status"] == "error"
    assert outcome["error_code"] == "invalid_terminal_status"
    assert "still_running" in outcome["error"]
