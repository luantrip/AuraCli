"""Tests for headless Paint document transformations."""

import pytest

from aura_cli.application.paint.ansi_art_document import AnsiArtDocument
from aura_cli.application.paint.transformations import (
    flip_horizontal,
    flip_vertical,
    rotate,
    stretch_skew,
)


def test_flip_and_rotate_transform_character_matrix() -> None:
    horizontal = AnsiArtDocument.from_text("AB\nCD")
    vertical = AnsiArtDocument.from_text("AB\nCD")
    rotated = AnsiArtDocument.from_text("AB\nCD")

    flip_horizontal(horizontal)
    flip_vertical(vertical)
    rotate(rotated, 90)

    assert horizontal.ch == [["B", "A"], ["D", "C"]]
    assert vertical.ch == [["C", "D"], ["A", "B"]]
    assert rotated.ch == [["C", "A"], ["D", "B"]]


def test_stretch_uses_nearest_neighbor_and_validates_scale() -> None:
    document = AnsiArtDocument.from_text("AB")

    stretch_skew(
        document,
        horizontal_percent=200,
        vertical_percent=100,
        horizontal_degrees=0,
        vertical_degrees=0,
    )

    assert document.ch == [["A", "A", "B", "B"]]
    with pytest.raises(ValueError, match="positive"):
        stretch_skew(
            document,
            horizontal_percent=0,
            vertical_percent=100,
            horizontal_degrees=0,
            vertical_degrees=0,
        )


def test_rotation_rejects_unsupported_angle() -> None:
    with pytest.raises(ValueError, match="90, 180, or 270"):
        rotate(AnsiArtDocument.from_text("A"), 45)
