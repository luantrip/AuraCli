"""Contracts and selection policies for command-backed hooks."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import fnmatch
import json
from typing import Any, Optional, Sequence


class HookEvent(Enum):
    AGENT_SPAWN = "agentSpawn"
    USER_PROMPT = "userPromptSubmit"
    PRE_TOOL = "preToolUse"
    POST_TOOL = "postToolUse"
    STOP = "stop"


@dataclass(frozen=True)
class HookResult:
    exit_code: int
    stdout: str = ""
    stderr: str = ""
    blocked: bool = False

    @property
    def success(self) -> bool:
        return self.exit_code == 0

    @property
    def should_block(self) -> bool:
        return self.exit_code == 2


@dataclass(frozen=True)
class CommandHook:
    event: HookEvent
    command: Sequence[str]
    matcher: Optional[str] = None
    timeout_ms: int = 30000
    cache_ttl_seconds: int = 0

    def __post_init__(self) -> None:
        if self.timeout_ms <= 0:
            raise ValueError("Hook timeout must be positive")
        if self.cache_ttl_seconds < 0:
            raise ValueError("Hook cache TTL cannot be negative")


def hook_matches(hook: CommandHook, context: dict[str, Any]) -> bool:
    """Return whether a command hook applies to the current tool context."""
    if not hook.matcher:
        return True
    tool_name = str(context.get("tool_name", ""))
    if hook.matcher == tool_name:
        return True
    if "*" in hook.matcher:
        return fnmatch.fnmatch(tool_name, hook.matcher)
    if hook.matcher.startswith("@"):
        if "/" in hook.matcher:
            return hook.matcher == tool_name
        return tool_name.startswith(f"@{hook.matcher[1:]}/")
    return False


def hook_cache_key(hook: CommandHook, context: dict[str, Any]) -> str:
    """Build a stable cache key independent of dictionary insertion order."""
    return "|".join(
        (
            hook.event.value,
            json.dumps(list(hook.command), ensure_ascii=False),
            json.dumps(context, sort_keys=True, ensure_ascii=False, default=str),
        )
    )
