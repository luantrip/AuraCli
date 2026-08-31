"""Toolkit data projections used by the optional Textual inspector widgets."""

from __future__ import annotations

from collections.abc import Iterable, Iterator

from textual.geometry import Region

PropertyItem = tuple[str, object, Exception | None]


def subtract_region(base: Region, negation: Region) -> list[Region]:
    """Return non-overlapping rectangles for ``base - negation``."""
    left = max(base.x, negation.x)
    top = max(base.y, negation.y)
    right = min(base.right, negation.right)
    bottom = min(base.bottom, negation.bottom)
    if left >= right or top >= bottom:
        return [base]

    result: list[Region] = []
    if top > base.y:
        result.append(Region(base.x, base.y, base.width, top - base.y))
    if bottom < base.bottom:
        result.append(Region(base.x, bottom, base.width, base.bottom - bottom))
    if left > base.x:
        result.append(Region(base.x, top, left - base.x, bottom - top))
    if right < base.right:
        result.append(Region(right, top, base.right - right, bottom - top))
    return result


def subtract_regions(base: Region, negations: Iterable[Region]) -> list[Region]:
    result = [base]
    for negation in negations:
        result = [
            remainder
            for region in result
            for remainder in subtract_region(region, negation)
        ]
    return result


def safe_object_items(obj: object) -> Iterator[PropertyItem]:
    """Read attributes while representing getter failures as data."""
    for key in dir(obj):
        try:
            yield key, getattr(obj, key), None
        except AttributeError:
            try:
                yield key, getattr(type(obj), key), None
            except Exception as error:
                yield key, None, error
        except Exception as error:
            yield key, None, error


__all__ = ["PropertyItem", "safe_object_items", "subtract_region", "subtract_regions"]
