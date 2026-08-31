"""Workspace boundary contracts for task parameter normalization."""

from aura_cli.core.agents.planning.task_parameter_normalizer import (
    TaskParameterNormalizer,
)


def test_default_normalizer_uses_allowed_base_dir(monkeypatch, tmp_path):
    from aura_cli.core.tools import file_system

    monkeypatch.setattr(file_system, "get_allowed_base_dir", lambda: tmp_path)

    normalizer = TaskParameterNormalizer()

    assert normalizer.workspace_root == tmp_path.resolve()
    assert normalizer.working_directory == str(tmp_path.resolve())


def test_normalizer_rejects_relative_escape_and_external_absolute_path(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    external = tmp_path / "outside.txt"
    external.write_text("outside", encoding="utf-8")
    normalizer = TaskParameterNormalizer(str(workspace))

    _, relative_errors = normalizer.normalize("read_file", {"path": "../outside.txt"})
    _, absolute_errors = normalizer.normalize("read_file", {"path": str(external)})

    assert any("fora do workspace" in error for error in relative_errors)
    assert any("fora do workspace" in error for error in absolute_errors)


def test_normalizer_rejects_symlink_resolving_outside_workspace(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    external = tmp_path / "outside.txt"
    external.write_text("outside", encoding="utf-8")
    link = workspace / "linked.txt"
    link.symlink_to(external)
    normalizer = TaskParameterNormalizer(str(workspace))

    _, errors = normalizer.normalize("read_file", {"path": str(link)})

    assert any("fora do workspace" in error for error in errors)
