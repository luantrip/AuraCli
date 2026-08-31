"""Tests for headless Paint shape planning."""

from textual.geometry import Offset, Region

from aura_cli.application.paint.drawing import DrawShape, apply_points, shape_points


def test_rectangle_points_are_outline_only_and_unique() -> None:
    points = list(shape_points(DrawShape.RECTANGLE, Offset(0, 0), Offset(2, 2)))

    assert set(points) == {
        (0, 0),
        (1, 0),
        (2, 0),
        (0, 1),
        (2, 1),
        (0, 2),
        (1, 2),
        (2, 2),
    }
    assert len(points) == len(set(points))


def test_apply_points_can_deduplicate_and_accumulate_region() -> None:
    calls: list[tuple[int, int]] = []

    def stamp(x: int, y: int, affected: Region | None) -> Region:
        calls.append((x, y))
        cell = Region(x, y, 1, 1)
        return affected.union(cell) if affected else cell

    region = apply_points([(1, 1), (1, 1), (2, 1)], stamp, deduplicate=True)

    assert calls == [(1, 1), (2, 1)]
    assert region == Region(1, 1, 2, 1)


def test_line_and_ellipse_plans_are_not_empty() -> None:
    assert list(shape_points(DrawShape.LINE, Offset(0, 0), Offset(3, 2)))
    assert list(shape_points(DrawShape.ELLIPSE, Offset(0, 0), Offset(4, 2)))
