"""Format-dependent save decisions independent of Paint dialogs."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import AbstractSet


class SaveWarning(str, Enum):
    COLOR_LOSS = "color_loss"
    TEXT_LOSS = "text_loss"
    NON_OPENABLE = "non_openable"


@dataclass(frozen=True, slots=True)
class SaveFormatPlan:
    warnings: tuple[SaveWarning, ...] = ()
    reload_after_save: bool = False


def plan_format_save(
    format_id: str | None,
    *,
    image_save_formats: AbstractSet[str],
    image_open_formats: AbstractSet[str],
    save_disabled_formats: AbstractSet[str],
) -> SaveFormatPlan:
    """Describe confirmations and reload behavior for a target format."""
    non_openable = format_id in {"HTML", "RICH_CONSOLE_MARKUP"} or (
        format_id in image_save_formats and format_id not in image_open_formats
    )
    if format_id in {"PLAINTEXT", "IRC"}:
        return SaveFormatPlan((SaveWarning.COLOR_LOSS,), reload_after_save=True)
    if format_id in save_disabled_formats:
        return SaveFormatPlan()
    if format_id in {"ANSI", "SVG", "HTML", "RICH_CONSOLE_MARKUP", "IRC"}:
        warnings = (SaveWarning.NON_OPENABLE,) if non_openable else ()
        return SaveFormatPlan(warnings)
    if format_id in image_save_formats:
        image_warnings: tuple[SaveWarning, ...] = (
            (SaveWarning.NON_OPENABLE, SaveWarning.TEXT_LOSS)
            if non_openable
            else (SaveWarning.TEXT_LOSS,)
        )
        return SaveFormatPlan(image_warnings, reload_after_save=not non_openable)
    return SaveFormatPlan()


__all__ = ["SaveFormatPlan", "SaveWarning", "plan_format_save"]
