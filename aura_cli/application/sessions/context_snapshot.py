"""Policies for bounding and snapshotting an interactive conversation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

Message = Mapping[str, Any]


@dataclass(frozen=True)
class SnapshotPlan:
    """Decision data used by a notebook adapter when creating a snapshot."""

    estimated_tokens: int
    use_cognitive_refinement: bool


def truncate_history(
    history: Sequence[Message], max_messages: int
) -> list[dict[str, Any]]:
    """Keep every system message and the newest messages within the configured bound."""
    messages = [dict(message) for message in history]
    if len(messages) <= max_messages:
        return messages

    system_messages = [
        message for message in messages if message.get("role") == "system"
    ]
    other_messages = [
        message for message in messages if message.get("role") != "system"
    ]
    keep_recent = max_messages - len(system_messages)
    if keep_recent <= 0:
        return system_messages
    return system_messages + other_messages[-keep_recent:]


def plan_snapshot(
    history: Sequence[Message], *, refinement_threshold_tokens: int = 16_000
) -> SnapshotPlan:
    """Estimate context size and decide whether cognitive refinement is worthwhile."""
    estimated_tokens = (
        sum(len(str(message.get("content", ""))) for message in history) // 4
    )
    return SnapshotPlan(
        estimated_tokens=estimated_tokens,
        use_cognitive_refinement=estimated_tokens > refinement_threshold_tokens,
    )


def build_snapshot_history(
    base_system_messages: Sequence[Message],
    *,
    page_path: str,
    saved_message_count: int,
    refined: bool,
) -> list[dict[str, Any]]:
    """Build the fresh history that points the model to a persisted notebook page."""
    refinement = " refinado e " if refined else " "
    system_note = (
        f"📓 **SYSTEM NOTE:** The previous context was{refinement}saved to the memory notebook.\n\n"
        f"**Page:** `{page_path}`\n\n"
        "If you need information from previous interactions, use the following tools:\n"
        "- `notebook_list()` - List all available pages\n"
        "- `notebook_read(page_path)` - Read the content of a specific page\n"
        "- `notebook_search(query)` - Search the notebook index\n\n"
        f"The saved context contains {saved_message_count} messages."
    )
    return [
        *[dict(message) for message in base_system_messages],
        {"role": "system", "content": system_note},
    ]


__all__ = [
    "SnapshotPlan",
    "build_snapshot_history",
    "plan_snapshot",
    "truncate_history",
]
