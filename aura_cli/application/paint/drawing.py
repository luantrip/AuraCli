"""Shape planning and brush application for headless Paint tools."""

from __future__ import annotations

from collections.abc import Callable, Iterable, Iterator
from enum import Enum

from textual.geometry import Offset, Region

from .graphics_primitives import bresenham_walk, midpoint_ellipse


class DrawShape(str, Enum):
    LINE = "line"
    RECTANGLE = "rectangle"
    ROUNDED_RECTANGLE = "rounded_rectangle"
    ELLIPSE = "ellipse"


def shape_points(
    shape: DrawShape, start: Offset, end: Offset
) -> Iterator[tuple[int, int]]:
    """Yield document coordinates for a shape outline."""
    if shape is DrawShape.LINE:
        yield from bresenham_walk(start.x, start.y, end.x, end.y)
        return

    min_x, max_x = sorted((start.x, end.x))
    min_y, max_y = sorted((start.y, end.y))
    if shape is DrawShape.RECTANGLE:
        for x in range(min_x, max_x + 1):
            yield x, min_y
            if max_y != min_y:
                yield x, max_y
        for y in range(min_y + 1, max_y):
            yield min_x, y
            if max_x != min_x:
                yield max_x, y
        return
    if shape is DrawShape.ELLIPSE:
        yield from midpoint_ellipse(
            (start.x + end.x) // 2,
            (start.y + end.y) // 2,
            abs(start.x - end.x) // 2,
            abs(start.y - end.y) // 2,
        )
        return
    if shape is not DrawShape.ROUNDED_RECTANGLE:
        raise ValueError(f"unsupported draw shape: {shape}")

    radius = min(2, (max_x - min_x) // 2, (max_y - min_y) // 2)
    for x, y in midpoint_ellipse(0, 0, radius, radius):
        yield (
            min_x + x + radius if x < 0 else max_x + x - radius,
            min_y + y + radius if y < 0 else max_y + y - radius,
        )
    for x in range(min_x + radius, max_x - radius + 1):
        yield x, min_y
        yield x, max_y
    for y in range(min_y + radius, max_y - radius + 1):
        yield min_x, y
        yield max_x, y


def apply_points(
    points: Iterable[tuple[int, int]],
    stamp: Callable[[int, int, Region | None], Region],
    affected_region: Region | None = None,
    *,
    deduplicate: bool = False,
) -> Region:
    """Apply a host-provided brush while tracking the affected region."""
    seen: set[tuple[int, int]] = set()
    for point in points:
        if deduplicate and point in seen:
            continue
        affected_region = stamp(*point, affected_region)
        seen.add(point)
    return affected_region or Region()


__all__ = ["DrawShape", "apply_points", "shape_points"]
