"""Tests for terminal-output presentation queries."""

from aura_cli.application.presentation import (
    detect_output_language,
    query_output_lines,
)


def test_detects_supported_output_languages() -> None:
    assert detect_output_language("Traceback: boom") == "python"
    assert detect_output_language('{"ok": true}') == "json"
    assert detect_output_language("<root>") == "xml"
    assert detect_output_language("plain") == "text"


def test_combines_category_and_text_queries_case_insensitively() -> None:
    lines = ["INFO ready", "ERROR Disk Full", "plain"]

    assert query_output_lines(lines, filter_type="error", query="DISK") == [
        "ERROR Disk Full"
    ]


def test_category_without_matches_preserves_original_lines() -> None:
    lines = ["plain", "quiet"]

    assert query_output_lines(lines, filter_type="warning") == lines
