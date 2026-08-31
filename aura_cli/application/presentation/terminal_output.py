"""Neutral querying and language hints for terminal output."""

from __future__ import annotations

from collections.abc import Iterable

_FILTER_KEYWORDS = {
    "error": ("error", "exception", "failed"),
    "warning": ("warning", "warn"),
    "info": ("info", "note"),
}


def detect_output_language(output: str) -> str:
    """Infer a syntax-highlighting language from output content."""
    normalized = output.casefold()
    if "error" in normalized or "traceback" in normalized:
        return "python"
    if "{" in output and "}" in output:
        return "json"
    if output.strip().startswith("<") and ">" in output:
        return "xml"
    return "text"


def query_output_lines(
    lines: Iterable[str], *, filter_type: str | None = None, query: str = ""
) -> list[str]:
    """Apply category and text filters while preserving legacy fallback semantics."""
    result = list(lines)
    keywords = _FILTER_KEYWORDS.get(filter_type or "")
    if keywords:
        matches = [
            line for line in result if any(word in line.casefold() for word in keywords)
        ]
        if matches:
            result = matches
    normalized_query = query.casefold()
    if normalized_query:
        result = [line for line in result if normalized_query in line.casefold()]
    return result
