"""Tests for TUI ↔ SessionManager sync."""

import json
from pathlib import Path

import pytest

from aura_cli.core.sessions.session_manager import Session
from aura_cli.tui.services.tui_session_service import (
    export_session_jsonl,
    load_session_from_path,
    sync_tui_chat_to_session,
)
from aura_cli.tui.widgets.history.session_store import parse_session_json


def test_parse_session_json_reads_conversation(tmp_path: Path):
    path = tmp_path / "abc12345.json"
    path.write_text(
        json.dumps(
            {
                "id": "abc12345",
                "name": "Test",
                "created_at": "2026-01-01T12:00:00",
                "updated_at": "2026-01-02T12:00:00",
                "conversation_history": [
                    {"role": "user", "content": "hi"},
                    {"role": "assistant", "content": "hello"},
                ],
                "current_directory": "/proj",
            }
        ),
        encoding="utf-8",
    )
    entry = parse_session_json(path)
    assert entry is not None
    assert entry.session_id == "abc12345"
    assert entry.message_count == 2
    assert entry.cwd == "/proj"


def test_sync_tui_chat_uses_app_loop_workspace(tmp_path):
    from unittest.mock import MagicMock

    app = MagicMock()
    app.all_chat_messages = [{"sender": "User", "content": "hello"}]
    app.app_loop.project_root = tmp_path / "workspace"
    session = Session(
        id="sync01",
        name="Sync",
        created_at="2026-01-01T00:00:00",
        updated_at="2026-01-01T00:00:00",
    )

    sync_tui_chat_to_session(app, session)

    assert session.current_directory == str((tmp_path / "workspace").resolve())


def test_load_jsonl_bounds_imported_cwd_to_workspace(tmp_path):
    from unittest.mock import MagicMock, patch

    path = tmp_path / "jsonl-session.jsonl"
    path.write_text(
        json.dumps({"role": "user", "content": "hi", "cwd": "/outside"}) + "\n",
        encoding="utf-8",
    )
    manager = MagicMock(workspace_root=tmp_path / "workspace")
    manager.workspace_root.mkdir()

    with patch(
        "aura_cli.tui.services.tui_session_service.get_session_manager",
        return_value=manager,
    ):
        session = load_session_from_path(path)

    assert session is not None
    assert session.current_directory == str(manager.workspace_root.resolve())


def test_chat_to_history_mapping():
    from aura_cli.application.sessions import chat_messages_to_history

    hist = chat_messages_to_history(
        [{"sender": "User", "content": "q"}, {"sender": "Aura", "content": "a"}]
    )
    assert hist[0]["role"] == "user"
    assert hist[1]["role"] == "assistant"


def test_export_session_jsonl_preserves_previous_file_on_serialization_error(
    tmp_path: Path,
) -> None:
    session = Session(
        id="jsonl-session",
        name="JSONL",
        created_at="2026-01-01T00:00:00",
        updated_at="2026-01-01T00:00:00",
    )
    session.add_message("user", "hello")
    path = tmp_path / "jsonl-session.jsonl"
    export_session_jsonl(session, path)
    previous = path.read_text(encoding="utf-8")

    session.conversation_history.append({"role": "assistant", "content": object()})
    with pytest.raises(TypeError):
        export_session_jsonl(session, path)

    assert path.read_text(encoding="utf-8") == previous
    assert not list(tmp_path.glob(f".{path.name}.*.tmp"))
