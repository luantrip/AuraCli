"""Pure file-browser formatting and navigation decisions."""

from __future__ import annotations

from pathlib import Path
import stat
from typing import Callable, Sequence


def resolve_child_path(parent: Path, name: str) -> Path:
    """Resolve a single child name while preventing path traversal."""
    normalized = name.strip()
    candidate = Path(normalized)
    if (
        not normalized
        or candidate.is_absolute()
        or normalized in {".", ".."}
        or len(candidate.parts) != 1
    ):
        raise ValueError("name must identify one item inside the current directory")
    return parent / normalized


def plan_transfer_destination(
    source: Path,
    destination_dir: Path,
    *,
    exists: Callable[[Path], bool],
) -> Path:
    """Choose a collision-free copy/move destination."""
    destination = destination_dir / source.name
    if not exists(destination):
        return destination
    counter = 1
    while True:
        candidate = destination_dir / f"{source.stem}_copy{counter}{source.suffix}"
        if not exists(candidate):
            return candidate
        counter += 1


def plan_duplicate_destination(source: Path, *, exists: Callable[[Path], bool]) -> Path:
    """Choose the historical ``_copy`` name followed by numbered variants."""
    candidate = source.parent / f"{source.stem}_copy{source.suffix}"
    if not exists(candidate):
        return candidate
    counter = 2
    while True:
        candidate = source.parent / f"{source.stem}_copy{counter}{source.suffix}"
        if not exists(candidate):
            return candidate
        counter += 1


def format_file_size(size: int) -> str:
    value = float(max(0, size))
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if value < 1024:
            return f"{int(value)} {unit}" if unit == "B" else f"{value:.1f} {unit}"
        value /= 1024
    return f"{value:.1f} PB"


def format_file_permissions(mode: int) -> str:
    return "".join(
        permission.casefold()
        if mode & getattr(stat, f"S_I{permission}{owner}")
        else "-"
        for owner in ("USR", "GRP", "OTH")
        for permission in ("R", "W", "X")
    )


def append_navigation_path(
    history: Sequence[Path], current_index: int, path: Path
) -> tuple[list[Path], int]:
    retained = list(history[: current_index + 1])
    if not retained or retained[-1] != path:
        retained.append(path)
    return retained, len(retained) - 1


__all__ = [
    "append_navigation_path",
    "format_file_permissions",
    "format_file_size",
    "plan_duplicate_destination",
    "plan_transfer_destination",
    "resolve_child_path",
]
