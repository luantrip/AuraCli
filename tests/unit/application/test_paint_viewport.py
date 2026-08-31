"""Tests for headless Paint viewport decisions."""

import pytest
from textual.geometry import Offset, Size

from aura_cli.application.paint.viewport import document_corner, magnifier_transition


def test_document_corner_scales_and_clamps_scroll_position() -> None:
    assert document_corner(
        scroll_offset=Offset(30, 18),
        canvas_offset=Offset(2, 2),
        magnification=4,
        document_size=Size(6, 4),
    ) == Offset(5, 3)


def test_magnifier_zoom_in_centers_click_and_zoom_out_has_no_scroll_target() -> None:
    zoom_in = magnifier_transition(
        click=Offset(20, 10),
        viewport_size=Size(16, 8),
        current_magnification=1,
        return_magnification=4,
    )
    zoom_out = magnifier_transition(
        click=Offset(20, 10),
        viewport_size=Size(16, 8),
        current_magnification=4,
        return_magnification=4,
    )

    assert zoom_in.magnification == 4
    assert zoom_in.scroll_target == (72.0, 36.0)
    assert zoom_out.magnification == 1
    assert zoom_out.scroll_target is None


def test_invalid_magnification_is_rejected() -> None:
    with pytest.raises(ValueError, match="positive"):
        document_corner(
            scroll_offset=Offset(),
            canvas_offset=Offset(),
            magnification=0,
            document_size=Size(1, 1),
        )
