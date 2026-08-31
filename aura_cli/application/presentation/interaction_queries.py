"""Presentation-neutral queries over recorded LLM interactions."""

from __future__ import annotations

import csv
from datetime import datetime
from io import StringIO
import json
from typing import Any, Iterable, Protocol, TypeVar


class InteractionView(Protocol):
    """Minimum interaction shape required by dashboard queries."""

    timestamp: float
    prompt: str
    response: str | None
    status: Any
    prompt_tokens: int
    generated_tokens: int
    execution_time: float
    tool_calls: list[dict[str, Any]]
    error: str | None

    @property
    def id(self) -> str: ...


InteractionT = TypeVar("InteractionT", bound=InteractionView)


def filter_interactions(
    interactions: Iterable[InteractionT],
    *,
    query: str = "",
    status: Any = None,
    interaction_type: str | None = None,
    cutoff_timestamp: float | None = None,
) -> list[InteractionT]:
    """Apply dashboard search and filters without depending on a UI toolkit."""
    filtered = list(interactions)
    normalized_query = query.casefold()
    if normalized_query:
        filtered = [
            item
            for item in filtered
            if normalized_query in item.prompt.casefold()
            or normalized_query in (item.response or "").casefold()
            or normalized_query in (item.error or "").casefold()
        ]
    if status is not None:
        filtered = [item for item in filtered if item.status == status]
    if interaction_type == "Chat":
        filtered = [item for item in filtered if not item.tool_calls]
    elif interaction_type == "Tools":
        filtered = [item for item in filtered if item.tool_calls]
    if cutoff_timestamp is not None:
        filtered = [item for item in filtered if item.timestamp >= cutoff_timestamp]
    return filtered


def summarize_interactions(interactions: Iterable[InteractionView]) -> dict[str, Any]:
    """Build aggregate counts consumed by any interaction-history surface."""
    items = list(interactions)
    by_status: dict[str, int] = {}
    by_type = {"Chat": 0, "Tools": 0}
    completed_times: list[float] = []
    for item in items:
        status_key = str(item.status.value)
        by_status[status_key] = by_status.get(status_key, 0) + 1
        by_type["Tools" if item.tool_calls else "Chat"] += 1
        if item.execution_time > 0:
            completed_times.append(item.execution_time)
    return {
        "total": len(items),
        "by_status": by_status,
        "by_type": by_type,
        "total_tokens": sum(
            item.prompt_tokens + item.generated_tokens for item in items
        ),
        "avg_execution_time": (
            sum(completed_times) / len(completed_times) if completed_times else 0.0
        ),
    }


def export_interactions(interactions: Iterable[InteractionView], fmt: str) -> str:
    """Serialize filtered interaction history to JSON or CSV."""
    items = list(interactions)
    if fmt == "json":
        return json.dumps(
            [
                {
                    "id": item.id,
                    "timestamp": item.timestamp,
                    "prompt": item.prompt,
                    "response": item.response,
                    "status": item.status.value,
                    "prompt_tokens": item.prompt_tokens,
                    "generated_tokens": item.generated_tokens,
                    "execution_time": item.execution_time,
                    "tool_calls": item.tool_calls,
                    "error": item.error,
                }
                for item in items
            ],
            indent=2,
            default=str,
        )
    if fmt != "csv":
        return ""
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(
        [
            "ID",
            "Timestamp",
            "Status",
            "Prompt",
            "Response",
            "Tokens",
            "Execution Time",
            "Tool Calls",
        ]
    )
    for item in items:
        writer.writerow(
            [
                item.id,
                datetime.fromtimestamp(item.timestamp).isoformat(),
                item.status.value,
                item.prompt[:100],
                (item.response or "")[:100],
                item.prompt_tokens + item.generated_tokens,
                item.execution_time,
                len(item.tool_calls),
            ]
        )
    return output.getvalue()
