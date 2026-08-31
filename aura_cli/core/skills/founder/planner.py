"""Business-plan verdicts built from native founder artifacts."""

from __future__ import annotations

from typing import Any


def compile_plan(
    economics: dict[str, Any],
    panel: dict[str, Any] | None = None,
    minimum_buy_rate: float = 0.25,
) -> dict[str, Any]:
    """Compute a transparent Profitable, Not yet or Incomplete verdict."""
    if minimum_buy_rate < 0 or minimum_buy_rate > 1:
        raise ValueError("minimum_buy_rate must be between zero and one")
    checks = {
        "unit_is_profitable": economics.get("contribution", 0) > 0,
        "year_one_is_profitable": economics.get("year1_after_startup", 0) >= 0,
        "no_red_flags": not economics.get("flags"),
    }
    if panel is None:
        return {"verdict": "Incomplete", "checks": checks, "missing": ["panel"]}
    checks["panel_buy_rate"] = float(panel.get("buy_rate", 0)) >= minimum_buy_rate
    verdict = "Profitable" if all(checks.values()) else "Not yet"
    return {"verdict": verdict, "checks": checks, "missing": []}
