"""Backup naming and scheduling policy for Paint documents."""

from __future__ import annotations

from enum import Enum
from pathlib import Path
import re


class BackupDecision(str, Enum):
    SKIP = "skip"
    DEFER_UNTIL_PREVIEW_ENDS = "defer_until_preview_ends"
    SAVE = "save"


def decide_backup(
    *, saved_action_count: int, current_action_count: int, has_preview: bool
) -> BackupDecision:
    if saved_action_count == current_action_count:
        return BackupDecision.SKIP
    if has_preview:
        return BackupDecision.DEFER_UNTIL_PREVIEW_ENDS
    return BackupDecision.SAVE


def backup_path(
    *,
    file_path: str | None,
    backup_folder: str | None,
    untitled_name: str,
    session_number: int | None = None,
) -> Path:
    """Build the deterministic backup path without touching the filesystem."""
    source = Path(file_path or untitled_name)
    if backup_folder:
        source = Path(backup_folder) / source.name
    without_ansi_suffix = re.sub(r"\.ans$", "", str(source), flags=re.IGNORECASE)
    target = Path(without_ansi_suffix + ".ans~")
    if session_number is not None:
        target = target.with_name(f"{target.stem}.{session_number}{target.suffix}")
    return target.absolute()


__all__ = ["BackupDecision", "backup_path", "decide_backup"]
