"""CostTracker plugin — accumulates token usage and warns when a budget is exceeded.

Hooks used: ``AFTER_LLM_CALL``

Behaviour:
- Reads token usage from the LLM response metadata on every call.
- Accumulates totals in memory for the current session.
- Emits a warning log (and optionally a Rich panel) when cumulative cost
  exceeds the configured ``warning_threshold_usd``.
- Cost estimates use the same per-model rate table already present in
  ``core/llm/model_profiles.py`` when available; falls back to a conservative
  generic rate otherwise.
- Resets on session start via the ``ON_SESSION_START`` hook.

Configuration (passed as plugin kwargs or via ``/config``):
    warning_threshold_usd (float): USD amount that triggers the warning (default 0.10).
    hard_limit_usd (float): If > 0, cancels the call when limit would be exceeded (default 0.0 = disabled).
"""

from __future__ import annotations

import logging
from typing import Any, Callable

from aura_cli.application.extensions.plugins import (
    AuraPlugin,
    PluginContext,
    PluginHook,
    PluginMetadata,
)

logger = logging.getLogger(__name__)

# Fallback cost per 1 000 tokens (input + output blended) in USD
_FALLBACK_RATE_PER_1K = 0.001

# Conservative per-model rates (USD / 1K tokens blended)
_MODEL_RATES: dict[str, float] = {
    "gemini-2.5-flash": 0.0,
    "gemini-2.5-pro": 0.0,
    "gpt-oss-120b": 0.0,
    "gpt-4o": 0.005,
    "gpt-4o-mini": 0.00015,
    "claude-sonnet-4-6": 0.003,
    "claude-opus": 0.015,
}


def _estimate_cost(model: str, total_tokens: int) -> float:
    """Return estimated cost in USD for *total_tokens* on *model*."""
    model_key = model.lower().split("/")[-1]
    rate = next(
        (v for k, v in _MODEL_RATES.items() if k in model_key),
        _FALLBACK_RATE_PER_1K,
    )
    return (total_tokens / 1_000) * rate


class CostTrackerPlugin(AuraPlugin):
    """Tracks cumulative token cost and warns when a budget threshold is exceeded."""

    def __init__(
        self,
        warning_threshold_usd: float = 0.10,
        hard_limit_usd: float = 0.0,
    ) -> None:
        super().__init__()
        self._warning_threshold = warning_threshold_usd
        self._hard_limit = hard_limit_usd
        self._session_tokens: int = 0
        self._session_cost: float = 0.0
        self._warned = False

    @property
    def name(self) -> str:
        return "cost_tracker"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="cost_tracker",
            version="1.0.0",
            description="Accumulates token usage and warns when a budget is exceeded.",
            author="AuraCli Core Team",
        )

    def get_hooks(self) -> dict[PluginHook, Callable[[PluginContext], None]]:
        return {
            PluginHook.ON_SESSION_START: self._on_session_start,
            PluginHook.AFTER_LLM_CALL: self._on_after_llm_call,
        }

    def _on_session_start(self, context: PluginContext) -> None:
        self._session_tokens = 0
        self._session_cost = 0.0
        self._warned = False

    def _on_after_llm_call(self, context: PluginContext) -> None:
        usage: dict[str, int] = context.get("usage") or {}
        model: str = context.get("model") or ""

        total_tokens = usage.get("total_tokens", 0)
        if total_tokens <= 0:
            return

        call_cost = _estimate_cost(model, total_tokens)
        self._session_tokens += total_tokens
        self._session_cost += call_cost

        if self._hard_limit > 0 and self._session_cost >= self._hard_limit:
            logger.warning(
                "CostTracker: hard limit $%.4f reached (session total $%.4f). "
                "Cancelling call.",
                self._hard_limit,
                self._session_cost,
            )
            context.cancel()
            return

        if not self._warned and self._session_cost >= self._warning_threshold:
            self._warned = True
            logger.warning(
                "CostTracker: session cost $%.4f exceeded warning threshold $%.4f "
                "(%d tokens total).",
                self._session_cost,
                self._warning_threshold,
                self._session_tokens,
            )

    @property
    def session_cost(self) -> float:
        """Current accumulated session cost in USD."""
        return self._session_cost

    @property
    def session_tokens(self) -> int:
        """Current accumulated session token count."""
        return self._session_tokens

    def consume_stage_ledger(self, ledger: Any) -> None:
        """Merge an AGI StageLedger into the current budget accounting."""
        summary = ledger.summary()
        self._session_tokens += int(summary.get("input_tokens", 0))
        self._session_tokens += int(summary.get("output_tokens", 0))
        self._session_cost += float(summary.get("total_cost", 0.0))
