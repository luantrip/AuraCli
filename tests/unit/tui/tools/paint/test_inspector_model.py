"""Tests for Paint inspector projections without mounting Textual widgets."""

from textual.geometry import Region

from aura_cli.tui.tools.paint.inspector_model import (
    safe_object_items,
    subtract_region,
    subtract_regions,
)


def _area(regions: list[Region]) -> int:
    return sum(region.width * region.height for region in regions)


def test_region_subtraction_produces_non_overlapping_remainder() -> None:
    remainder = subtract_region(Region(0, 0, 10, 10), Region(2, 2, 4, 4))

    assert _area(remainder) == 84
    assert len(remainder) == 4


def test_multiple_region_subtraction_is_compositional() -> None:
    remainder = subtract_regions(
        Region(0, 0, 10, 10),
        [Region(0, 0, 5, 10), Region(5, 0, 5, 5)],
    )

    assert remainder == [Region(5, 5, 5, 5)]


def test_safe_object_items_preserves_getter_error() -> None:
    class Subject:
        @property
        def broken(self) -> str:
            raise RuntimeError("broken getter")

    items = {key: (value, error) for key, value, error in safe_object_items(Subject())}

    value, error = items["broken"]
    assert value is None
    assert isinstance(error, RuntimeError)
