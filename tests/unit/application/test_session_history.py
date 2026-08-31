"""Session-history parsing and query contracts."""

from datetime import datetime, timedelta, timezone
from pathlib import Path

from aura_cli.application.sessions.history import (
    query_session_history,
    session_entry_from_jsonl,
    session_entry_from_snapshot,
)


def test_snapshot_supports_aware_timestamp_and_relative_time() -> None:
    entry = session_entry_from_snapshot(
        {
            "id": "s1",
            "updated_at": "2026-08-12T12:00:00Z",
            "current_directory": "/work/aura",
            "conversation_history": [
                {"role": "user", "content": "first"},
                {"role": "assistant", "content": "answer"},
                {"role": "user", "content": "last"},
            ],
        },
        path=Path("s1.json"),
        fallback_timestamp=datetime(2020, 1, 1),
    )

    assert entry.first_message == "first"
    assert entry.last_message == "last"
    assert entry.message_count == 3
    assert (
        entry.relative_time(datetime(2026, 8, 12, 12, 2, tzinfo=timezone.utc))
        == "2m atrá"
    )


def test_jsonl_ignores_malformed_lines_and_tracks_latest_cwd() -> None:
    entry = session_entry_from_jsonl(
        [
            "not-json",
            '{"role":"user","content":"Build API","cwd":"/one"}',
            '{"role":"assistant","content":"done","metadata":{"cwd":"/two"}}',
        ],
        path=Path("session.jsonl"),
        timestamp=datetime.now() - timedelta(days=1),
    )

    assert entry.message_count == 2
    assert entry.cwd == "/two"
    assert entry.short_cwd == "/two"


def test_query_matches_all_tokens_and_optional_workspace() -> None:
    first = session_entry_from_jsonl(
        ['{"role":"user","content":"Build API endpoint","cwd":"/one"}'],
        path=Path("one.jsonl"),
        timestamp=datetime.now(),
    )
    second = session_entry_from_jsonl(
        ['{"role":"user","content":"Build UI","cwd":"/two"}'],
        path=Path("two.jsonl"),
        timestamp=datetime.now(),
    )

    assert query_session_history([first, second], query="build endpoint") == [first]
    assert query_session_history([first, second], query="build", cwd="/two") == [second]
