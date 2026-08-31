"""Helpers for classifying worker fallback reasons."""

from __future__ import annotations

from typing import Any


def classify_fallback_reason(error: Any) -> str:
    """Return a stable fallback reason from a worker error."""
    text = str(error or "").strip().lower()
    if not text:
        return "execution_error"

    human_markers = (
        "approval",
        "approve",
        "confirmation",
        "confirm",
        "autoriz",
        "humano",
        "human",
        "interven",
        "permission denied",
        "forbidden",
    )
    if any(marker in text for marker in human_markers):
        return "human_approval_required"

    external_markers = (
        "api key",
        "not configured",
        "rate limit",
        "quota",
        "timed out",
        "timeout",
        "network",
        "connection",
        "dns",
        "service unavailable",
        "docker daemon",
        "authentication",
        "unauthorized",
        "forbidden by policy",
    )
    if any(marker in text for marker in external_markers):
        return "external_dependency"

    blocked_markers = (
        "blocked",
        "waiting",
        "waiting",
        "pendente",
        "manual intervention",
    )
    if any(marker in text for marker in blocked_markers):
        return "blocked_external"

    missing_markers = (
        "not found",
        "no such file",
        "command not found",
        "module not found",
        "missing",
        "ausente",
        "not found",
    )
    if any(marker in text for marker in missing_markers):
        return "missing_dependency"

    return "execution_error"
