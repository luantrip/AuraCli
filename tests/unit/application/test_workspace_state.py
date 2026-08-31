"""Workspace facade contracts."""

from unittest.mock import Mock

from aura_cli.application.workspace import WorkspaceState


def test_workspace_state_groups_one_resolved_workspace(tmp_path) -> None:
    context = Mock()
    state = WorkspaceState(
        project_root=tmp_path / "child" / "..",
        memory=Mock(),
        session=Mock(),
        context=context,
        notebook=Mock(),
        imagination=Mock(),
        checkpoint=Mock(),
    )

    assert state.project_root == tmp_path.resolve()
    assert state.conversation is context
