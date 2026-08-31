"""Pure request and result policy for web-search tools."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence


@dataclass(frozen=True, slots=True)
class WebSearchRequest:
    query: str
    num_results: int

    @property
    def cache_key(self) -> str:
        return f"{self.query}:{self.num_results}"


def normalize_web_search_request(query: str, num_results: int) -> WebSearchRequest:
    """Normalize input and reject invalid network requests before invoking adapters."""
    normalized = " ".join(query.split())
    if not normalized:
        raise ValueError("search query must not be empty")
    if not 1 <= num_results <= 50:
        raise ValueError("num_results must be between 1 and 50")
    return WebSearchRequest(normalized, num_results)


def format_web_search_results(results: Sequence[Mapping[str, Any]]) -> str:
    """Project backend-neutral search records into the tool response."""
    return "\n".join(
        f"{index}. {result.get('title', '')}\n"
        f"   Link: {result.get('url', '')}\n"
        f"   Descrição: {result.get('description', '')}\n"
        for index, result in enumerate(results, 1)
    )
