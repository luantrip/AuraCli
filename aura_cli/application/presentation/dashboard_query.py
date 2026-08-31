"""Neutral filtering and sorting for tabular dashboards."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Iterable, Mapping


class SortOrder(Enum):
    NONE = "none"
    ASC = "asc"
    DESC = "desc"


@dataclass(frozen=True)
class DashboardFilter:
    column: str
    value: str
    operator: str = "contains"


def _matches(item: Mapping[str, Any], active_filter: DashboardFilter) -> bool:
    value = str(item.get(active_filter.column, "")).casefold()
    expected = active_filter.value.casefold()
    if active_filter.operator == "contains":
        return expected in value
    if active_filter.operator == "equals":
        return value == expected
    if active_filter.operator == "startswith":
        return value.startswith(expected)
    if active_filter.operator in {"gt", "lt"}:
        try:
            numeric_left, numeric_right = float(value), float(expected)
        except ValueError:
            return (
                value > expected if active_filter.operator == "gt" else value < expected
            )
        return (
            numeric_left > numeric_right
            if active_filter.operator == "gt"
            else numeric_left < numeric_right
        )
    return False


def query_dashboard_rows(
    rows: Iterable[dict[str, Any]],
    *,
    search: str = "",
    filters: Iterable[DashboardFilter] = (),
    sort_column: str | None = None,
    sort_order: SortOrder = SortOrder.NONE,
) -> list[dict[str, Any]]:
    """Apply full-text search, column filters and ordering to dashboard rows."""
    result = list(rows)
    normalized_search = search.casefold()
    if normalized_search:
        result = [
            item
            for item in result
            if any(
                normalized_search in str(value).casefold() for value in item.values()
            )
        ]
    for active_filter in filters:
        result = [item for item in result if _matches(item, active_filter)]
    if sort_column and sort_order is not SortOrder.NONE:
        result.sort(
            key=lambda item: item.get(sort_column, ""),
            reverse=sort_order is SortOrder.DESC,
        )
    return result
