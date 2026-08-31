"""Application contracts for delegated-task reports."""

from aura_cli.application.agents.delegated_reporting import (
    build_delegated_task_context,
    format_delegated_task_artifacts,
    format_delegated_task_status,
    format_delegated_task_summary,
)


def task() -> dict:
    return {
        "task_id": "ops-1",
        "agent_type": "ops",
        "thread_name": "worker-1",
        "prompt": "deploy",
        "mode": "safe",
        "persisted_status": "completed",
        "fallback_reason": None,
        "snapshot_path": "/tmp/page.md",
        "delegation_payload": {
            "primary_request": "deploy service",
            "project_root": "/work",
            "current_chat_model": "local",
            "constitution_active": True,
            "supporting_context": "Dockerfile",
        },
        "final_result": {
            "status": "completed",
            "generated_files": ["compose.yml"],
            "tools_used": ["docker"],
        },
        "final_error": None,
    }


def test_reports_share_stable_task_and_supervision_data() -> None:
    data = task()
    status = format_delegated_task_status(data, status="completed", alive=False)
    summary = format_delegated_task_summary(data, status)
    artifacts = format_delegated_task_artifacts(data, snapshot_exists=True)

    assert "task_id=ops-1" in status
    assert "supervisor_state=completed" in status
    assert "primary_request=deploy service" in summary
    assert "snapshot_page=page.md" in summary
    assert "generated_files=['compose.yml']" in artifacts
    assert "snapshot_exists=True" in artifacts


def test_context_is_bounded_and_excludes_result_payloads() -> None:
    data = task()
    data["delegation_payload"]["supporting_context"] = "x" * 1200
    context = build_delegated_task_context(data)

    assert "[DELEGATED TASK CONTEXT]" in context
    assert "supporting_context:\n" + "x" * 1000 in context
    assert "generated_files" not in context
