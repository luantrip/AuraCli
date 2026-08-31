"""Tests for session history store."""

from pathlib import Path

from aura_cli.tui.widgets.history.session_store import parse_session_file


def test_parse_session_file_extracts_messages(tmp_path: Path):
    path = tmp_path / "sess1.jsonl"
    path.write_text(
        '{"role": "user", "content": "hello", "cwd": "/proj"}\n'
        '{"role": "assistant", "content": "hi"}\n',
        encoding="utf-8",
    )
    entry = parse_session_file(path)
    assert entry is not None
    assert entry.session_id == "sess1"
    assert entry.message_count == 2
    assert entry.first_message == "hello"
    assert entry.cwd == "/proj"
    assert "hello" in entry.search_blob
