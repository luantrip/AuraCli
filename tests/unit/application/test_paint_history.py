"""Tests for widget-independent Paint history policy."""

from textual.geometry import Region

from aura_cli.application.paint.action import PaintAction
from aura_cli.application.paint.ansi_art_document import AnsiArtDocument
from aura_cli.application.paint.history import PaintHistory


def test_history_undo_and_redo_swap_document_state() -> None:
    document = AnsiArtDocument.from_text("A")
    action = PaintAction("draw", Region(0, 0, 1, 1))
    action.update(document)
    document.ch[0][0] = "B"
    history = PaintHistory()
    history.add(action)

    undone = history.undo(document, full_region=Region(0, 0, 1, 1))
    redone = history.redo(document, full_region=Region(0, 0, 1, 1))

    assert undone.changed is True
    assert redone.changed is True
    assert document.ch[0][0] == "B"
    assert len(history.undos) == 1
    assert history.redos == []


def test_history_empty_transition_is_explicit() -> None:
    document = AnsiArtDocument.from_text("A")

    outcome = PaintHistory().undo(document, full_region=Region(0, 0, 1, 1))

    assert outcome.changed is False
