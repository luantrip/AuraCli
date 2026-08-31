"""Tests for core/tools/codebase_tools.py — search and navigation functions."""

from unittest.mock import MagicMock, patch

import pytest

from aura_cli.core.tools.codebase_tools import (
    advanced_grep_search,
    codebase_search,
    glob_search,
    view_repo_map,
    view_subdirectory,
)


@pytest.fixture(autouse=True)
def _patch_ui(monkeypatch):
    monkeypatch.setattr("aura_cli.core.tools.codebase_tools.console", MagicMock())
    monkeypatch.setattr(
        "aura_cli.core.tools.codebase_tools.get_stats", lambda: MagicMock()
    )


@pytest.fixture
def project(tmp_path):
    """Create a minimal project structure."""
    (tmp_path / "main.py").write_text("def main():\n    print('hello')\n")
    (tmp_path / "utils.py").write_text("def helper():\n    return 42\n# TODO: fix\n")
    sub = tmp_path / "src"
    sub.mkdir()
    (sub / "app.py").write_text("class App:\n    pass\n")
    (sub / "config.json").write_text('{"key": "value"}\n')
    return tmp_path


class TestCodebaseSearch:
    @patch("aura_cli.core.tools.codebase_tools.display_tool_call", create=True)
    def test_finds_text(self, _d, project, monkeypatch):
        monkeypatch.setattr(
            "aura_cli.core.tools.codebase_tools.display_tool_call",
            MagicMock(),
            raising=False,
        )
        with patch("aura_cli.core.ui.display_tool_call", MagicMock(), create=True):
            result = codebase_search("def main", path=str(project))
        assert "main.py" in result
        assert "Encontrados" in result

    def test_no_results(self, project):
        with patch("aura_cli.core.ui.display_tool_call", MagicMock(), create=True):
            result = codebase_search("nonexistent_xyz", path=str(project))
        assert "Nenhum resultado" in result

    def test_filter_by_extension(self, project):
        with patch("aura_cli.core.ui.display_tool_call", MagicMock(), create=True):
            result = codebase_search(
                "key", path=str(project), filters={"file_extensions": [".json"]}
            )
        assert "config.json" in result

    def test_case_insensitive_default(self, project):
        with patch("aura_cli.core.ui.display_tool_call", MagicMock(), create=True):
            result = codebase_search("DEF MAIN", path=str(project))
        assert "main.py" in result

    def test_case_sensitive(self, project):
        with patch("aura_cli.core.ui.display_tool_call", MagicMock(), create=True):
            result = codebase_search(
                "DEF MAIN", path=str(project), filters={"case_sensitive": True}
            )
        assert "Nenhum resultado" in result

    def test_max_results(self, project):
        with patch("aura_cli.core.ui.display_tool_call", MagicMock(), create=True):
            result = codebase_search("def", path=str(project), max_results=1)
        # Should have at most 1 result
        lines = [line for line in result.split("\n") if ":" in line and ".py" in line]
        assert len(lines) <= 1

    def test_regex_pattern(self, project):
        with patch("aura_cli.core.ui.display_tool_call", MagicMock(), create=True):
            result = codebase_search(r"def \w+\(\)", path=str(project))
        assert "Encontrados" in result

    def test_invalid_regex_escaped(self, project):
        with patch("aura_cli.core.ui.display_tool_call", MagicMock(), create=True):
            result = codebase_search("[invalid", path=str(project))
        # Should not crash — escapes the pattern
        assert isinstance(result, str)

    def test_exclude_dirs(self, project):
        hidden = project / ".git"
        hidden.mkdir()
        (hidden / "config").write_text("def secret()")
        with patch("aura_cli.core.ui.display_tool_call", MagicMock(), create=True):
            result = codebase_search("secret", path=str(project))
        assert "Nenhum resultado" in result

    def test_skip_comments_filter(self, project):
        with patch("aura_cli.core.ui.display_tool_call", MagicMock(), create=True):
            result = codebase_search(
                "TODO", path=str(project), filters={"search_in_comments": False}
            )
        assert "Nenhum resultado" in result


class TestGlobSearch:
    def test_finds_python_files(self, project):
        with patch("aura_cli.core.ui.display_tool_call", MagicMock(), create=True):
            result = glob_search("**/*.py", path=str(project))
        assert "main.py" in result
        assert "Encontrados" in result

    def test_finds_json_files(self, project):
        with patch("aura_cli.core.ui.display_tool_call", MagicMock(), create=True):
            result = glob_search("**/*.json", path=str(project))
        assert "config.json" in result

    def test_no_matches(self, project):
        with patch("aura_cli.core.ui.display_tool_call", MagicMock(), create=True):
            result = glob_search("**/*.rs", path=str(project))
        assert "Nenhum arquivo" in result

    def test_exclude_pattern(self, project):
        with patch("aura_cli.core.ui.display_tool_call", MagicMock(), create=True):
            result = glob_search("**/*.py", path=str(project), exclude=["**/main*"])
        assert "main.py" not in result


class TestAdvancedGrepSearch:
    def test_basic_search(self, project):
        with patch("aura_cli.core.ui.display_tool_call", MagicMock(), create=True):
            result = advanced_grep_search("class", path=str(project))
        assert "app.py" in result

    def test_no_results(self, project):
        with patch("aura_cli.core.ui.display_tool_call", MagicMock(), create=True):
            result = advanced_grep_search("nonexistent_xyz", path=str(project))
        assert "Nenhum resultado" in result

    def test_invalid_regex(self, project):
        with patch("aura_cli.core.ui.display_tool_call", MagicMock(), create=True):
            result = advanced_grep_search("[invalid", path=str(project))
        assert "Invalid" in result or "invalid" in result.lower()

    def test_whole_word(self, project):
        with patch("aura_cli.core.ui.display_tool_call", MagicMock(), create=True):
            result = advanced_grep_search(
                "main", path=str(project), options={"whole_word": True}
            )
        assert "main.py" in result

    def test_context_lines(self, project):
        with patch("aura_cli.core.ui.display_tool_call", MagicMock(), create=True):
            result = advanced_grep_search(
                "def main", path=str(project), options={"context_lines": 1}
            )
        assert ">>>" in result

    def test_invert_match(self, project):
        with patch("aura_cli.core.ui.display_tool_call", MagicMock(), create=True):
            result = advanced_grep_search(
                "def", path=str(project), options={"invert_match": True}
            )
        # Lines NOT containing "def"
        assert "Encontrados" in result

    def test_filter_extension(self, project):
        with patch("aura_cli.core.ui.display_tool_call", MagicMock(), create=True):
            result = advanced_grep_search(
                "key", path=str(project), options={"file_extensions": [".json"]}
            )
        assert "config.json" in result
        assert "main.py" not in result


class TestViewRepoMap:
    def test_returns_tree(self, project):
        with patch("aura_cli.core.ui.display_tool_call", MagicMock(), create=True):
            result = view_repo_map(path=str(project))
        assert "main.py" in result
        assert "src/" in result

    def test_respects_depth(self, project):
        deep = project / "a" / "b" / "c"
        deep.mkdir(parents=True)
        (deep / "deep.py").write_text("")
        with patch("aura_cli.core.ui.display_tool_call", MagicMock(), create=True):
            result = view_repo_map(path=str(project), depth=1)
        assert "deep.py" not in result

    def test_excludes_pycache(self, project):
        cache = project / "__pycache__"
        cache.mkdir()
        (cache / "mod.pyc").write_text("")
        with patch("aura_cli.core.ui.display_tool_call", MagicMock(), create=True):
            result = view_repo_map(path=str(project))
        assert "__pycache__" not in result


class TestViewSubdirectory:
    def test_returns_tree(self, project):
        with patch("aura_cli.core.ui.display_tool_call", MagicMock(), create=True):
            result = view_subdirectory(path=str(project / "src"))
        assert "app.py" in result

    def test_nonexistent_path(self, project):
        with patch("aura_cli.core.ui.display_tool_call", MagicMock(), create=True):
            result = view_subdirectory(path=str(project / "nope"))
        # Should handle gracefully
        assert isinstance(result, str)
