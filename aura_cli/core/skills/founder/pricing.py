"""Van Westendorp price sensitivity analysis."""

from __future__ import annotations

from typing import Iterable

KEYS = ("too_cheap", "cheap", "expensive", "too_expensive")


class PricingError(ValueError):
    """Raised when too few or invalid price answers are supplied."""


def analyse_price_sensitivity(rows: Iterable[Iterable[float]]) -> dict[str, object]:
    """Return transparent price sensitivity summaries from ordered answers."""
    valid = []
    for row in rows:
        try:
            values = tuple(float(value) for value in row)
        except (TypeError, ValueError):
            continue
        if (
            len(values) == 4
            and all(value > 0 for value in values)
            and values[0] <= values[1] <= values[2] <= values[3]
        ):
            valid.append(values)
    if len(valid) < 5:
        raise PricingError(f"at least 5 ordered answers are required; got {len(valid)}")
    medians = {
        key: sorted(row[index] for row in valid)[len(valid) // 2]
        for index, key in enumerate(KEYS)
    }
    return {
        "answers": len(valid),
        "median": medians,
        "range": [medians["too_cheap"], medians["too_expensive"]],
    }
