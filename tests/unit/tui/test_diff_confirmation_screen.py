"""Tests for diff confirmation screen construction."""

from aura_cli.tui.screens.diff_confirmation_screen import DiffConfirmationScreen


def test_diff_screen_from_legacy_diff_text():
    screen = DiffConfirmationScreen(diff_text="+added\n-old")
    assert screen.file_path == "file"
    assert screen.diff_lines == ["+added", "-old"]


def test_diff_screen_with_explicit_path():
    screen = DiffConfirmationScreen("src/a.py", ["+x"], new_content="x")
    assert screen.file_path == "src/a.py"
    assert screen.new_content == "x"
