"""Tests for duplicate_detector module."""

from aura_cli.core.quality.duplicate_detector import detect_duplicates


class TestDuplicateDetection:
    def test_no_duplicates(self):
        src = "\n".join(f"line_{i} = {i}" for i in range(20))
        findings = detect_duplicates(src)
        assert findings == []

    def test_exact_duplicate_block(self):
        block = "\n".join(f"    x_{i} = {i} + 1" for i in range(6))
        src = f"def a():\n{block}\n\ndef b():\n{block}\n"
        findings = detect_duplicates(src)
        assert len(findings) >= 1
        f = findings[0]
        assert f["type"] == "duplicate"
        assert f["severity"] == "medium"
        assert f["lines"] >= 6

    def test_min_lines_respected(self):
        block = "\n".join(f"    val_{i} = {i}" for i in range(4))
        src = f"def a():\n{block}\n\ndef b():\n{block}\n"
        # With min_lines=6, 4-line block should not be detected
        findings = detect_duplicates(src, min_lines=6)
        assert findings == []
        # With min_lines=4, it should be detected
        findings = detect_duplicates(src, min_lines=4)
        assert len(findings) >= 1

    def test_short_source_returns_empty(self):
        src = "x = 1\ny = 2\n"
        findings = detect_duplicates(src)
        assert findings == []

    def test_whitespace_normalization(self):
        block_a = "\n".join(f"    x_{i} = {i}" for i in range(6))
        block_b = "\n".join(f"      x_{i} = {i}" for i in range(6))
        src = f"def a():\n{block_a}\n\ndef b():\n{block_b}\n"
        findings = detect_duplicates(src)
        assert len(findings) >= 1

    def test_comment_stripping(self):
        block_a = "\n".join(f"    x_{i} = {i}  # comment a" for i in range(6))
        block_b = "\n".join(f"    x_{i} = {i}  # comment b" for i in range(6))
        src = f"def a():\n{block_a}\n\ndef b():\n{block_b}\n"
        findings = detect_duplicates(src)
        assert len(findings) >= 1

    def test_returns_correct_line_numbers(self):
        block = "\n".join(f"    result_{i} = compute({i})" for i in range(6))
        src = f"def a():\n{block}\n\ndef b():\n{block}\n"
        findings = detect_duplicates(src)
        assert len(findings) >= 1
        f = findings[0]
        assert f["line_start_a"] >= 1
        assert f["line_end_a"] >= f["line_start_a"]
        assert f["line_start_b"] > f["line_end_a"]

    def test_empty_source(self):
        findings = detect_duplicates("")
        assert findings == []

    def test_blank_lines_not_duplicates(self):
        src = "\n" * 30
        findings = detect_duplicates(src)
        assert findings == []
