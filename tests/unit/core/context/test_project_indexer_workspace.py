"""Workspace-root contracts for the project indexer."""

from unittest.mock import patch

from aura_cli.core.context.project_indexer import (
    ProjectContextManager,
    handle_init_command,
)


def test_project_context_manager_default_uses_allowed_workspace(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()

    with patch(
        "aura_cli.core.tools.file_system.get_allowed_base_dir",
        return_value=workspace,
    ):
        manager = ProjectContextManager()

    assert manager.project_root == workspace.resolve()
    assert manager.aura_dir == (workspace / ".aura").resolve()


def test_handle_init_command_accepts_explicit_project_root(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    captured = {}

    class FakeManager:
        project_root = workspace.resolve()

    with (
        patch(
            "aura_cli.core.context.project_indexer.ProjectContextManager",
            side_effect=lambda root: (
                captured.__setitem__("root", root) or FakeManager()
            ),
        ),
        patch(
            "aura_cli.core.context.project_indexer.generate_file_tree",
            return_value="workspace/\n",
        ),
        patch(
            "aura_cli.core.context.project_indexer._identify_key_files",
            return_value=[],
        ),
    ):
        # The command should stop before any LLM or filesystem mutation when no
        # key files are identified; the assertion is only about root propagation.
        import asyncio

        result = asyncio.run(handle_init_command(project_root=workspace, max_files=1))

    assert captured["root"] == workspace
    assert result["status"] == "error"
