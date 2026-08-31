"""Text selection projections for Paint documents."""

from __future__ import annotations

from collections.abc import Iterator

from textual.geometry import Offset

from .ansi_art_document import Selection


def offset_to_text_index(textbox: Selection, offset: Offset) -> int:
    if not textbox.textbox_mode:
        raise ValueError("text index requires a textbox selection")
    return offset.y * textbox.region.width + offset.x


def text_index_to_offset(textbox: Selection, index: int) -> Offset:
    if not textbox.textbox_mode:
        raise ValueError("text offset requires a textbox selection")
    return Offset(index % textbox.region.width, index // textbox.region.width)


def selected_text_range(textbox: Selection) -> Iterator[Offset]:
    """Yield the inclusive selection in document reading order."""
    start = offset_to_text_index(textbox, textbox.text_selection_start)
    end = offset_to_text_index(textbox, textbox.text_selection_end)
    for index in range(min(start, end), max(start, end) + 1):
        yield text_index_to_offset(textbox, index)


def selected_text(textbox: Selection) -> str:
    """Project selected cells as rows separated by one newline."""
    if textbox.contained_image is None:
        raise ValueError("textbox selection has no image data")
    rows: list[list[str]] = []
    last_y: int | None = None
    for x, y in selected_text_range(textbox):
        if y != last_y:
            rows.append([])
            last_y = y
        rows[-1].append(textbox.contained_image.ch[y][x])
    return "\n".join("".join(row) for row in rows)


__all__ = [
    "offset_to_text_index",
    "selected_text",
    "selected_text_range",
    "text_index_to_offset",
]
