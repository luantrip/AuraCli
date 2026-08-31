"""Explainable capability decisions for tool execution.

The broker is deliberately pure: it does not prompt, log, mutate policy state,
or execute tools. It only combines the already-canonical risk classification,
the task-local execution policy, and intervention availability into a decision
that the UI/executor can render or enforce.
"""

from __future__ import annotations

from dataclasses import dataclass

from aura_cli.application.tools.execution_policy import TaskExecutionPolicy


@dataclass(frozen=True)
class CapabilityDecision:
    """Explainable result of evaluating one tool capability."""

    allowed: bool
    requires_confirmation: bool
    reason: str
    risk_level: object | None = None


def _risk_value(risk_level: object | None) -> str | None:
    """Read an enum-like risk value without importing an outer layer."""
    if risk_level is None:
        return None
    value = getattr(risk_level, "value", risk_level)
    return value.casefold() if isinstance(value, str) else str(value).casefold()


def decide_tool_capability(
    risk_level: object | None,
    *,
    policy: TaskExecutionPolicy | None = None,
    adapter_available: bool = False,
    access_allowed: bool = True,
    access_reason: str | None = None,
) -> CapabilityDecision:
    """Combine access, risk, policy, and intervention into one decision.

    ``allowed`` means the tool may continue through the executor. A decision
    with ``requires_confirmation=True`` is allowed to reach the confirmation
    UI, but must not execute before the user approves it.
    """
    if not access_allowed:
        return CapabilityDecision(
            allowed=False,
            requires_confirmation=False,
            reason=access_reason or "Acesso negado pela política.",
            risk_level=risk_level,
        )

    risk_value = _risk_value(risk_level)
    if risk_value is None or risk_value == "low":
        return CapabilityDecision(
            allowed=True,
            requires_confirmation=False,
            reason="Ferramenta sem confirmação adicional.",
            risk_level=risk_level,
        )

    if policy and policy.auto_confirm:
        if risk_value in {"high", "critical"} and not policy.allow_dangerous:
            if policy.fail_closed_without_adapter and not adapter_available:
                return CapabilityDecision(
                    allowed=False,
                    requires_confirmation=False,
                    reason=(
                        "Operação de alto risco rejeitada: adapter de intervenção "
                        "ausente."
                    ),
                    risk_level=risk_level,
                )
            return CapabilityDecision(
                allowed=True,
                requires_confirmation=True,
                reason="Auto-confirmação não cobre operações de alto risco.",
                risk_level=risk_level,
            )
        return CapabilityDecision(
            allowed=True,
            requires_confirmation=False,
            reason="Auto-confirmação autorizada pela policy task-local.",
            risk_level=risk_level,
        )

    return CapabilityDecision(
        allowed=True,
        requires_confirmation=True,
        reason="Confirmação explícita necessária para esta operação.",
        risk_level=risk_level,
    )


__all__ = ["CapabilityDecision", "decide_tool_capability"]
