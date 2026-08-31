"""Foundation regressions for localized TUI states and glyph fallback."""

import pytest
from textual.app import App, ComposeResult
from textual.widgets import Input, Label

import aura_cli.tui.constants as tui_constants
from aura_cli.tui.widgets.footer import AuraFooter
from aura_cli.tui.widgets.input import AuraInputBar
from aura_cli.tui.widgets.loading import AuraLoadingIndicator


class GlyphHarness(App[None]):
    def compose(self) -> ComposeResult:
        yield AuraFooter()
        yield AuraInputBar()
        yield AuraLoadingIndicator()


def test_ascii_glyph_mode_preserves_semantic_labels():
    original_mode = tui_constants.ACTIVE_GLYPH_MODE
    try:
        active = tui_constants.configure_glyphs("ascii")

        assert active == "ascii"
        assert tui_constants.SUCCESS == "[ok]"
        assert tui_constants.ERROR == "[x]"
        assert tui_constants.WARNING == "[!]"
        assert tui_constants.IDLE == "[ ]"
        assert tui_constants.STATUS_ICONS["running"] == "..."
        assert tui_constants.MODE_ICONS["agi"] == "[A]"
    finally:
        tui_constants.configure_glyphs(original_mode)


def test_runtime_ascii_reconfiguration_reaches_dynamic_widgets():
    original_mode = tui_constants.ACTIVE_GLYPH_MODE
    try:
        active = tui_constants.configure_glyphs("ascii")
        indicator = AuraLoadingIndicator()

        assert active == "ascii"
        assert tui_constants.ACTIVE_GLYPH_MODE == "ascii"
        assert tui_constants.get_glyph("AURA_STAR") == "*"
        assert indicator._spinner_frames == ["...", "..", ".", ".."]
    finally:
        tui_constants.configure_glyphs(original_mode)


@pytest.mark.asyncio
async def test_mounted_widgets_use_current_ascii_glyphs():
    original_mode = tui_constants.ACTIVE_GLYPH_MODE
    try:
        tui_constants.configure_glyphs("ascii")
        app = GlyphHarness()
        async with app.run_test() as pilot:
            assert str(app.query_one("#footer-icon", Label).render()) == "* AURA"
            assert app.query_one("#main_input", Input).placeholder.startswith("* ")
            assert str(app.query_one("#spinner", Label).render()) == "..."
            await pilot.pause()
    finally:
        tui_constants.configure_glyphs(original_mode)


def test_unicode_glyph_mode_can_be_selected_explicitly():
    original_mode = tui_constants.ACTIVE_GLYPH_MODE
    try:
        active = tui_constants.configure_glyphs("unicode")

        assert active == "unicode"
        assert tui_constants.SUCCESS == "✔"
        assert tui_constants.ERROR == "✖"
    finally:
        tui_constants.configure_glyphs(original_mode)


def test_auto_glyph_mode_uses_ascii_for_dumb_terminal(monkeypatch):
    monkeypatch.delenv("AURA_TUI_GLYPHS", raising=False)
    monkeypatch.setenv("TERM", "dumb")

    assert tui_constants.detect_glyph_mode() == "ascii"


def test_loading_indicator_starts_hidden_and_without_processing_text():
    indicator = AuraLoadingIndicator()

    assert indicator.is_visible is False
    assert indicator.message == ""
