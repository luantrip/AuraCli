"""Behavioral tests for presentation-neutral interaction queries."""

from dataclasses import dataclass, field
from enum import Enum

from aura_cli.application.presentation import (
    export_interactions,
    filter_interactions,
    summarize_interactions,
)


class Status(Enum):
    SUCCESS = "success"
    ERROR = "error"


@dataclass
class Record:
    id: str
    timestamp: float
    prompt: str
    response: str | None = None
    status: Status = Status.SUCCESS
    prompt_tokens: int = 0
    generated_tokens: int = 0
    execution_time: float = 0.0
    tool_calls: list[dict] = field(default_factory=list)
    error: str | None = None


def test_filters_across_text_status_type_and_time() -> None:
    records = [
        Record("one", 20, "Deploy service", tool_calls=[{"name": "shell"}]),
        Record("two", 10, "Chat question", status=Status.ERROR, error="timeout"),
    ]

    assert filter_interactions(
        records, query="deploy", interaction_type="Tools", cutoff_timestamp=15
    ) == [records[0]]
    assert filter_interactions(records, query="TIMEOUT", status=Status.ERROR) == [
        records[1]
    ]


def test_summarizes_tokens_types_statuses_and_positive_timings() -> None:
    records = [
        Record("one", 1, "one", prompt_tokens=10, generated_tokens=5, execution_time=2),
        Record("two", 2, "two", status=Status.ERROR, tool_calls=[{}], execution_time=0),
    ]

    summary = summarize_interactions(records)

    assert summary == {
        "total": 2,
        "by_status": {"success": 1, "error": 1},
        "by_type": {"Chat": 1, "Tools": 1},
        "total_tokens": 15,
        "avg_execution_time": 2.0,
    }


def test_exports_json_csv_and_rejects_unknown_format() -> None:
    record = Record("record-1", 1, "prompt", response="response")

    assert '"id": "record-1"' in export_interactions([record], "json")
    assert "ID,Timestamp,Status" in export_interactions([record], "csv")
    assert export_interactions([record], "yaml") == ""
