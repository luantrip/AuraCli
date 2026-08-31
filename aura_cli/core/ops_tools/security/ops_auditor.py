"""
Ops Security Auditor — Phase 4.1

Intercepts Ops tool calls, classifies risk level, and requires confirmation
for destructive operations before they are executed.

Risk classification:
    CRITICAL  — irreversible data loss (rm -rf, DROP TABLE, force-push, etc.)
    HIGH      — significant side effects (docker rm, git reset --hard, etc.)
    MEDIUM    — reversible but impactful (git commit, write_file, etc.)
    LOW       — read-only or safe operations

Integration:
    Called from execute_tool_call() via BEFORE_TOOL_CALL hook, or directly
    via audit_tool_call() before dispatching to the tool.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import re
from typing import Any, Dict, List, Tuple

from aura_cli.core.logger import get_logger

logger = get_logger(__name__)


class OpsRiskLevel(Enum):
    """Risk level classification for ops operations."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class OpsAuditResult:
    """Result of an ops security audit."""

    tool_name: str
    risk_level: OpsRiskLevel
    reason: str
    blocked: bool = False
    warnings: List[str] = field(default_factory=list)


# Risk rules — (tool_name_pattern, arg_pattern, risk, reason)

_CRITICAL_SHELL_PATTERNS = [
    r"rm\s+-[rf]{1,2}\s+/",  # rm -rf /path (any absolute)
    r"rm\s+-[rf]{1,2}\s+\*",  # rm -rf *
    r"rm\s+-[rf]{1,2}\s+\.",  # rm -rf . or ./dir
    r"rm\s+-[rf]{1,2}\s+~",  # rm -rf ~/
    r"rm\s+--recursive",  # rm --recursive
    r":\s*\(\)\s*\{.*\}",  # fork bomb
    r"dd\s+if=",
    r"mkfs\.",
    r">\s*/dev/sd",
    r"chmod\s+-R\s+777\s+/",
    r"DROP\s+TABLE",
    r"DROP\s+DATABASE",
    r"TRUNCATE\s+TABLE",
    r"git\s+push\s+.*--force",
    r"git\s+reset\s+--hard\s+HEAD",
]

_HIGH_SHELL_PATTERNS = [
    r"rm\s+-r",
    r"docker\s+rm\s+-f",
    r"docker\s+system\s+prune",
    r"kubectl\s+delete",
    r"terraform\s+destroy",
    r"git\s+reset\s+--hard",
    r"pkill\s+-9",
    r"kill\s+-9",
]

# Tool-level risk table: tool_name → (risk, reason)
_TOOL_RISK: Dict[str, Tuple[OpsRiskLevel, str]] = {
    # CRITICAL
    "docker_compose": (OpsRiskLevel.HIGH, "Manages multi-container stacks"),
    # HIGH
    "docker_exec": (OpsRiskLevel.HIGH, "Executes commands inside containers"),
    "docker_build": (OpsRiskLevel.MEDIUM, "Builds Docker images"),
    # MEDIUM
    "git_commit": (OpsRiskLevel.MEDIUM, "Creates a Git commit"),
    "write_file": (OpsRiskLevel.MEDIUM, "Writes to filesystem"),
    "edit_file": (OpsRiskLevel.MEDIUM, "Modifies existing file"),
    # LOW (read-only)
    "git_status": (OpsRiskLevel.LOW, "Read-only Git status"),
    "git_diff": (OpsRiskLevel.LOW, "Read-only Git diff"),
    "git_log": (OpsRiskLevel.LOW, "Read-only Git log"),
    "git_branch": (OpsRiskLevel.LOW, "Read-only branch list"),
    "docker_ps": (OpsRiskLevel.LOW, "Read-only container list"),
    "docker_images": (OpsRiskLevel.LOW, "Read-only image list"),
    "docker_logs": (OpsRiskLevel.LOW, "Read-only container logs"),
    "read_file": (OpsRiskLevel.LOW, "Read-only file access"),
    "list_directory": (OpsRiskLevel.LOW, "Read-only directory listing"),
    "system_resources": (OpsRiskLevel.LOW, "Read-only system metrics"),
    "service_health": (OpsRiskLevel.LOW, "Read-only health check"),
    "check_port": (OpsRiskLevel.LOW, "Read-only port check"),
    "process_info": (OpsRiskLevel.LOW, "Read-only process info"),
}

# Minimum risk level that requires confirmation (configurable)
_CONFIRMATION_THRESHOLD = OpsRiskLevel.HIGH


def _classify_shell_command(command: str) -> Tuple[OpsRiskLevel, str]:
    """Classify risk of a raw shell command string."""
    for pattern in _CRITICAL_SHELL_PATTERNS:
        if re.search(pattern, command, re.IGNORECASE):
            return OpsRiskLevel.CRITICAL, f"Matches critical pattern: {pattern}"
    for pattern in _HIGH_SHELL_PATTERNS:
        if re.search(pattern, command, re.IGNORECASE):
            return OpsRiskLevel.HIGH, f"Matches high-risk pattern: {pattern}"
    return OpsRiskLevel.MEDIUM, "Shell command with side effects"


def audit_tool_call(
    tool_name: str,
    tool_args: Dict[str, Any],
    *,
    confirmation_threshold: OpsRiskLevel = _CONFIRMATION_THRESHOLD,
) -> OpsAuditResult:
    """
    Classify the risk of an Ops tool call.

    Args:
        tool_name: Name of the tool being called.
        tool_args: Arguments passed to the tool.
        confirmation_threshold: Minimum risk level that sets blocked=True.

    Returns:
        OpsAuditResult with risk classification and blocked flag.
    """
    warnings: List[str] = []

    # Special handling for shell commands
    if tool_name == "run_shell_command":
        command = tool_args.get("command", "")
        risk, reason = _classify_shell_command(command)
        if risk == OpsRiskLevel.CRITICAL:
            warnings.append(
                f"⚠️  CRITICAL: '{command[:80]}' may cause irreversible data loss"
            )
    else:
        risk, reason = _TOOL_RISK.get(
            tool_name, (OpsRiskLevel.MEDIUM, "Unknown Ops tool")
        )

    # Escalate git_commit to HIGH if --force or --amend
    if tool_name == "git_commit":
        msg = str(tool_args.get("message", ""))
        if "--force" in msg or "--amend" in msg:
            risk = OpsRiskLevel.HIGH
            reason = "git commit with --force or --amend"

    risk_order = [
        OpsRiskLevel.LOW,
        OpsRiskLevel.MEDIUM,
        OpsRiskLevel.HIGH,
        OpsRiskLevel.CRITICAL,
    ]
    blocked = risk_order.index(risk) >= risk_order.index(confirmation_threshold)

    result = OpsAuditResult(
        tool_name=tool_name,
        risk_level=risk,
        reason=reason,
        blocked=blocked,
        warnings=warnings,
    )

    if blocked:
        logger.warning(f"OpsAudit: '{tool_name}' blocked (risk={risk.value}): {reason}")
    else:
        logger.debug(f"OpsAudit: '{tool_name}' allowed (risk={risk.value})")

    return result


def format_audit_warning(result: OpsAuditResult) -> str:
    """Return a human-readable warning string for display before confirmation."""
    lines = [
        f"⚠️  Security Audit — {result.risk_level.value.upper()} risk",
        f"   Tool: {result.tool_name}",
        f"   Reason: {result.reason}",
    ]
    for w in result.warnings:
        lines.append(f"   {w}")
    lines.append("   Proceed? (y/N)")
    return "\n".join(lines)
