"""Lightweight runtime doubles for AppLoop unit and integration tests."""

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock


def make_runtime_services(project_root: Path):
    """Return an explicit AppLoop runtime without initializing production services."""
    memory_service = Mock(notebook_manager=Mock())
    workspace = SimpleNamespace(
        project_root=project_root.resolve(),
        memory=memory_service,
        session=Mock(),
        context=Mock(),
        notebook=Mock(),
        imagination=Mock(),
        checkpoint=Mock(),
    )
    return SimpleNamespace(
        project_root=project_root.resolve(),
        workspace=workspace,
        memory_service=memory_service,
        session_state=workspace.session,
        notebook_service=workspace.notebook,
        imagination_manager=workspace.imagination,
        tangent_manager=Mock(),
        checkpoint_manager=workspace.checkpoint,
        hook_manager=Mock(),
        shutdown=Mock(),
    )
