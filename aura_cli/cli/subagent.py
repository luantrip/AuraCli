"""Compatibility shim — subagent runner moved to ``core/agents/subagent_runner``."""

from aura_cli.core.agents.subagent_runner import (  # noqa: F401
    MAX_TURNS,
    SUBAGENT_TOOLS,
    TIMEOUT_SECONDS,
    _invoke_subagent_tool_with_policy,
    run_subagent,
)
