"""TUI adapter for the canonical token usage snapshot."""

from __future__ import annotations

from typing import Any, Optional

from aura_cli.application.observability.token_usage import (
    TokenUsageSnapshot,
)
from aura_cli.application.observability.token_usage import (
    build_token_usage_snapshot as build_application_snapshot,
)


def build_token_usage_snapshot(
    stats: Any,
    *,
    app_loop: Optional[Any] = None,
    message_count: int = 0,
) -> TokenUsageSnapshot:
    """Collect configured budget/tool definitions and delegate normalization."""
    from aura_cli.core.config import get_config_manager

    try:
        budget = int(get_config_manager().get("token_budget_warning") or 100_000)
    except Exception:
        budget = 1
    tools = None
    if app_loop is not None:
        registry = getattr(app_loop, "tool_registry", None)
        if registry is not None:
            tools = getattr(registry, "tools", None) or getattr(
                registry, "_tools", None
            )
    return build_application_snapshot(
        stats,
        token_budget_warning=budget,
        message_count=message_count,
        tool_definitions=tools,
    )


__all__ = ["TokenUsageSnapshot", "build_token_usage_snapshot"]
