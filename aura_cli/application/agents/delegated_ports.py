"""Ports used by delegated-task orchestration adapters."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass


@dataclass(frozen=True)
class ThreadObservation:
    """Framework-neutral observation of a background worker thread."""

    status: str
    alive: bool


ObserveThread = Callable[[str], ThreadObservation | None]
ReadSnapshot = Callable[[str], str | None]
SnapshotExists = Callable[[str], bool]

__all__ = ["ObserveThread", "ReadSnapshot", "SnapshotExists", "ThreadObservation"]
