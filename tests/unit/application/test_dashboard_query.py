"""Tests for neutral tabular dashboard queries."""

from aura_cli.application.presentation.dashboard_query import (
    DashboardFilter,
    SortOrder,
    query_dashboard_rows,
)


def test_combines_search_filter_and_descending_sort() -> None:
    rows = [
        {"name": "Alpha API", "score": 2},
        {"name": "Beta API", "score": 5},
        {"name": "Site", "score": 9},
    ]
    result = query_dashboard_rows(
        rows,
        search="api",
        filters=[DashboardFilter("score", "1", "gt")],
        sort_column="score",
        sort_order=SortOrder.DESC,
    )
    assert [item["name"] for item in result] == ["Beta API", "Alpha API"]


def test_supports_text_operators_and_unknown_operator() -> None:
    rows = [{"name": "Alpha"}, {"name": "Beta"}]
    assert query_dashboard_rows(rows, filters=[DashboardFilter("name", "alp")]) == [
        rows[0]
    ]
    assert query_dashboard_rows(
        rows, filters=[DashboardFilter("name", "beta", "equals")]
    ) == [rows[1]]
    assert (
        query_dashboard_rows(rows, filters=[DashboardFilter("name", "a", "unknown")])
        == []
    )
