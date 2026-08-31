"""Conversation use cases independent from model and UI adapters."""

from .budget import BudgetDecision, TokenBudget
from .context_pruner import (
    PrunedEntry,
    PruningConfig,
    PruningRule,
    estimate_pruning_savings,
    prune_context,
)
from .history import (
    append_tool_interaction,
    build_tool_result_response,
    summarize_tool_result,
)
from .prompt import (
    PreparedPrompt,
    estimate_context_tokens,
    filter_tool_schemas,
    prepare_prompt,
    sanitize_prompt_text,
)
from .provider_errors import (
    ProviderErrorKind,
    ProviderErrorResolution,
    friendly_provider_error,
    resolve_provider_error,
)

__all__ = [
    "BudgetDecision",
    "PreparedPrompt",
    "ProviderErrorKind",
    "ProviderErrorResolution",
    "PrunedEntry",
    "PruningConfig",
    "PruningRule",
    "TokenBudget",
    "append_tool_interaction",
    "build_tool_result_response",
    "estimate_context_tokens",
    "estimate_pruning_savings",
    "filter_tool_schemas",
    "friendly_provider_error",
    "prepare_prompt",
    "prune_context",
    "resolve_provider_error",
    "sanitize_prompt_text",
    "summarize_tool_result",
]
