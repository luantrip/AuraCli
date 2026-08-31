"""Headless viewport and magnification decisions for Paint."""

from __future__ import annotations

from dataclasses import dataclass
import math

from textual.geometry import Offset, Size


@dataclass(frozen=True, slots=True)
class ZoomTransition:
    magnification: int
    scroll_target: tuple[float, float] | None = None


def next_magnification(current: int, return_magnification: int) -> int:
    if current <= 0 or return_magnification <= 0:
        raise ValueError("magnification must be positive")
    return return_magnification if current == 1 else 1


def document_corner(
    *,
    scroll_offset: Offset,
    canvas_offset: Offset,
    magnification: int,
    document_size: Size,
) -> Offset:
    if magnification <= 0:
        raise ValueError("magnification must be positive")
    unscaled = scroll_offset - canvas_offset
    return Offset(
        max(0, min(document_size.width - 1, math.ceil(unscaled.x / magnification))),
        max(0, min(document_size.height - 1, math.ceil(unscaled.y / magnification))),
    )


def magnifier_transition(
    *,
    click: Offset,
    viewport_size: Size,
    current_magnification: int,
    return_magnification: int,
) -> ZoomTransition:
    if current_magnification <= 0 or return_magnification <= 0:
        raise ValueError("magnification must be positive")
    target = next_magnification(current_magnification, return_magnification)
    if target <= current_magnification:
        return ZoomTransition(target)
    visible_width = viewport_size.width / target
    visible_height = viewport_size.height / target
    return ZoomTransition(
        target,
        (
            (click.x - visible_width / 2) * target / current_magnification,
            (click.y - visible_height / 2) * target / current_magnification,
        ),
    )


__all__ = [
    "ZoomTransition",
    "document_corner",
    "magnifier_transition",
    "next_magnification",
]
