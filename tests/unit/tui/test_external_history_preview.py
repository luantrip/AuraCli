import json

from aura_cli.tui.widgets.history.session_store import load_sessions


def test_history_store_can_include_discovered_external_sessions(tmp_path, monkeypatch) -> None:
    external = tmp_path / "grok-session"
    external.mkdir()
    (external / "updates.jsonl").write_text(
        json.dumps(
            {
                "params": {
                    "sessionId": "grok-1",
                    "update": {
                        "sessionUpdate": "user_message_chunk",
                        "content": {"type": "text", "text": "Olá"},
                    },
                }
            }
        ),
        encoding="utf-8",
    )
    (external / "summary.json").write_text(
        json.dumps({"info": {"id": "grok-1", "cwd": str(tmp_path)}}),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        "aura_cli.tui.widgets.history.session_store.discover_external_sessions",
        lambda provider: [
            type(
                "Candidate",
                (),
                {
                    "provider": "grok",
                    "session_id": "grok-1",
                    "path": external,
                    "cwd": str(tmp_path),
                },
            )()
        ]
        if provider == "grok"
        else [],
    )

    sessions = load_sessions(tmp_path / "aura", include_external=True)

    assert len(sessions) == 1
    assert sessions[0].external is True
    assert sessions[0].session_id == "grok:grok-1"
