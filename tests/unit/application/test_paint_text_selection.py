"""Tests for headless Paint text-selection projections."""

from textual.geometry import Offset, Region

from aura_cli.application.paint.ansi_art_document import AnsiArtDocument, Selection
from aura_cli.application.paint.text_selection import (
    offset_to_text_index,
    selected_text,
    selected_text_range,
    text_index_to_offset,
)


def _textbox() -> Selection:
    selection = Selection(Region(0, 0, 2, 2))
    selection.textbox_mode = True
    selection.contained_image = AnsiArtDocument.from_text("AB\nCD")
    selection.text_selection_start = Offset(1, 1)
    selection.text_selection_end = Offset(0, 0)
    return selection


def test_text_offsets_round_trip() -> None:
    textbox = _textbox()

    assert offset_to_text_index(textbox, Offset(1, 1)) == 3
    assert text_index_to_offset(textbox, 3) == Offset(1, 1)


def test_reverse_selection_projects_in_reading_order_without_extra_newlines() -> None:
    textbox = _textbox()

    assert list(selected_text_range(textbox)) == [
        Offset(0, 0),
        Offset(1, 0),
        Offset(0, 1),
        Offset(1, 1),
    ]
    assert selected_text(textbox) == "AB\nCD"


def test_non_textbox_selection_is_rejected() -> None:
    selection = Selection(Region(0, 0, 1, 1))

    try:
        offset_to_text_index(selection, Offset(0, 0))
    except ValueError as error:
        assert "textbox" in str(error)
    else:
        raise AssertionError("non-textbox selection was accepted")
