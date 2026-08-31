import json

from aura_cli.core.sessions.external_import import (
    import_external_session,
    inspect_external_session,
)
from aura_cli.core.sessions.session_manager import SessionManager


def test_import_external_jsonl_creates_read_only_historical_session(tmp_path) -> None:
    source = tmp_path / "updates.jsonl"
    source.write_text(
        "\n".join(
            [
                json.dumps({"role": "user", "content": "Analise"}),
                json.dumps({"role": "assistant", "content": "Resultado"}),
                json.dumps({"type": "tool_call", "name": "shell"}),
            ]
        ),
        encoding="utf-8",
    )
    manager = SessionManager(storage_path=tmp_path / "sessions", workspace_root=tmp_path)

    session = import_external_session(manager, f"file:{source}")

    assert session.id
    assert session.tags == ["imported", "jsonl"]
    assert len(session.conversation_history) == 2
    report = session.context["external_import"]
    assert report["skipped_events"] == 1
    assert manager.load_session(session.id).name == session.name


def test_import_grok_directory_merges_summary_metadata(tmp_path) -> None:
    source = tmp_path / "grok-session"
    source.mkdir()
    (source / "updates.jsonl").write_text(
        json.dumps(
            {
                "params": {
                    "sessionId": "grok-123",
                    "update": {
                        "sessionUpdate": "user_message_chunk",
                        "content": {"type": "text", "text": "Oi"},
                    },
                }
            }
        ),
        encoding="utf-8",
    )
    (source / "summary.json").write_text(
        json.dumps(
            {
                "info": {"id": "grok-123", "cwd": "/historical/project"},
                "current_model_id": "grok-4.7",
                "generated_title": "Sessão Grok",
            }
        ),
        encoding="utf-8",
    )

    inspected = inspect_external_session(str(source))

    assert inspected.source_session_id == "grok-123"
    assert inspected.cwd == "/historical/project"
    assert inspected.model == "grok-4.7"
    assert inspected.name == "Sessão Grok"
