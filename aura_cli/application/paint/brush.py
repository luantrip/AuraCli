"""Headless brush policy and cell mutation for Paint."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from random import random

from rich.color import Color as RichColor
from rich.style import Style
from textual.geometry import Region

from .ansi_art_document import AnsiArtDocument
from .palette_data import (
    AURA_DARK_BACKGROUND,
    AURA_LIGHT_GRAY,
    AURA_LIGHT_TEXT,
    AURA_WHITE,
)


class BrushKind(str, Enum):
    PENCIL = "pencil"
    BRUSH = "brush"
    ERASER = "eraser"
    AIRBRUSH = "airbrush"
    FREE_SELECT = "free_select"


@dataclass(frozen=True, slots=True)
class BrushSettings:
    kind: BrushKind
    character: str
    foreground: str
    background: str
    dark_mode: bool = False
    color_eraser: bool = False


def stamp_cell(
    document: AnsiArtDocument,
    x: int,
    y: int,
    settings: BrushSettings,
    *,
    erase_mode: bool = False,
    character_override: str | None = None,
    random_value: Callable[[], float] = random,
) -> bool:
    """Mutate one cell and report whether a mutation occurred."""
    if x < 0 or y < 0 or x >= document.width or y >= document.height:
        return False
    if settings.kind is BrushKind.AIRBRUSH and random_value() < 0.7:
        return False
    if settings.kind is BrushKind.FREE_SELECT:
        style = document.st[y][x]
        if style.color is None or style.bgcolor is None:
            return False
        document.st[y][x] = Style(
            color=AnsiArtDocument._invert_color(style.color),
            bgcolor=AnsiArtDocument._invert_color(style.bgcolor),
        )
        return True

    character = character_override or settings.character
    foreground = settings.foreground
    background = settings.background
    is_eraser = settings.kind is BrushKind.ERASER or erase_mode
    if is_eraser:
        character = " "
        background, foreground = (
            (AURA_DARK_BACKGROUND, AURA_LIGHT_GRAY)
            if settings.dark_mode
            else (AURA_WHITE, AURA_LIGHT_TEXT)
        )
        if settings.color_eraser and not erase_mode:
            character = document.ch[y][x]
            style = document.st[y][x]
            if style.color is None or style.bgcolor is None:
                return False
            selected = RichColor.parse(settings.foreground).get_truecolor()
            current_fg = style.color.get_truecolor()
            current_bg = style.bgcolor.get_truecolor()
            threshold = 5
            foreground = (
                settings.background
                if all(
                    abs(current - target) < threshold
                    for current, target in zip(current_fg, selected, strict=True)
                )
                else current_fg.hex
            )
            background = (
                settings.background
                if all(abs(current_bg[i] - selected[i]) < threshold for i in range(3))
                else current_bg.hex
            )
    document.ch[y][x] = character
    document.st[y][x] = Style(color=foreground, bgcolor=background)
    return True


def stamp_brush(
    document: AnsiArtDocument,
    x: int,
    y: int,
    settings: BrushSettings,
    affected_region: Region | None = None,
    *,
    random_value: Callable[[], float] = random,
) -> Region:
    diameter = (
        3
        if settings.kind
        in {
            BrushKind.BRUSH,
            BrushKind.AIRBRUSH,
            BrushKind.ERASER,
        }
        else 1
    )
    square = settings.kind is BrushKind.ERASER
    radius = diameter // 2
    for offset_y in range(-radius, radius + 1):
        for offset_x in range(-radius, radius + 1):
            if square or offset_x**2 + offset_y**2 <= radius**2:
                stamp_cell(
                    document,
                    x + offset_x,
                    y + offset_y,
                    settings,
                    random_value=random_value,
                )
    tracked_diameter = diameter + 2
    region = Region(
        x - tracked_diameter // 2,
        y - tracked_diameter // 2,
        tracked_diameter,
        tracked_diameter,
    )
    return affected_region.union(region) if affected_region else region


__all__ = ["BrushKind", "BrushSettings", "stamp_brush", "stamp_cell"]
