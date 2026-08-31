"""Canonical default-root contracts for memory services."""

from unittest.mock import patch

from aura_cli.core.memory.memory_service import MemoryService, _default_project_root


def test_memory_default_project_root_uses_allowed_base(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()

    with patch(
        "aura_cli.core.tools.file_system.get_allowed_base_dir",
        return_value=workspace,
    ):
        assert _default_project_root() == workspace.resolve()


def test_memory_service_without_root_uses_allowed_base(tmp_path, monkeypatch):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    monkeypatch.setenv("AURA_HOME", str(tmp_path / "aura-home"))

    with patch(
        "aura_cli.core.tools.file_system.get_allowed_base_dir",
        return_value=workspace,
    ):
        service = MemoryService()

    assert service.project_root == workspace.resolve()
