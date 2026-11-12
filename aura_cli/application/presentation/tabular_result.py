"""Framework-neutral classification of tool results as tabular data.

Some tools return a homogeneous list of records (e.g. cloud instances, docker
containers, health checks). Presentation surfaces can render those as a table
instead of raw JSON. This module decides — WITHOUT importing any UI framework —
whether a result qualifies and projects it into ordered rows + columns, so both
the Rich CLI and the Textual TUI can materialize the same decision.

Design rules:
* No Rich/Textual imports here (neutral policy layer).
* A result qualifies only when it is a non-empty list of mappings that share a
  stable, primitive-valued schema. Nested/irregular data falls back to JSON.
* Column order follows first-row insertion order, unioned with later rows.
* Values are coerced to display strings here so the materializer stays dumb.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

# Bound how much we will turn into a table; larger results stay as JSON/preview.
_MAX_ROWS = 200
_MAX_COLUMNS = 12


@dataclass(frozen=True)
class TabularResult:
    """An ordered table projection of a tool result."""

    columns: tuple[str, ...]
    rows: tuple[tuple[str, ...], ...]


def _is_primitive(value: Any) -> bool:
    return value is None or isinstance(value, (str, int, float, bool))


def _coerce(value: Any) -> str:
    if value is None:
        return "-"
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def as_tabular_result(result: Any) -> TabularResult | None:
    """Return a table projection when ``result`` is homogeneous records.

    Returns None when the result is not a clean list of flat mappings, so the
    caller falls back to its default (JSON/text) rendering.
    """
    # Must be a concrete sequence of mappings (not a string/bytes).
    if isinstance(result, (str, bytes, Mapping)) or not isinstance(result, Sequence):
        return None
    records = list(result)
    if not records or len(records) > _MAX_ROWS:
        return None
    if not all(isinstance(item, Mapping) for item in records):
        return None

    # Columns: first-row order, unioned with keys seen later (stable append).
    columns: list[str] = []
    seen: set[str] = set()
    for record in records:
        for key in record:
            key_str = str(key)
            if key_str not in seen:
                seen.add(key_str)
                columns.append(key_str)
    if not columns or len(columns) > _MAX_COLUMNS:
        return None

    # Every value must be primitive (flat records only) for a clean table.
    for record in records:
        for value in record.values():
            if not _is_primitive(value):
                return None

    rows = tuple(
        tuple(_coerce(record.get(column)) for column in columns)
        for record in records
    )
    return TabularResult(columns=tuple(columns), rows=rows)


__all__ = ["TabularResult", "as_tabular_result"]
