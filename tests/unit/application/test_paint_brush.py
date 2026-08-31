"""Tests for headless Paint brush policy."""

from rich.style import Style

from aura_cli.application.paint.ansi_art_document import AnsiArtDocument
from aura_cli.application.paint.brush import (
    BrushKind,
    BrushSettings,
    stamp_brush,
    stamp_cell,
)


def _settings(kind: BrushKind) -> BrushSettings:
    return BrushSettings(kind, "X", "#112233", "#445566")


def test_pencil_and_eraser_mutate_document_headlessly() -> None:
    document = AnsiArtDocument.from_text("A")
    assert stamp_cell(document, 0, 0, _settings(BrushKind.PENCIL)) is True
    assert document.ch[0][0] == "X"

    assert stamp_cell(document, 0, 0, _settings(BrushKind.ERASER)) is True
    assert document.ch[0][0] == " "


def test_airbrush_probability_is_injectable() -> None:
    document = AnsiArtDocument.from_text("A")

    assert (
        stamp_cell(
            document, 0, 0, _settings(BrushKind.AIRBRUSH), random_value=lambda: 0.1
        )
        is False
    )
    assert document.ch[0][0] == "A"
    assert (
        stamp_cell(
            document, 0, 0, _settings(BrushKind.AIRBRUSH), random_value=lambda: 0.9
        )
        is True
    )


def test_free_select_inverts_colors_and_brush_tracks_region() -> None:
    document = AnsiArtDocument.from_text("A")
    document.st[0][0] = Style(color="#000000", bgcolor="#ffffff")

    assert stamp_cell(document, 0, 0, _settings(BrushKind.FREE_SELECT)) is True
    assert document.st[0][0].color.name == "#ffffff"
    assert document.st[0][0].bgcolor.name == "#000000"

    region = stamp_brush(document, 0, 0, _settings(BrushKind.BRUSH))
    assert region.width == region.height == 5


def test_out_of_bounds_stamp_is_explicit() -> None:
    assert (
        stamp_cell(AnsiArtDocument.from_text("A"), -1, 0, _settings(BrushKind.PENCIL))
        is False
    )
