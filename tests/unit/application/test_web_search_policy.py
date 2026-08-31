"""Headless web-search policy tests."""

import pytest

from aura_cli.application.tools.web_search_policy import (
    format_web_search_results,
    normalize_web_search_request,
)


def test_request_normalizes_query_and_builds_stable_cache_key() -> None:
    request = normalize_web_search_request("  python   async  ", 5)
    assert request.query == "python async"
    assert request.cache_key == "python async:5"


@pytest.mark.parametrize("query,count", [("", 5), ("x", 0), ("x", 51)])
def test_request_rejects_invalid_network_work(query: str, count: int) -> None:
    with pytest.raises(ValueError):
        normalize_web_search_request(query, count)


def test_result_projection_is_backend_neutral() -> None:
    assert (
        format_web_search_results(
            [{"title": "Aura", "url": "https://example.test", "description": "CLI"}]
        )
        == "1. Aura\n   Link: https://example.test\n   Descrição: CLI\n"
    )
