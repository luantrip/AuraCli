"""UI-neutral token usage snapshot construction."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, Optional


@dataclass(frozen=True)
class TokenUsageSnapshot:
    used_tokens: int = 0
    total_tokens: int = 500_000
    model_name: str = "aura"
    prompt_tokens: int = 0
    completion_tokens: int = 0
    tool_call_count: int = 0
    message_count: int = 0
    tool_definitions_count: int = 0
    skills_count: int = 0
    mcp_server_count: int = 0
    extra_lines: list[str] = field(default_factory=list)


def build_token_usage_snapshot(
    stats: Any,
    *,
    token_budget_warning: int = 100_000,
    message_count: int = 0,
    tool_definitions: Optional[Iterable[Any]] = None,
    skills_count: int = 0,
    mcp_server_count: int = 0,
) -> TokenUsageSnapshot:
    """Normalize loosely shaped runtime statistics for any presentation adapter."""
    used = int(getattr(stats, "tokens_used", 0) or 0)
    tokens_by_model = getattr(stats, "tokens_by_model", None) or {}
    model = getattr(stats, "current_model", None) or next(iter(tokens_by_model), "aura")
    tool_count = 0
    if tool_definitions is not None:
        try:
            tool_count = len(tool_definitions)  # type: ignore[arg-type]
        except TypeError:
            tool_count = sum(1 for _ in tool_definitions)
    budget = max(int(token_budget_warning or 0), 1)
    return TokenUsageSnapshot(
        used_tokens=used,
        total_tokens=max(budget * 5, used, 1),
        model_name=str(model),
        prompt_tokens=int(getattr(stats, "prompt_tokens", 0) or 0),
        completion_tokens=int(getattr(stats, "completion_tokens", 0) or 0),
        tool_call_count=int(
            getattr(stats, "tool_calls", 0) or getattr(stats, "tools_used", 0) or 0
        ),
        message_count=message_count,
        tool_definitions_count=tool_count,
        skills_count=skills_count,
        mcp_server_count=mcp_server_count,
    )
