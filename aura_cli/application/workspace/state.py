"""Canonical aggregate of services owned by one workspace session."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class WorkspaceState:
    """Group stateful services that must always belong to the same workspace."""

    project_root: Path
    memory: Any
    session: Any
    context: Any
    notebook: Any
    imagination: Any
    checkpoint: Any

    def __post_init__(self) -> None:
        resolved_root = self.project_root.resolve()
        object.__setattr__(self, "project_root", resolved_root)

    @property
    def conversation(self) -> Any:
        """Expose the conversation context through a domain-neutral name."""
        return self.context
