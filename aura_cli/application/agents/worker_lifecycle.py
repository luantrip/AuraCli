"""Shared terminal-state policies for delegated AGI and Ops workers."""

from __future__ import annotations

import time
from typing import Any, Iterable, Mapping

from .delegation import get_supervisor_state

TERMINAL_OUTCOME_VERSION = 1
TERMINAL_OUTCOME_STATUSES = frozenset(
    {
        "completed",
        "error",
        "failed",
        "cancelled",
        "canceled",
        "timeout",
        "timed_out",
        "blocked",
        "stopped",
    }
)


def normalize_worker_outcome(
    payload: Mapping[str, Any],
    *,
    task_id: str,
    started_at: float,
    finished_at: float | None = None,
) -> dict[str, Any]:
    """Normalize one terminal worker result without dropping domain fields."""
    normalized = dict(payload)
    status = str(normalized.get("status") or "error")
    if status not in TERMINAL_OUTCOME_STATUSES:
        normalized["status"] = "error"
        normalized.setdefault("error_code", "invalid_terminal_status")
        normalized.setdefault("error", f"Invalid terminal status received: {status}")
    else:
        normalized["status"] = status

    normalized.setdefault("task_id", task_id)
    normalized.setdefault("started_at", started_at)
    resolved_finished_at = (
        normalized.get("finished_at")
        or normalized.get("completed_at")
        or finished_at
        or time.time()
    )
    normalized.setdefault("finished_at", resolved_finished_at)
    normalized.setdefault("completed_at", resolved_finished_at)
    normalized.setdefault("outcome_version", TERMINAL_OUTCOME_VERSION)
    normalized.setdefault("terminal", True)
    normalized.setdefault("retryability", "unknown")
    return normalized


def _deduplicate_paths(groups: Iterable[Iterable[str]]) -> list[str]:
    paths: list[str] = []
    for group in groups:
        for path in group:
            if path not in paths:
                paths.append(path)
    return paths


def build_worker_success_payload(
    result: Mapping[str, Any],
    *,
    task_id: str,
    completed_at: float,
    delegation_payload: Mapping[str, Any] | None,
    snapshot_path: str | None,
    mode: str | None = None,
    generated_files: Iterable[str] = (),
    edited_files: Iterable[str] = (),
    analyzed_files: Iterable[str] = (),
) -> dict[str, Any]:
    """Complete and normalize the successful result persisted by a worker."""
    payload = dict(result)
    payload.setdefault("status", "completed")
    payload.setdefault("task_id", task_id)
    if mode is not None:
        payload.setdefault("mode", mode)
    payload.setdefault("delegation_payload", delegation_payload)
    payload.setdefault("fallback_reason", None)
    if mode is not None:
        payload.setdefault("generated_files", list(generated_files))
        payload.setdefault("edited_files", list(edited_files))
        payload.setdefault("analyzed_files", list(analyzed_files))
        payload["files_touched"] = _deduplicate_paths(
            (
                payload.get("generated_files", ()),
                payload.get("edited_files", ()),
                payload.get("analyzed_files", ()),
                payload.get("files_touched", ()) or (),
            )
        )
    if snapshot_path:
        payload.setdefault("snapshot_path", snapshot_path)
    payload.setdefault("completed_at", completed_at)
    return payload


def build_worker_error_payload(
    error: Any,
    *,
    task_id: str,
    prompt: str,
    completed_at: float,
    fallback_reason: str | None,
    delegation_payload: Mapping[str, Any] | None,
    snapshot_path: str | None,
    mode: str | None = None,
    error_code: str | None = None,
) -> dict[str, Any]:
    """Build the stable error record persisted by either delegated worker."""
    payload = {
        "status": "error",
        "task_id": task_id,
        "error": str(error),
        "error_code": error_code or "worker_error",
        "fallback_reason": fallback_reason,
        "prompt": prompt,
        "delegation_payload": delegation_payload,
        "snapshot_path": snapshot_path,
        "completed_at": completed_at,
        "finished_at": completed_at,
    }
    if mode is not None:
        payload["mode"] = mode
    return payload


def get_worker_failure_supervisor_state(fallback_reason: str | None) -> str:
    """Translate a terminal failure into the state observed by the chat supervisor."""
    return get_supervisor_state(
        status="error", alive=False, fallback_reason=fallback_reason
    )


def summarize_worker_success(payload: Mapping[str, Any], limit: int = 180) -> str:
    """Build the bounded terminal summary published through the event adapter."""
    summary = (
        payload.get("workflow_result") or payload.get("result") or "worker finished"
    )
    return str(summary)[:limit]


__all__ = [
    "build_worker_error_payload",
    "build_worker_success_payload",
    "get_worker_failure_supervisor_state",
    "normalize_worker_outcome",
    "summarize_worker_success",
]
