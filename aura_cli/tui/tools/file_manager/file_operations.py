"""Concrete filesystem operations used by the Textual file-manager adapter."""

from __future__ import annotations

from pathlib import Path
import shutil
from typing import Literal

TransferOperation = Literal["copy", "cut"]


def create_path(path: Path, *, directory: bool) -> None:
    if directory:
        path.mkdir(parents=True, exist_ok=False)
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.touch(exist_ok=False)


def rename_path(source: Path, destination: Path) -> None:
    source.rename(destination)


def delete_path(path: Path) -> None:
    if path.is_dir() and not path.is_symlink():
        shutil.rmtree(path)
    else:
        path.unlink()


def transfer_path(
    source: Path, destination: Path, *, operation: TransferOperation
) -> None:
    if operation == "cut":
        shutil.move(str(source), str(destination))
    elif operation == "copy" and source.is_dir():
        shutil.copytree(source, destination)
    elif operation == "copy":
        shutil.copy2(source, destination)
    else:
        raise ValueError(f"unsupported transfer operation: {operation}")


def duplicate_file(source: Path, destination: Path) -> None:
    if not source.is_file():
        raise ValueError("only files can be duplicated")
    shutil.copy2(source, destination)


__all__ = [
    "TransferOperation",
    "create_path",
    "delete_path",
    "duplicate_file",
    "rename_path",
    "transfer_path",
]
