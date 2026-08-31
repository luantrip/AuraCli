"""Workspace path-containment policy tests."""

from pathlib import Path

import pytest

from aura_cli.application.workspace.path_policy import resolve_workspace_path


def test_resolve_workspace_path_accepts_relative_child(tmp_path: Path) -> None:
    assert resolve_workspace_path("src/main.py", tmp_path) == tmp_path / "src/main.py"


def test_resolve_workspace_path_rejects_escape_and_null_byte(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="outside allowed directory"):
        resolve_workspace_path("../secret", tmp_path)
    with pytest.raises(ValueError, match="null bytes"):
        resolve_workspace_path("bad\x00path", tmp_path)


def test_disabled_validation_preserves_explicit_absolute_path(tmp_path: Path) -> None:
    outside = tmp_path.parent / "outside"
    assert (
        resolve_workspace_path(str(outside), tmp_path, validation_enabled=False)
        == outside.resolve()
    )
