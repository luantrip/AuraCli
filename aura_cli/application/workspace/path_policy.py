"""Workspace path-containment policy independent from filesystem operations."""

from __future__ import annotations

from pathlib import Path


def resolve_workspace_path(
    path: str,
    base_dir: Path,
    *,
    validation_enabled: bool = True,
) -> Path:
    """Resolve a path and require containment in the configured workspace."""
    if "\x00" in path:
        raise ValueError("Path contains null bytes")

    candidate = Path(path)
    resolved_base = base_dir.resolve()
    resolved = (
        candidate.resolve()
        if candidate.is_absolute()
        else (resolved_base / candidate).resolve()
    )
    if validation_enabled:
        try:
            resolved.relative_to(resolved_base)
        except ValueError as error:
            raise ValueError(
                f"Path resolves outside allowed directory: {resolved}"
            ) from error
    return resolved
