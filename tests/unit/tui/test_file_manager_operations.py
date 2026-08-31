"""Concrete file-manager I/O adapter tests, confined to pytest tmp paths."""

from pathlib import Path

import pytest

from aura_cli.tui.tools.file_manager.file_operations import (
    create_path,
    delete_path,
    duplicate_file,
    rename_path,
    transfer_path,
)


def test_create_rename_duplicate_and_delete_file(tmp_path: Path) -> None:
    source = tmp_path / "source.txt"
    create_path(source, directory=False)
    source.write_text("content", encoding="utf-8")
    renamed = tmp_path / "renamed.txt"
    rename_path(source, renamed)
    duplicate = tmp_path / "duplicate.txt"
    duplicate_file(renamed, duplicate)

    assert duplicate.read_text(encoding="utf-8") == "content"
    delete_path(renamed)
    assert not renamed.exists() and duplicate.exists()


def test_copy_directory_and_move_file(tmp_path: Path) -> None:
    directory = tmp_path / "directory"
    create_path(directory, directory=True)
    (directory / "nested.txt").write_text("nested", encoding="utf-8")
    copied = tmp_path / "copied"
    transfer_path(directory, copied, operation="copy")
    moved = tmp_path / "moved.txt"
    transfer_path(copied / "nested.txt", moved, operation="cut")

    assert moved.read_text(encoding="utf-8") == "nested"
    assert not (copied / "nested.txt").exists()


def test_invalid_transfer_and_directory_duplicate_are_rejected(tmp_path: Path) -> None:
    source = tmp_path / "source"
    create_path(source, directory=True)
    with pytest.raises(ValueError, match="unsupported"):
        transfer_path(source, tmp_path / "target", operation="invalid")  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="only files"):
        duplicate_file(source, tmp_path / "duplicate")
