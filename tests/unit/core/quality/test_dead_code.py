"""Tests for dead code detector."""

from aura_cli.core.quality.dead_code_detector import detect_dead_code


class TestUnusedImports:
    def test_unused_import_detected(self):
        source = "import os\nimport sys\nprint(sys.argv)\n"
        findings = detect_dead_code(source)
        unused = [f for f in findings if f["rule"] == "unused_import"]
        assert len(unused) == 1
        assert unused[0]["name"] == "os"
        assert unused[0]["severity"] == "medium"

    def test_used_import_not_flagged(self):
        source = "import os\nprint(os.getcwd())\n"
        findings = detect_dead_code(source)
        unused = [f for f in findings if f["rule"] == "unused_import"]
        assert len(unused) == 0

    def test_from_import_unused(self):
        source = "from os.path import join, exists\nprint(join('a', 'b'))\n"
        findings = detect_dead_code(source)
        unused = [f for f in findings if f["rule"] == "unused_import"]
        assert len(unused) == 1
        assert unused[0]["name"] == "exists"


class TestUnreachableCode:
    def test_code_after_return(self):
        source = "def f():\n    return 1\n    x = 2\n"
        findings = detect_dead_code(source)
        unreach = [f for f in findings if f["rule"] == "unreachable"]
        assert len(unreach) == 1
        assert unreach[0]["line"] == 3
        assert unreach[0]["severity"] == "low"

    def test_code_after_raise(self):
        source = "def f():\n    raise ValueError()\n    x = 2\n"
        findings = detect_dead_code(source)
        unreach = [f for f in findings if f["rule"] == "unreachable"]
        assert len(unreach) == 1

    def test_no_unreachable_when_no_terminator(self):
        source = "def f():\n    x = 1\n    return x\n"
        findings = detect_dead_code(source)
        unreach = [f for f in findings if f["rule"] == "unreachable"]
        assert len(unreach) == 0


class TestUnusedVariables:
    def test_unused_variable_detected(self):
        source = "def f():\n    x = 1\n    y = 2\n    return y\n"
        findings = detect_dead_code(source)
        unused = [f for f in findings if f["rule"] == "unused_variable"]
        assert len(unused) == 1
        assert unused[0]["name"] == "x"
        assert unused[0]["severity"] == "low"

    def test_underscore_prefixed_excluded(self):
        source = "def f():\n    _unused = 1\n    return 42\n"
        findings = detect_dead_code(source)
        unused = [f for f in findings if f["rule"] == "unused_variable"]
        assert len(unused) == 0

    def test_used_variable_not_flagged(self):
        source = "def f():\n    x = 1\n    return x\n"
        findings = detect_dead_code(source)
        unused = [f for f in findings if f["rule"] == "unused_variable"]
        assert len(unused) == 0

    def test_self_excluded(self):
        source = "def f(self):\n    self = None\n    return 1\n"
        findings = detect_dead_code(source)
        unused = [
            f
            for f in findings
            if f["rule"] == "unused_variable" and f["name"] == "self"
        ]
        assert len(unused) == 0
