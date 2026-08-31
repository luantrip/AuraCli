"""Strategy card injector for subagent system prompts.

``inject_card_into_prompt`` appends a structured strategy card block to any
system prompt so that subagents receiving the same base task diverge in their
reasoning approach.  The injected block is intentionally compact (≤ 800 chars)
to avoid consuming excessive context budget.
"""

from __future__ import annotations

from aura_cli.core.agents.strategy_deck import AgentCard

# ─── Template ────────────────────────────────────────────────────────────────

_CARD_TEMPLATE = """\

=== YOUR STRATEGY CARD ===
Reasoning mode: {reasoning_name}. {reasoning_how}
Workflow: {workflow_name}. {workflow_how}
Strategy: {strategy_name}. {strategy_how}
=== END OF CARD ===

Use this card for real: think in the reasoning mode, go through the workflow's
steps in order, and let the strategy settle every trade-off. A generic answer
with the card's label on top will not be useful.
"""


def inject_card_into_prompt(base_prompt: str, card: AgentCard) -> str:
    """Append a strategy card block to *base_prompt*.

    The card is appended at the end so it does not displace critical
    instructions that appear at the beginning of the prompt.

    Args:
        base_prompt: The original system or user prompt string.
        card: The ``AgentCard`` to inject.

    Returns:
        The combined prompt string with the card appended.
    """
    card_block = _CARD_TEMPLATE.format(
        reasoning_name=card.reasoning_name,
        reasoning_how=card.reasoning_how[:200],   # guard against very long entries
        workflow_name=card.workflow_name,
        workflow_how=card.workflow_how[:200],
        strategy_name=card.strategy_name,
        strategy_how=card.strategy_how[:200],
    )
    return base_prompt.rstrip() + "\n" + card_block


def strip_card_from_prompt(prompt: str) -> str:
    """Remove a previously injected card block from *prompt*.

    Useful when displaying a prompt to the user without the injected card.
    Returns the original prompt if no card block is found.
    """
    marker = "\n=== YOUR STRATEGY CARD ==="
    idx = prompt.find(marker)
    if idx == -1:
        return prompt
    return prompt[:idx].rstrip()
