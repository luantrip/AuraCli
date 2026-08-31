"""Framework-neutral reports for delegated task state."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from aura_cli.application.agents.delegation import get_supervisor_state


def _outcome(
    task: Mapping[str, Any],
) -> tuple[dict[str, Any], dict[str, Any], Any, Any]:
    result = dict(task.get("final_result") or {})
    error = dict(task.get("final_error") or {})
    fallback = (
        task.get("fallback_reason")
        or result.get("fallback_reason")
        or error.get("fallback_reason")
    )
    snapshot = (
        task.get("snapshot_path")
        or result.get("snapshot_path")
        or error.get("snapshot_path")
    )
    return result, error, fallback, snapshot


def format_delegated_task_status(
    task: Mapping[str, Any],
    *,
    status: str,
    alive: bool,
) -> str:
    """Format a live/persisted status observation."""
    thread_name = str(task.get("thread_name", ""))
    fallback = task.get("fallback_reason")
    supervisor = get_supervisor_state(
        status=status, alive=alive, fallback_reason=fallback
    )
    suffix = f"; fallback_reason={fallback}" if fallback else ""
    return (
        f"task_id={task['task_id']}; agent_type={task.get('agent_type')}; "
        f"status={status}; supervisor_state={supervisor}; alive={alive}; "
        f"thread={thread_name}; mode={task.get('mode') or 'n/a'}{suffix}"
    )


def format_delegated_task_summary(task: Mapping[str, Any], status_line: str) -> str:
    """Format the detailed state and handoff context of one task."""
    payload = task.get("delegation_payload", {}) or {}
    result, error, fallback, snapshot = _outcome(task)
    supervisor = get_supervisor_state(
        status=str(task.get("persisted_status") or "unknown"),
        alive=False,
        fallback_reason=fallback,
    )
    return "\n".join(
        [
            status_line,
            f"prompt={str(task.get('prompt', ''))[:400]}",
            f"primary_request={payload.get('primary_request', '')}",
            f"project_root={payload.get('project_root', '')}",
            f"current_chat_model={payload.get('current_chat_model', '')}",
            f"constitution_active={payload.get('constitution_active', False)}",
            f"supervisor_state={supervisor}",
            f"fallback_reason={fallback or 'n/a'}",
            f"snapshot_path={snapshot or 'n/a'}",
            f"snapshot_page={Path(snapshot).name if snapshot else 'n/a'}",
            f"result_summary={str(result)[:500] if result else 'n/a'}",
            f"error_summary={str(error)[:500] if error else 'n/a'}",
            f"recent_chat_excerpt={str(payload.get('recent_chat_excerpt', ''))[:800] or 'n/a'}",
            f"supporting_context={str(payload.get('supporting_context', ''))[:800] or 'n/a'}",
        ]
    )


def format_delegated_task_artifacts(
    task: Mapping[str, Any], *, snapshot_exists: bool
) -> str:
    """Format concrete files and workflow artifacts produced by a task."""
    result, error, fallback, snapshot = _outcome(task)
    generated = result.get("generated_files") or []
    edited = result.get("edited_files") or []
    analyzed = result.get("analyzed_files") or []
    touched = result.get("files_touched") or generated or edited or analyzed or []
    supervisor = get_supervisor_state(
        status=str(task.get("persisted_status") or "unknown"),
        alive=False,
        fallback_reason=fallback,
    )
    return "\n".join(
        [
            f"task_id={task['task_id']}",
            f"agent_type={task.get('agent_type')}",
            f"supervisor_state={supervisor}",
            f"fallback_reason={fallback or 'n/a'}",
            f"snapshot_path={snapshot or 'n/a'}",
            f"snapshot_exists={snapshot_exists}",
            f"tools_used={str(result.get('tools_used', 'n/a'))[:300]}",
            f"generated_files={str(generated)[:400] if generated else 'n/a'}",
            f"edited_files={str(edited)[:400] if edited else 'n/a'}",
            f"analyzed_files={str(analyzed)[:400] if analyzed else 'n/a'}",
            f"files_touched={str(touched)[:400] if touched else 'n/a'}",
            f"workflow_result={str(result.get('workflow_result', 'n/a'))[:400]}",
            f"error_summary={str(error or 'n/a')[:400]}",
        ]
    )


def build_delegated_task_context(task: Mapping[str, Any]) -> str:
    """Build the bounded context block attached to the next conversation turn."""
    payload = task.get("delegation_payload", {}) or {}
    lines = [
        "[DELEGATED TASK CONTEXT]",
        f"task_id: {task['task_id']}",
        f"agent_type: {task.get('agent_type')}",
        f"mode: {task.get('mode') or 'n/a'}",
        f"prompt: {str(task.get('prompt', ''))[:500]}",
        f"primary_request: {payload.get('primary_request', '')}",
        f"project_root: {payload.get('project_root', '')}",
        f"current_chat_model: {payload.get('current_chat_model', '')}",
        f"constitution_active: {payload.get('constitution_active', False)}",
        f"snapshot_path: {task.get('snapshot_path') or 'n/a'}",
    ]
    if payload.get("supporting_context"):
        lines.extend(["supporting_context:", str(payload["supporting_context"])[:1000]])
    if payload.get("recent_chat_excerpt"):
        lines.extend(
            ["recent_chat_excerpt:", str(payload["recent_chat_excerpt"])[:1000]]
        )
    lines.append("[/DELEGATED TASK CONTEXT]")
    return "\n".join(lines)


__all__ = [
    "build_delegated_task_context",
    "format_delegated_task_artifacts",
    "format_delegated_task_status",
    "format_delegated_task_summary",
]
