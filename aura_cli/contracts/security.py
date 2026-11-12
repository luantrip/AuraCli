"""Compatibility shim — moved to aura_cli.core.contracts.security."""

from aura_cli.core.contracts.security import (
    CapabilityAuditSink,
    ToolAccessDecision,
)

__all__ = ["CapabilityAuditSink", "ToolAccessDecision"]
