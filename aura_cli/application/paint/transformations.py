"""In-place document transformations independent of Paint widgets."""

from __future__ import annotations

import math

from rich.style import Style

from .ansi_art_document import AnsiArtDocument


def flip_horizontal(image: AnsiArtDocument) -> None:
    source = AnsiArtDocument(image.width, image.height)
    source.copy(image)
    for y in range(image.height):
        for x in range(image.width):
            target_x = image.width - x - 1
            image.ch[y][target_x] = source.ch[y][x]
            image.st[y][target_x] = source.st[y][x]


def flip_vertical(image: AnsiArtDocument) -> None:
    source = AnsiArtDocument(image.width, image.height)
    source.copy(image)
    for y in range(image.height):
        for x in range(image.width):
            target_y = image.height - y - 1
            image.ch[target_y][x] = source.ch[y][x]
            image.st[target_y][x] = source.st[y][x]


def rotate(image: AnsiArtDocument, angle: int) -> None:
    if angle not in {90, 180, 270}:
        raise ValueError("rotation angle must be 90, 180, or 270")
    source = AnsiArtDocument(image.width, image.height)
    source.copy(image)
    if angle != 180:
        image.resize(image.height, image.width)
    for y in range(image.height):
        for x in range(image.width):
            if angle == 90:
                source_y, source_x = image.width - x - 1, y
            elif angle == 180:
                source_y, source_x = image.height - y - 1, image.width - x - 1
            else:
                source_y, source_x = x, image.height - y - 1
            image.ch[y][x] = source.ch[source_y][source_x]
            image.st[y][x] = source.st[source_y][source_x]


def stretch_skew(
    image: AnsiArtDocument,
    *,
    horizontal_percent: float,
    vertical_percent: float,
    horizontal_degrees: float,
    vertical_degrees: float,
) -> None:
    """Apply nearest-neighbor stretch and skew to a document."""
    horizontal_stretch = horizontal_percent / 100
    vertical_stretch = vertical_percent / 100
    if horizontal_stretch <= 0 or vertical_stretch <= 0:
        raise ValueError("stretch percentages must be positive")
    horizontal_skew = math.radians(horizontal_degrees)
    vertical_skew = math.radians(vertical_degrees)

    source = AnsiArtDocument(image.width, image.height)
    source.copy(image)
    width = source.width * horizontal_stretch
    height = source.height * vertical_stretch
    corners = [
        (
            math.tan(-horizontal_skew) * height * x01 + width * y01,
            math.tan(-vertical_skew) * width * y01 + height * x01,
        )
        for x01, y01 in ((0, 0), (0, 1), (1, 0), (1, 1))
    ]
    min_x = min(x for x, _ in corners)
    max_x = max(x for x, _ in corners)
    min_y = min(y for _, y in corners)
    max_y = max(y for _, y in corners)
    image.resize(max(1, int(max_x - min_x)), max(1, int(max_y - min_y)))

    default_style = Style(color="#000000", bgcolor="#ffffff")
    for y in range(image.height):
        for x in range(image.width):
            source_x = int(
                x / horizontal_stretch + math.tan(horizontal_skew) * y + min_x
            )
            source_y = int(math.tan(vertical_skew) * x + y / vertical_stretch + min_y)
            if 0 <= source_x < source.width and 0 <= source_y < source.height:
                image.ch[y][x] = source.ch[source_y][source_x]
                image.st[y][x] = source.st[source_y][source_x]
            else:
                image.ch[y][x] = " "
                image.st[y][x] = default_style


__all__ = ["flip_horizontal", "flip_vertical", "rotate", "stretch_skew"]
