"""Workspace-root contracts for persistent sessions."""

import json
import os

import pytest

from aura_cli.core.sessions.session_manager import SessionManager


def test_create_session_uses_resolved_workspace_root(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    storage = tmp_path / "sessions"
    manager = SessionManager(storage_path=storage, workspace_root=workspace / ".")

    session = manager.create_session("workspace-session")

    assert manager.workspace_root == workspace.resolve()
    assert session.current_directory == str(workspace.resolve())


def test_load_session_normalizes_historical_directory_to_workspace(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    storage = tmp_path / "sessions"
    storage.mkdir()
    session_id = "legacy01"
    (storage / f"{session_id}.json").write_text(
        json.dumps(
            {
                "id": session_id,
                "name": "legacy",
                "created_at": "2026-01-01T00:00:00",
                "updated_at": "2026-01-01T00:00:00",
                "current_directory": "/outside/old-project",
            }
        ),
        encoding="utf-8",
    )

    session = SessionManager(
        storage_path=storage, workspace_root=workspace
    ).load_session(session_id)

    assert session is not None
    assert session.current_directory == str(workspace.resolve())


def test_legacy_manager_without_workspace_preserves_directory(tmp_path):
    storage = tmp_path / "sessions"
    manager = SessionManager(storage_path=storage)
    historical = "/outside/old-project"
    data = {
        "id": "legacy02",
        "name": "legacy",
        "current_directory": historical,
    }
    (storage / "legacy02.json").write_text(json.dumps(data), encoding="utf-8")

    session = manager.load_session("legacy02")

    assert session is not None
    assert session.current_directory == historical


def test_session_storage_and_files_are_private(tmp_path):
    storage = tmp_path / "sessions"
    manager = SessionManager(storage_path=storage)
    session = manager.create_session("private")

    assert os.stat(storage).st_mode & 0o777 == 0o700
    assert os.stat(storage / f"{session.id}.json").st_mode & 0o777 == 0o600


def test_switching_workspace_clears_active_session(tmp_path):
    first = tmp_path / "first"
    second = tmp_path / "second"
    first.mkdir()
    second.mkdir()
    manager = SessionManager(storage_path=tmp_path / "sessions", workspace_root=first)
    manager.create_session("first")

    manager.set_workspace_root(second)

    assert manager.workspace_root == second.resolve()
    assert manager.current_session is None


def test_symlink_workspace_is_rejected(tmp_path):
    target = tmp_path / "target"
    target.mkdir()
    link = tmp_path / "link"
    link.symlink_to(target, target_is_directory=True)

    with pytest.raises(ValueError, match="real directory"):
        SessionManager(storage_path=tmp_path / "sessions", workspace_root=link)
