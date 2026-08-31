"""SecurityGuard plugin — blocks dangerous shell commands before execution.

Hooks used: ``BEFORE_TOOL_CALL``

Behaviour:
- Intercepts every call to shell/command tools (``run_shell_command``,
  ``run_command``, ``execute_shell``, ``shell``).
- Checks the command string against a curated list of high-risk patterns
  (recursive deletes, force-pushes, disk wipes, privilege escalation, etc.).
- Cancels the call and logs a warning when a dangerous pattern is matched.
- Patterns are case-insensitive and matched as substrings unless anchored.

The guard is intentionally conservative: it only blocks unambiguously
dangerous operations.  It does *not* replace the existing ``ToolPolicies``
confirmation system — both layers are active simultaneously.
"""

from __future__ import annotations

import logging
import re
from typing import Callable

from aura_cli.application.extensions.plugins import (
    AuraPlugin,
    PluginContext,
    PluginHook,
    PluginMetadata,
)

logger = logging.getLogger(__name__)

# Shell tool names this guard watches
_SHELL_TOOLS = frozenset(
    {"run_shell_command", "run_command", "execute_shell", "shell", "run_script"}
)

# (pattern, reason) pairs — compiled once at import time
_DANGEROUS_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"rm\s+-[^\s]*r[^\s]*\s+/", re.I), "recursive delete from root"),
    (re.compile(r"rm\s+-rf\s+[~/$]", re.I), "recursive force-delete of home/root"),
    (re.compile(r":\s*\(\)\s*\{\s*:\s*\|\s*:", re.I), "fork bomb"),
    (re.compile(r">\s*/dev/(sda|hda|nvme|disk)", re.I), "raw disk overwrite"),
    (re.compile(r"dd\s+.*of=/dev/(sda|hda|nvme|disk)", re.I), "dd disk wipe"),
    (re.compile(r"mkfs\b", re.I), "filesystem format"),
    (re.compile(r"git\s+push\s+.*--force\b", re.I), "force-push to remote"),
    (re.compile(r"git\s+reset\s+--hard\s+HEAD~[2-9]", re.I), "large hard reset"),
    (re.compile(r"chmod\s+-R\s+777\s+/", re.I), "recursive world-writable on /"),
    (re.compile(r"chown\s+-R\s+\S+\s+/(?!\S)", re.I), "recursive chown on /"),
    (re.compile(r"sudo\s+rm\b", re.I), "sudo delete"),
    (re.compile(r"sudo\s+dd\b", re.I), "sudo dd"),
    (re.compile(r"curl\s+.*\|\s*(sudo\s+)?bash", re.I), "curl-pipe-to-bash"),
    (re.compile(r"wget\s+.*\|\s*(sudo\s+)?bash", re.I), "wget-pipe-to-bash"),
    (re.compile(r"npm\s+publish\b", re.I), "npm publish (production release)"),
    (re.compile(r"pip\s+install\s+.*--index-url\s+http://", re.I), "insecure pip source"),
]


class SecurityGuardPlugin(AuraPlugin):
    """Blocks dangerous shell commands before they are executed."""

    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="security_guard",
            version="1.0.0",
            description="Blocks dangerous shell commands before execution.",
            author="AuraCli Core Team",
        )

    def get_hooks(self) -> dict[PluginHook, Callable[[PluginContext], None]]:
        return {PluginHook.BEFORE_TOOL_CALL: self._on_before_tool_call}

    def _on_before_tool_call(self, context: PluginContext) -> None:
        tool_name: str = context.get("tool_name", "")
        if tool_name not in _SHELL_TOOLS:
            return

        command: str = (
            context.get("args", {}).get("command")
            or context.get("args", {}).get("cmd")
            or context.get("args", {}).get("script")
            or ""
        )
        if not command:
            return

        for pattern, reason in _DANGEROUS_PATTERNS:
            if pattern.search(command):
                logger.warning(
                    "SecurityGuard: blocked '%s' — matched dangerous pattern: %s",
                    command[:120],
                    reason,
                )
                context.cancel()
                context.set(
                    "block_reason",
                    f"SecurityGuard blocked this command ({reason}). "
                    "Review the command manually before running it.",
                )
                return
