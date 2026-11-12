"""Neutral security contracts shared by policy and execution adapters."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(frozen=True)
class ToolAccessDecision:
    """Typed access result while preserving the legacy tuple contract."""

    allowed: bool
    reason: str | None = None

    def as_legacy_tuple(self) -> tuple[bool, str | None]:
        """Return the historical ``check_access`` representation."""
        return self.allowed, self.reason


class CapabilityAuditSink(Protocol):
    """Keyword-only sink for sanitized capability observations."""

    def __call__(
        self,
        tool_name: str,
        decision: Any,
        *,
        task_id: str | None = None,
        phase: str = "evaluation",
    ) -> Any: ...


__all__ = ["CapabilityAuditSink", "ToolAccessDecision"]
