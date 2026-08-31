"""Tests for aura_cli.core.tools.deep_analysis helper functions."""

from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Lazy-import helpers: patch heavy deps before importing the module
# ---------------------------------------------------------------------------
_mock_rich_print = MagicMock()
_mock_rprint_module = MagicMock()
_mock_rprint_module.print = _mock_rich_print

with patch.dict("sys.modules", {"rich": _mock_rprint_module}):
    # rich.print is accessed as `from rich import print as rprint`
    pass


@pytest.fixture(autouse=True)
def _patch_external(monkeypatch):
    """Silence rprint, display_tool_call, logger, stats for all tests."""
    monkeypatch.setattr(
        "aura_cli.core.tools.deep_analysis.rprint", MagicMock(), raising=False
    )
    monkeypatch.setattr(
        "aura_cli.core.tools.deep_analysis._display_tool_call",
        MagicMock(),
        raising=False,
    )
    monkeypatch.setattr(
        "aura_cli.core.tools.deep_analysis.logger", MagicMock(), raising=False
    )
    monkeypatch.setattr(
        "aura_cli.core.tools.deep_analysis._get_stats", lambda: None, raising=False
    )
    monkeypatch.setattr(
        "aura_cli.core.tools.deep_analysis._get_ui_constants",
        lambda: (MagicMock(SUCCESS="✓"), MagicMock(SUCCESS="green")),
        raising=False,
    )


from aura_cli.core.tools.deep_analysis import (
    _analyze_architecture,
    _analyze_quality,
    _collect_file_stats,
    _extract_patterns_from_file,
    _generate_recommendations,
    _report_section,
)


# ---------------------------------------------------------------------------
# _report_section
# ---------------------------------------------------------------------------
class TestReportSection:
    def test_empty_items_appends_nothing(self):
        parts: list = []
        _report_section(parts, "## Title", [])
        assert parts == []

    def test_appends_title_and_items(self):
        parts: list = []
        _report_section(parts, "## Title", ["a", "b"])
        assert "## Title" in parts
        assert "- `a`" in parts
        assert "- `b`" in parts

    def test_custom_format(self):
        parts: list = []
        _report_section(parts, "T", ["x"], fmt="* {}")
        assert "* x" in parts

    def test_trailing_empty_string(self):
        parts: list = []
        _report_section(parts, "T", ["x"])
        # ends with empty string separator
        assert parts[-1] == ""


# ---------------------------------------------------------------------------
# _collect_file_stats
# ---------------------------------------------------------------------------
class TestCollectFileStats:
    def test_empty_dir(self, tmp_path):
        stats = _collect_file_stats(tmp_path)
        assert stats["total_files"] == 0
        assert stats["code_files"] == 0
        assert stats["config_files"] == 0
        assert stats["doc_files"] == 0
        assert stats["by_extension"] == {}

    def test_counts_code_files(self, tmp_path):
        (tmp_path / "main.py").write_text("x = 1")
        (tmp_path / "app.js").write_text("var x;")
        stats = _collect_file_stats(tmp_path)
        assert stats["total_files"] == 2
        assert stats["code_files"] == 2

    def test_counts_config_files(self, tmp_path):
        (tmp_path / "config.yaml").write_text("key: val")
        (tmp_path / "setup.cfg").write_text("[meta]")
        stats = _collect_file_stats(tmp_path)
        assert stats["config_files"] == 2

    def test_counts_doc_files(self, tmp_path):
        (tmp_path / "README.md").write_text("# Readme")
        stats = _collect_file_stats(tmp_path)
        assert stats["doc_files"] == 1

    def test_by_extension_populated(self, tmp_path):
        (tmp_path / "a.py").write_text("")
        (tmp_path / "b.py").write_text("")
        (tmp_path / "c.js").write_text("")
        stats = _collect_file_stats(tmp_path)
        assert stats["by_extension"][".py"] == 2
        assert stats["by_extension"][".js"] == 1

    def test_ignores_git_and_pycache(self, tmp_path):
        git_dir = tmp_path / ".git"
        git_dir.mkdir()
        (git_dir / "config").write_text("")
        cache_dir = tmp_path / "__pycache__"
        cache_dir.mkdir()
        (cache_dir / "mod.pyc").write_text("")
        stats = _collect_file_stats(tmp_path)
        assert stats["total_files"] == 0

    def test_ignores_venv(self, tmp_path):
        venv = tmp_path / "venv"
        venv.mkdir()
        (venv / "activate").write_text("")
        stats = _collect_file_stats(tmp_path)
        assert stats["total_files"] == 0

    def test_nested_files_counted(self, tmp_path):
        sub = tmp_path / "src"
        sub.mkdir()
        (sub / "utils.py").write_text("")
        stats = _collect_file_stats(tmp_path)
        assert stats["total_files"] == 1
        assert stats["code_files"] == 1


# ---------------------------------------------------------------------------
# _analyze_quality
# ---------------------------------------------------------------------------
class TestAnalyzeQuality:
    def test_empty_dir_no_findings(self, tmp_path):
        result = _analyze_quality(tmp_path, max_files=50)
        assert result["issues"] == []
        assert result["patterns"] == []

    def test_detects_wildcard_import(self, tmp_path):
        (tmp_path / "bad.py").write_text("from os import *\n")
        result = _analyze_quality(tmp_path, max_files=50)
        assert any("wildcard" in i for i in result["issues"])

    def test_detects_bare_except(self, tmp_path):
        (tmp_path / "bad.py").write_text("try:\n    pass\nexcept:\n    pass\n")
        result = _analyze_quality(tmp_path, max_files=50)
        assert any("bare except" in i for i in result["issues"])

    def test_detects_todo(self, tmp_path):
        (tmp_path / "todo.py").write_text("# TODO: fix this\n")
        result = _analyze_quality(tmp_path, max_files=50)
        assert any("TODO" in i for i in result["issues"])

    def test_detects_oop_pattern(self, tmp_path):
        (tmp_path / "good.py").write_text(
            "class Foo:\n    def __init__(self):\n        self.x = 1\n"
        )
        result = _analyze_quality(tmp_path, max_files=50)
        assert any("OOP" in p for p in result["patterns"])

    def test_detects_logging_pattern(self, tmp_path):
        (tmp_path / "log.py").write_text(
            "import logging\nlogger = logging.getLogger()\n"
        )
        result = _analyze_quality(tmp_path, max_files=50)
        assert any("logging" in p for p in result["patterns"])

    def test_respects_max_files(self, tmp_path):
        for i in range(5):
            (tmp_path / f"f{i}.py").write_text("import *\n")
        result = _analyze_quality(tmp_path, max_files=2)
        # only 2 files analysed, so at most 2 issues
        assert len(result["issues"]) <= 2

    def test_ignores_pycache(self, tmp_path):
        cache = tmp_path / "__pycache__"
        cache.mkdir()
        (cache / "mod.py").write_text("from os import *\n")
        result = _analyze_quality(tmp_path, max_files=50)
        assert result["issues"] == []


# ---------------------------------------------------------------------------
# _analyze_architecture
# ---------------------------------------------------------------------------
class TestAnalyzeArchitecture:
    def test_empty_dir(self, tmp_path):
        result = _analyze_architecture(tmp_path)
        assert result["entry_points"] == []
        assert result["core_modules"] == []

    def test_finds_main_py(self, tmp_path):
        (tmp_path / "main.py").write_text("")
        result = _analyze_architecture(tmp_path)
        assert any("main.py" in ep for ep in result["entry_points"])

    def test_finds_app_py(self, tmp_path):
        (tmp_path / "app.py").write_text("")
        result = _analyze_architecture(tmp_path)
        assert any("app.py" in ep for ep in result["entry_points"])

    def test_finds_manage_py(self, tmp_path):
        (tmp_path / "manage.py").write_text("")
        result = _analyze_architecture(tmp_path)
        assert any("manage.py" in ep for ep in result["entry_points"])

    def test_finds_core_modules(self, tmp_path):
        pkg = tmp_path / "mypackage"
        pkg.mkdir()
        (pkg / "__init__.py").write_text("")
        result = _analyze_architecture(tmp_path)
        assert any("mypackage" in m for m in result["core_modules"])

    def test_deep_packages_excluded(self, tmp_path):
        """Packages at depth > 2 should not appear in core_modules."""
        deep = tmp_path / "a" / "b" / "c"
        deep.mkdir(parents=True)
        (deep / "__init__.py").write_text("")
        result = _analyze_architecture(tmp_path)
        # c is at depth 3, should not appear
        assert not any(m.split("/")[-1] == "c" for m in result["core_modules"])


# ---------------------------------------------------------------------------
# _generate_recommendations
# ---------------------------------------------------------------------------
class TestGenerateRecommendations:
    def test_recommends_docs_when_few(self):
        file_stats = {"code_files": 150, "doc_files": 2, "by_extension": {}}
        recs = _generate_recommendations(file_stats, ["quality"])
        assert any("documentation" in r.lower() for r in recs)

    def test_recommends_test_coverage(self):
        file_stats = {"code_files": 60, "doc_files": 10, "by_extension": {}}
        recs = _generate_recommendations(file_stats, [])
        assert any("test" in r.lower() or "coverage" in r.lower() for r in recs)

    def test_quality_area_adds_linting_rec(self):
        file_stats = {"code_files": 5, "doc_files": 5, "by_extension": {}}
        recs = _generate_recommendations(file_stats, ["quality"])
        assert any("lint" in r.lower() for r in recs)

    def test_architecture_area_adds_architecture_rec(self):
        file_stats = {"code_files": 5, "doc_files": 5, "by_extension": {}}
        recs = _generate_recommendations(file_stats, ["architecture"])
        assert any("architecture" in r.lower() for r in recs)

    def test_fallback_when_no_recs(self):
        file_stats = {"code_files": 1, "doc_files": 10, "by_extension": {}}
        recs = _generate_recommendations(file_stats, [])
        assert len(recs) >= 1


# ---------------------------------------------------------------------------
# _extract_patterns_from_file
# ---------------------------------------------------------------------------
class TestExtractPatternsFromFile:
    def _empty_patterns(self):
        return {"naming": [], "structure": [], "testing": [], "error": []}

    def test_pascal_case_classes(self):
        patterns = self._empty_patterns()
        _extract_patterns_from_file(
            "class MyClass:\n    pass\nclass AnotherClass:\n    pass\n",
            "file.py",
            patterns,
        )
        assert any("PascalCase" in p for p in patterns["naming"])

    def test_snake_case_functions(self):
        patterns = self._empty_patterns()
        _extract_patterns_from_file(
            "def my_func():\n    pass\ndef another_one():\n    pass\n",
            "file.py",
            patterns,
        )
        assert any("snake_case" in p for p in patterns["naming"])

    def test_dataclass_detected(self):
        patterns = self._empty_patterns()
        _extract_patterns_from_file(
            "@dataclass\nclass Foo:\n    x: int\n", "f.py", patterns
        )
        assert any("dataclass" in p for p in patterns["structure"])

    def test_typing_detected(self):
        patterns = self._empty_patterns()
        _extract_patterns_from_file("from typing import List\n", "f.py", patterns)
        assert any("type" in p.lower() for p in patterns["structure"])

    def test_async_detected(self):
        patterns = self._empty_patterns()
        _extract_patterns_from_file("async def run():\n    pass\n", "f.py", patterns)
        assert any("async" in p for p in patterns["structure"])

    def test_test_prefix_detected(self):
        patterns = self._empty_patterns()
        _extract_patterns_from_file(
            "def test_foo():\n    pass\n", "test_f.py", patterns
        )
        assert any("test_" in p for p in patterns["testing"])

    def test_pytest_decorator_detected(self):
        patterns = self._empty_patterns()
        _extract_patterns_from_file(
            "@pytest.mark.parametrize\ndef test_x():\n    pass\n", "t.py", patterns
        )
        assert any("pytest" in p for p in patterns["testing"])

    def test_try_except_detected(self):
        patterns = self._empty_patterns()
        _extract_patterns_from_file(
            "try:\n    x()\nexcept Exception:\n    pass\n", "f.py", patterns
        )
        assert any("try/except" in p for p in patterns["error"])

    def test_raise_detected(self):
        patterns = self._empty_patterns()
        _extract_patterns_from_file("raise ValueError('bad')\n", "f.py", patterns)
        assert any("raise" in p.lower() for p in patterns["error"])

    def test_empty_content(self):
        patterns = self._empty_patterns()
        _extract_patterns_from_file("", "empty.py", patterns)
        # no crash, lists remain (may be empty or not)


# ---------------------------------------------------------------------------
# deep_project_analysis (integration-light)
# ---------------------------------------------------------------------------
class TestDeepProjectAnalysis:
    def test_nonexistent_path_returns_error(self):
        from aura_cli.core.tools.deep_analysis import deep_project_analysis

        with patch("aura_cli.core.tools.deep_analysis._display_tool_call", MagicMock()):
            result = deep_project_analysis("/nonexistent/path/xyz")
        assert "não existe" in result or "Erro" in result

    def test_returns_markdown_report(self, tmp_path):
        (tmp_path / "main.py").write_text("def hello(): pass\n")
        from aura_cli.core.tools.deep_analysis import deep_project_analysis

        with (
            patch("aura_cli.core.tools.deep_analysis._display_tool_call", MagicMock()),
            patch("aura_cli.core.tools.deep_analysis.rprint", MagicMock()),
            patch(
                "aura_cli.core.tools.deep_analysis._get_ui_constants",
                return_value=(MagicMock(SUCCESS="✓"), MagicMock(SUCCESS="green")),
            ),
            patch(
                "aura_cli.core.tools.deep_analysis._get_stats",
                return_value=None,
            ),
        ):
            # tree_view may fail — that's OK
            with patch(
                "aura_cli.core.tools.deep_analysis.tree_view",
                side_effect=ImportError,
                create=True,
            ):
                result = deep_project_analysis(str(tmp_path))
        assert "# 🔍 Deep Project Analysis" in result
        assert "File Statistics" in result


# ---------------------------------------------------------------------------
# analyze_dependencies (integration-light)
# ---------------------------------------------------------------------------
class TestAnalyzeDependencies:
    def test_nonexistent_path(self):
        from aura_cli.core.tools.deep_analysis import analyze_dependencies

        result = analyze_dependencies("/nope/nope")
        assert "não existe" in result or "Erro" in result

    def test_reads_requirements_txt(self, tmp_path):
        (tmp_path / "requirements.txt").write_text("requests==2.28.0\npytest==7.0.0\n")
        from aura_cli.core.tools.deep_analysis import analyze_dependencies

        with (
            patch("aura_cli.core.tools.deep_analysis.rprint", MagicMock()),
            patch(
                "aura_cli.core.tools.deep_analysis._get_ui_constants",
                return_value=(MagicMock(SUCCESS="✓"), MagicMock(SUCCESS="green")),
            ),
        ):
            result = analyze_dependencies(str(tmp_path))
        assert "requests" in result
        assert "pytest" in result

    def test_reads_package_json(self, tmp_path):
        import json

        pkg = {
            "dependencies": {"express": "^4.18.0"},
            "devDependencies": {"jest": "^29.0.0"},
        }
        (tmp_path / "package.json").write_text(json.dumps(pkg))
        from aura_cli.core.tools.deep_analysis import analyze_dependencies

        with (
            patch("aura_cli.core.tools.deep_analysis.rprint", MagicMock()),
            patch(
                "aura_cli.core.tools.deep_analysis._get_ui_constants",
                return_value=(MagicMock(SUCCESS="✓"), MagicMock(SUCCESS="green")),
            ),
        ):
            result = analyze_dependencies(str(tmp_path))
        assert "express" in result
