"""Deterministic unit economics for the native founder skill."""

from __future__ import annotations

import math
from typing import Any


class EconomicsError(ValueError):
    """Raised when business numbers are incomplete or inconsistent."""


def _sum_costs(items: Any, field: str) -> float:
    if items is None:
        return 0.0
    if not isinstance(items, list):
        raise EconomicsError(f"{field} must be a list")
    total = 0.0
    for index, item in enumerate(items):
        if not isinstance(item, dict) or "cost" not in item:
            raise EconomicsError(f"{field}[{index}] needs a cost")
        try:
            cost = float(item["cost"])
        except (TypeError, ValueError) as exc:
            raise EconomicsError(f"{field}[{index}].cost is not numeric") from exc
        if not math.isfinite(cost) or cost < 0:
            raise EconomicsError(
                f"{field}[{index}].cost must be finite and non-negative"
            )
        total += cost
    return total


def analyse_economics(  # noqa: C901
    spec: dict[str, Any], price: float | None = None, volume: float = 1.0
) -> dict[str, Any]:
    """Calculate contribution, break-even, ramp profit and red flags."""
    if volume <= 0 or not math.isfinite(volume):
        raise EconomicsError("volume must be finite and above zero")
    if "price" not in spec and price is None:
        raise EconomicsError("price is required")
    try:
        unit_price = float(spec["price"] if price is None else price)
        days = float(spec.get("days_per_month", 30))
    except (TypeError, ValueError) as exc:
        raise EconomicsError("price and days_per_month must be numeric") from exc
    if unit_price <= 0 or days <= 0:
        raise EconomicsError("price and days_per_month must be above zero")
    variable = _sum_costs(spec.get("variable", []), "variable")
    fixed = _sum_costs(spec.get("fixed_monthly", []), "fixed_monthly")
    startup = _sum_costs(spec.get("startup", []), "startup")
    if "plan_per_day" not in spec and "ramp_per_day" not in spec:
        raise EconomicsError("plan_per_day or ramp_per_day is required")
    plan = float(spec.get("plan_per_day", 0)) * volume
    ramp = spec.get("ramp_per_day")
    if ramp is None:
        ramp = [plan] * 12
    elif len(ramp) != 12:
        raise EconomicsError("ramp_per_day must contain 12 values")
    else:
        ramp = [float(item) * volume for item in ramp]
    if any(item < 0 or not math.isfinite(item) for item in ramp):
        raise EconomicsError("ramp_per_day values must be finite and non-negative")
    if not plan:
        plan = ramp[-1]
    if plan < 0:
        raise EconomicsError("plan_per_day must be non-negative")
    contribution = unit_price - variable
    break_even = math.inf if contribution <= 0 else fixed / (contribution * days)
    plan_units = plan * days
    margin = (
        (contribution - fixed / plan_units) / unit_price if plan_units else -math.inf
    )
    months = []
    cumulative = -startup
    payback = None
    for month, per_day in enumerate(ramp, 1):
        units = per_day * days
        revenue = units * unit_price
        profit = revenue - units * variable - fixed
        cumulative += profit
        payback = month if payback is None and cumulative >= 0 else payback
        months.append(
            {
                "month": month,
                "per_day": per_day,
                "units": units,
                "revenue": revenue,
                "profit": profit,
                "cumulative": cumulative,
            }
        )
    capacity = spec.get("capacity_per_day")
    flags = []
    if contribution <= 0:
        flags.append("unit price does not cover variable cost")
    if capacity is not None and break_even > float(capacity):
        flags.append("break-even exceeds daily capacity")
    if capacity is not None and plan > float(capacity):
        flags.append("planned volume exceeds daily capacity")
    year_profit = sum(item["profit"] for item in months)
    if year_profit < 0:
        flags.append("year one operating profit is negative")
    if payback is None:
        flags.append("startup spend is not recovered in year one")
    return {
        "business": spec.get("business", ""),
        "unit": spec.get("unit", "unit"),
        "price": unit_price,
        "variable_per_unit": variable,
        "contribution": contribution,
        "contribution_pct": contribution / unit_price,
        "fixed_monthly": fixed,
        "startup": startup,
        "plan_per_day": plan,
        "margin_at_plan": margin,
        "breakeven_per_day": break_even,
        "capacity_per_day": capacity,
        "year1_revenue": sum(item["revenue"] for item in months),
        "year1_profit": year_profit,
        "year1_after_startup": year_profit - startup,
        "payback_month": payback,
        "cash_needed": -min([-startup] + [item["cumulative"] for item in months]),
        "months": months,
        "flags": flags,
    }
