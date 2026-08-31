"""Artifact classification policy shared by concrete worker adapters."""

from __future__ import annotations

from enum import Enum
from typing import Any, Mapping


class ArtifactKind(str, Enum):
    GENERATED = "generated"
    EDITED = "edited"
    ANALYZED = "analyzed"


_GENERATING_OPERATIONS = {"write_file"}
_EDITING_OPERATIONS = {"edit_file"}
_ANALYZING_OPERATIONS = {
    "analyze_code",
    "find_in_files",
    "list_directory",
    "read_file",
    "tree_view",
    "validate_syntax",
}


def classify_artifact(
    operation: str, parameters: Mapping[str, Any]
) -> tuple[ArtifactKind, str] | None:
    """Classify the first meaningful path carried by a tool or workflow operation."""
    path = next(
        (
            value.strip()
            for key in ("path", "file_path", "test_path")
            if isinstance((value := parameters.get(key)), str) and value.strip()
        ),
        None,
    )
    if path is None or path in {".", "/"}:
        return None

    normalized_operation = operation.casefold()
    if normalized_operation in _GENERATING_OPERATIONS:
        return ArtifactKind.GENERATED, path
    if normalized_operation in _EDITING_OPERATIONS:
        return ArtifactKind.EDITED, path
    if normalized_operation in _ANALYZING_OPERATIONS:
        return ArtifactKind.ANALYZED, path
    return None


__all__ = ["ArtifactKind", "classify_artifact"]
