"""Scheduling policy for periodic delegated-worker conversation snapshots."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SnapshotSchedule:
    """Decision returned to a worker snapshot adapter."""

    message_count: int
    should_save: bool


def assess_snapshot_schedule(
    *,
    message_count: int,
    last_snapshot_count: int,
    interval: int,
    minimum_messages: int = 5,
) -> SnapshotSchedule:
    """Decide whether enough new conversation messages justify a snapshot."""
    return SnapshotSchedule(
        message_count=message_count,
        should_save=(
            message_count >= minimum_messages
            and message_count - last_snapshot_count >= interval
        ),
    )


__all__ = ["SnapshotSchedule", "assess_snapshot_schedule"]
