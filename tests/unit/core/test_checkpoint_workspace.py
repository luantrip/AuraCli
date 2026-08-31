"""Workspace-root contracts for checkpoint operations."""

from types import SimpleNamespace
from unittest.mock import patch

from aura_cli.core.checkpoint.manager import CheckpointManager


def test_checkpoint_manager_derives_root_from_shadow_directory(tmp_path):
    shadow_dir = tmp_path / "workspace" / ".checkpoints"
    manager = CheckpointManager(shadow_dir=shadow_dir)

    assert manager.workspace_root == (tmp_path / "workspace").resolve()


def test_checkpoint_manager_without_arguments_uses_project_root_env(
    tmp_path, monkeypatch
):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    monkeypatch.setenv("AURA_PROJECT_ROOT", str(workspace))

    manager = CheckpointManager()

    assert manager.workspace_root == workspace.resolve()
    assert manager.shadow_dir == workspace / ".aura" / ".checkpoints"


def test_create_uses_workspace_root_as_git_worktree(tmp_path):
    workspace = tmp_path / "workspace"
    shadow_dir = tmp_path / "shadow"
    workspace.mkdir()
    shadow_dir.mkdir()
    manager = CheckpointManager(shadow_dir=shadow_dir, workspace_root=workspace / ".")
    manager.initialized = True
    manager._get_changed_files = lambda _env: []
    calls = [
        SimpleNamespace(returncode=0, stdout=""),
        SimpleNamespace(returncode=0, stdout=""),
        SimpleNamespace(returncode=0, stdout="abc12345\n"),
    ]

    with patch(
        "aura_cli.core.checkpoint.manager.subprocess.run",
        side_effect=calls,
    ) as run:
        checkpoint = manager.create("workspace checkpoint")

    assert checkpoint is not None
    assert all(
        call.kwargs["env"]["GIT_WORK_TREE"] == str(workspace.resolve())
        for call in run.call_args_list
    )


def test_restore_uses_workspace_root_as_git_worktree(tmp_path):
    workspace = tmp_path / "workspace"
    shadow_dir = tmp_path / "shadow"
    workspace.mkdir()
    shadow_dir.mkdir()
    manager = CheckpointManager(shadow_dir=shadow_dir, workspace_root=workspace)
    manager.initialized = True

    with patch("aura_cli.core.checkpoint.manager.subprocess.run") as run:
        success, state = manager.restore("abc12345")

    assert success is True
    assert state is None
    assert run.call_args.kwargs["env"]["GIT_WORK_TREE"] == str(workspace.resolve())
