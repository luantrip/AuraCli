"""Tests for style_checker module."""

from aura_cli.core.quality.style_checker import check_style


class TestFunctionNaming:
    def test_snake_case_passes(self):
        src = "def my_function():\n    pass\n"
        findings = check_style(src)
        assert not any(f["rule"] == "naming-function" for f in findings)

    def test_camel_case_flagged(self):
        src = "def myFunction():\n    pass\n"
        findings = check_style(src)
        matches = [f for f in findings if f["rule"] == "naming-function"]
        assert len(matches) == 1
        assert matches[0]["name"] == "myFunction"
        assert matches[0]["severity"] == "low"

    def test_dunder_excluded(self):
        src = "class A:\n    def __init__(self):\n        pass\n"
        findings = check_style(src)
        assert not any(f["rule"] == "naming-function" for f in findings)

    def test_private_snake_passes(self):
        src = "def _private_func():\n    pass\n"
        findings = check_style(src)
        assert not any(f["rule"] == "naming-function" for f in findings)


class TestClassNaming:
    def test_pascal_case_passes(self):
        src = "class MyClass:\n    pass\n"
        findings = check_style(src)
        assert not any(f["rule"] == "naming-class" for f in findings)

    def test_snake_case_flagged(self):
        src = "class my_class:\n    pass\n"
        findings = check_style(src)
        matches = [f for f in findings if f["rule"] == "naming-class"]
        assert len(matches) == 1
        assert matches[0]["name"] == "my_class"

    def test_underscore_prefix_passes(self):
        src = "class _InternalClass:\n    pass\n"
        findings = check_style(src)
        assert not any(f["rule"] == "naming-class" for f in findings)


class TestConstantNaming:
    def test_all_caps_passes(self):
        src = "MAX_SIZE = 100\n"
        findings = check_style(src)
        assert not any(f["rule"] == "naming-constant" for f in findings)

    def test_mixed_case_flagged(self):
        src = "MaxSize = 100\n"
        findings = check_style(src)
        matches = [f for f in findings if f["rule"] == "naming-constant"]
        assert len(matches) == 1
        assert matches[0]["name"] == "MaxSize"

    def test_lowercase_not_flagged(self):
        src = "my_var = 100\n"
        findings = check_style(src)
        assert not any(f["rule"] == "naming-constant" for f in findings)


class TestLineLength:
    def test_short_line_passes(self):
        src = "x = 1\n"
        findings = check_style(src)
        assert not any(f["rule"] == "line-too-long" for f in findings)

    def test_long_line_flagged(self):
        src = "x = " + "a" * 120 + "\n"
        findings = check_style(src)
        matches = [f for f in findings if f["rule"] == "line-too-long"]
        assert len(matches) == 1
        assert matches[0]["line"] == 1

    def test_exactly_120_passes(self):
        src = "x" * 120 + "\n"
        findings = check_style(src)
        assert not any(f["rule"] == "line-too-long" for f in findings)


class TestTooManyArgs:
    def test_seven_args_passes(self):
        src = "def f(a, b, c, d, e, f, g):\n    pass\n"
        findings = check_style(src)
        assert not any(f["rule"] == "too-many-args" for f in findings)

    def test_eight_args_flagged(self):
        src = "def f(a, b, c, d, e, f, g, h):\n    pass\n"
        findings = check_style(src)
        matches = [f for f in findings if f["rule"] == "too-many-args"]
        assert len(matches) == 1
        assert "8" in matches[0]["message"]

    def test_kwargs_counted(self):
        src = "def f(a, b, c, d, e, f, *args, **kwargs):\n    pass\n"
        findings = check_style(src)
        matches = [f for f in findings if f["rule"] == "too-many-args"]
        assert len(matches) == 1


class TestSyntaxError:
    def test_syntax_error_returns_line_findings_only(self):
        src = "def ???:\n" + "x" * 121 + "\n"
        findings = check_style(src)
        # Should still report line-length even with syntax error
        assert any(f["rule"] == "line-too-long" for f in findings)
