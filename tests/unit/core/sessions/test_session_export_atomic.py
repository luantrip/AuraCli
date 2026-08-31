"""Atomic session export contracts."""

import json
from pathlib import Path

from aura_cli.core.sessions.session_manager import SessionManager


def test_export_session_preserves_existing_file_when_replace_fails(
    tmp_path, monkeypatch
):
    storage = tmp_path / "sessions"
    manager = SessionManager(storage_path=storage)
    session = manager.create_session("atomic-export")
    destination = tmp_path / "export.json"
    original = {"sentinel": "keep-me"}
    destination.write_text(json.dumps(original), encoding="utf-8")

    def fail_replace(_source: Path, _destination: Path) -> None:
        raise OSError("simulated replace failure")

    monkeypatch.setattr(
        "aura_cli.core.sessions.session_manager.os.replace", fail_replace
    )

    assert manager.export_session(session.id, str(destination)) is False
    assert json.loads(destination.read_text(encoding="utf-8")) == original
    assert list(tmp_path.glob(".export.json.*.tmp")) == []
