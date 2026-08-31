"""Project-boundary contracts for memory source files."""

from unittest.mock import Mock

from aura_cli.core.memory.memory_service import MemoryService


def _service(workspace):
    service = MemoryService.__new__(MemoryService)
    service.project_root = workspace.resolve()
    service._vector_storage = Mock()
    return service


def test_remember_rejects_file_path_outside_workspace(tmp_path):
    workspace = tmp_path / "workspace"
    outside = tmp_path / "outside.py"
    workspace.mkdir()
    outside.write_text("secret", encoding="utf-8")
    service = _service(workspace)

    assert service.remember("content", {"file_path": str(outside)}) is False
    service._vector_storage.add.assert_not_called()


def test_relative_memory_file_is_anchored_to_workspace(tmp_path):
    workspace = tmp_path / "workspace"
    source = workspace / "src" / "module.py"
    workspace.joinpath("src").mkdir(parents=True)
    source.write_text("print('ok')", encoding="utf-8")
    service = _service(workspace)

    assert service._resolve_project_file("src/module.py") == source.resolve()


def test_remember_rejects_symlink_resolving_outside_workspace(tmp_path):
    workspace = tmp_path / "workspace"
    outside = tmp_path / "outside.py"
    link = workspace / "link.py"
    workspace.mkdir()
    outside.write_text("secret", encoding="utf-8")
    link.symlink_to(outside)
    service = _service(workspace)

    assert service.remember("content", {"path": "link.py"}) is False
    service._vector_storage.add.assert_not_called()
