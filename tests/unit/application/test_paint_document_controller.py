"""Tests for Paint document/layer coordination without widgets."""

from rich.style import Style

from aura_cli.application.paint.ansi_art_document import AnsiArtDocument
from aura_cli.application.paint.document_service import sample_document_cell
from aura_cli.application.paint.layers import LayerStack


def test_document_layer_sync_round_trip() -> None:
    document = AnsiArtDocument.from_text("A")
    document.st[0][0] = Style(color="#112233", bgcolor="#445566")
    stack = LayerStack(1, 1)
    layer = stack.active_layer
    assert layer is not None

    assert stack.store_document(layer.id, document) is True
    document.ch[0][0] = "B"
    assert stack.load_document(layer.id, document) is True

    assert document.ch[0][0] == "A"
    assert document.st[0][0].color.name == "#112233"


def test_cell_sample_normalizes_colors_and_bounds() -> None:
    document = AnsiArtDocument.from_text("X")
    document.st[0][0] = Style(color="#abcdef", bgcolor="#123456")

    sample = sample_document_cell(document, 0, 0)

    assert sample is not None
    assert (sample.character, sample.foreground, sample.background) == (
        "X",
        "#abcdef",
        "#123456",
    )
    assert sample_document_cell(document, -1, 0) is None
    assert sample_document_cell(document, 1, 0) is None


def test_document_clear_preserves_dimensions() -> None:
    document = AnsiArtDocument.from_text("AB\nCD")

    document.clear(default_bg="#123456", default_fg="#abcdef")

    assert (document.width, document.height) == (2, 2)
    assert document.ch == [[" ", " "], [" ", " "]]
    assert document.st[0][0].color.name == "#abcdef"
