"""Compatibility shim — contracts merged into core.contracts.

Import directly from ``aura_cli.core.contracts.security`` for new code.
"""

from aura_cli.core.contracts.security import CapabilityAuditSink, ToolAccessDecision

__all__ = ["CapabilityAuditSink", "ToolAccessDecision"]
