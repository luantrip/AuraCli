"""Tests for core/tools/project_analyzer.py — helper functions + main function."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

# ── helpers ──────────────────────────────────────────────────────────────────
from aura_cli.core.tools.project_analyzer import (
    _extract_purpose,
    _extract_technologies,
    _generate_recommendations,
    _generate_summary,
    _identify_project_fronts,
    _parse_directory_listing,
    _read_key_files,
    analyze_project_structure,
)


class TestParseDirListing:
    def test_empty_string(self):
        result = _parse_directory_listing("")
        assert result == {"items": [], "count": 0}

    def test_parses_file_entry(self):
        listing = "┃ 📄 main.py ┃"
        result = _parse_directory_listing(listing)
        assert result["count"] == 1
        assert result["items"][0]["name"] == "main.py"
        assert result["items"][0]["type"] == "file"

    def test_parses_directory_entry(self):
        listing = "┃ 📁 src/ ┃"
        result = _parse_directory_listing(listing)
        assert result["items"][0]["type"] == "directory"
        assert result["items"][0]["name"] == "src"

    def test_ignores_lines_without_pipe(self):
        listing = "no pipe here\n┃ 📄 file.py ┃"
        result = _parse_directory_listing(listing)
        assert result["count"] == 1

    def test_multiple_entries(self):
        listing = "┃ 📄 a.py ┃\n┃ 📁 b/ ┃\n┃ 📄 c.py ┃"
        result = _parse_directory_listing(listing)
        assert result["count"] == 3


class TestExtractTechnologies:
    def test_empty(self):
        result = _extract_technologies({})
        assert result == []

    def test_detects_python_from_requirements(self):
        techs = _extract_technologies({"root": {"requirements.txt": "flask\nrequests"}})
        assert "Python" in techs

    def test_detects_python_from_pyproject(self):
        techs = _extract_technologies({"root": {"pyproject.toml": "[tool.poetry]"}})
        assert "Python" in techs

    def test_detects_nodejs(self):
        pkg = json.dumps({"dependencies": {"express": "^4.0"}})
        techs = _extract_technologies({"root": {"package.json": pkg}})
        assert "Node.js" in techs

    def test_detects_react(self):
        pkg = json.dumps({"dependencies": {"react": "^18.0"}})
        techs = _extract_technologies({"root": {"package.json": pkg}})
        assert "React" in techs

    def test_detects_vue(self):
        pkg = json.dumps({"dependencies": {"vue": "^3.0"}})
        techs = _extract_technologies({"root": {"package.json": pkg}})
        assert "Vue.js" in techs

    def test_detects_docker(self):
        techs = _extract_technologies({"root": {"Dockerfile": "FROM python:3.11"}})
        assert "Docker" in techs

    def test_detects_docker_compose(self):
        techs = _extract_technologies({"root": {"docker-compose.yml": "version: '3'"}})
        assert "Docker Compose" in techs

    def test_invalid_json_pkg_ignored(self):
        techs = _extract_technologies({"root": {"package.json": "not-json"}})
        # Should not raise
        assert isinstance(techs, list)

    def test_no_duplicates(self):
        data = {"a": {"requirements.txt": "x"}, "b": {"requirements.txt": "y"}}
        techs = _extract_technologies(data)
        assert techs.count("Python") == 1


class TestExtractPurpose:
    def test_empty(self):
        result = _extract_purpose({})
        assert result == "Não especificado"

    def test_extracts_from_readme(self):
        readme = "# Title\n\nThis is a long enough description of the project purpose here.\n"
        result = _extract_purpose({"root": {"README.md": readme}})
        assert "description" in result

    def test_skips_header_lines(self):
        readme = "# Header\n## Sub\nShort.\nThis is a proper long enough description line that exceeds fifty characters.\n"
        result = _extract_purpose({"root": {"README.md": readme}})
        assert "Header" not in result

    def test_skips_lines_under_50_chars(self):
        readme = "Short line.\nThis is a sufficiently long description line for the project.\n"
        result = _extract_purpose({"root": {"README.md": readme}})
        assert "Short" not in result

    def test_combines_multiple_fronts(self):
        readme = (
            "This is a sufficiently long description line for the project purpose.\n"
        )
        result = _extract_purpose(
            {"a": {"README.md": readme}, "b": {"README.md": readme}}
        )
        assert "|" in result


class TestIdentifyProjectFronts:
    def _root(self, items):
        return {"items": [{"name": n, "type": "directory"} for n in items]}

    def test_detects_backend(self):
        fronts = _identify_project_fronts(Path("."), self._root(["backend"]))
        assert any(f["type"] == "backend" for f in fronts)

    def test_detects_frontend(self):
        fronts = _identify_project_fronts(Path("."), self._root(["frontend"]))
        assert any(f["type"] == "frontend" for f in fronts)

    def test_detects_mobile(self):
        fronts = _identify_project_fronts(Path("."), self._root(["mobile"]))
        assert any(f["type"] == "mobile" for f in fronts)

    def test_detects_docs(self):
        fronts = _identify_project_fronts(Path("."), self._root(["docs"]))
        assert any(f["type"] == "docs" for f in fronts)

    def test_ignores_files(self):
        root = {"items": [{"name": "backend", "type": "file"}]}
        fronts = _identify_project_fronts(Path("."), root)
        assert fronts == []

    def test_empty_structure(self):
        fronts = _identify_project_fronts(Path("."), {})
        assert fronts == []

    def test_unknown_dir_ignored(self):
        fronts = _identify_project_fronts(Path("."), self._root(["random_dir"]))
        assert fronts == []


class TestGenerateSummary:
    def _base_result(self):
        return {
            "project_root": "/tmp/project",
            "fronts": [],
            "technologies": [],
            "purpose": "",
            "key_files": {},
        }

    def test_contains_project_root(self):
        summary = _generate_summary(self._base_result())
        assert "/tmp/project" in summary

    def test_lists_fronts(self):
        r = self._base_result()
        r["fronts"] = [{"name": "Backend"}, {"name": "Frontend"}]
        summary = _generate_summary(r)
        assert "Backend" in summary
        assert "Frontend" in summary

    def test_lists_technologies(self):
        r = self._base_result()
        r["technologies"] = ["Python", "Docker"]
        summary = _generate_summary(r)
        assert "Python" in summary

    def test_purpose_truncated_to_150(self):
        r = self._base_result()
        r["purpose"] = "x" * 200
        summary = _generate_summary(r)
        # purpose snippet is cut at 150
        assert "x" * 150 in summary
        assert "x" * 151 not in summary

    def test_architecture_entry_points(self):
        r = self._base_result()
        r["architecture"] = {"entry_points": ["a", "b", "c"], "patterns": []}
        summary = _generate_summary(r)
        assert "3" in summary

    def test_tests_info(self):
        r = self._base_result()
        r["tests"] = {
            "test_directories": [{"d": "x"}],
            "test_files": [{"f": "y"}, {"f": "z"}],
            "test_frameworks": [{"framework": "pytest"}],
        }
        summary = _generate_summary(r)
        assert "pytest" in summary


class TestGenerateRecommendations:
    def _base(self, has_readme=False, fronts=None, techs=None):
        return {
            "key_files": {"root": {"README.md": "x"} if has_readme else {}},
            "fronts": fronts or [],
            "technologies": techs or [],
        }

    def test_suggests_readme_when_missing(self):
        recs = _generate_recommendations(self._base(has_readme=False))
        assert any("README" in r for r in recs)

    def test_no_readme_suggestion_when_present(self):
        recs = _generate_recommendations(self._base(has_readme=True))
        assert not any("README" in r for r in recs)

    def test_suggests_exploring_fronts(self):
        recs = _generate_recommendations(self._base(fronts=[{"name": "API"}]))
        assert any("API" in r for r in recs)

    def test_always_has_codebase_search_tip(self):
        recs = _generate_recommendations(self._base())
        assert any("codebase_search" in r for r in recs)


class TestReadKeyFiles:
    def test_reads_existing_files(self, tmp_path):
        (tmp_path / "README.md").write_text("hello")
        result = _read_key_files(tmp_path)
        assert "README.md" in result
        assert result["README.md"] == "hello"

    def test_skips_missing_files(self, tmp_path):
        result = _read_key_files(tmp_path)
        assert "README.md" not in result

    def test_truncates_large_file(self, tmp_path):
        (tmp_path / "README.md").write_text("x" * 6000)
        result = _read_key_files(tmp_path)
        assert len(result["README.md"]) < 6000
        assert "truncated" in result["README.md"]

    def test_handles_read_error(self, tmp_path, monkeypatch):
        (tmp_path / "README.md").write_text("x")
        import aura_cli.core.tools.project_analyzer as mod

        original = mod.read_file
        mod.read_file = MagicMock(side_effect=Exception("read error"))
        result = _read_key_files(tmp_path)
        mod.read_file = original
        assert "README.md" in result
        assert "Erro" in result["README.md"]


class TestAnalyzeProjectStructure:
    @patch("aura_cli.core.tools.project_analyzer.get_stats")
    def test_nonexistent_path_returns_error(self, mock_stats, tmp_path):
        with patch("aura_cli.core.ui.display_tool_call", create=True):
            result = analyze_project_structure(str(tmp_path / "nonexistent"))
        assert "error" in result

    @patch("aura_cli.core.tools.project_analyzer.get_stats")
    def test_file_path_returns_error(self, mock_stats, tmp_path):
        f = tmp_path / "file.txt"
        f.write_text("x")
        with patch("aura_cli.core.ui.display_tool_call", create=True):
            result = analyze_project_structure(str(f))
        assert "error" in result

    @patch("aura_cli.core.tools.project_analyzer.get_stats")
    @patch("aura_cli.core.tools.project_analyzer.list_directory")
    @patch("aura_cli.core.tools.project_analyzer.read_file")
    def test_valid_dir_returns_structure(
        self, mock_read, mock_list, mock_stats, tmp_path
    ):
        mock_list.return_value = ""
        mock_read.return_value = "content"
        mock_stats.return_value = MagicMock()
        with patch("aura_cli.core.ui.display_tool_call", create=True):
            result = analyze_project_structure(
                str(tmp_path),
                include_subprojects=False,
                analyze_architecture=False,
                analyze_dependencies=False,
                analyze_tests=False,
            )
        assert "project_root" in result
        assert "fronts" in result
        assert "summary" in result

    @patch("aura_cli.core.tools.project_analyzer.get_stats")
    @patch(
        "aura_cli.core.tools.project_analyzer.list_directory",
        side_effect=Exception("fail"),
    )
    def test_list_directory_error_graceful(self, mock_list, mock_stats, tmp_path):
        mock_stats.return_value = MagicMock()
        with patch("aura_cli.core.ui.display_tool_call", create=True):
            result = analyze_project_structure(
                str(tmp_path),
                include_subprojects=False,
                read_key_files=False,
                analyze_architecture=False,
                analyze_dependencies=False,
                analyze_tests=False,
            )
        assert "error" in result["structure"]["root"]

    @patch("aura_cli.core.tools.project_analyzer.get_stats")
    @patch("aura_cli.core.tools.project_analyzer.list_directory")
    @patch("aura_cli.core.tools.project_analyzer.read_file")
    def test_analyze_all_flags(self, mock_read, mock_list, mock_stats, tmp_path):
        mock_list.return_value = ""
        mock_read.return_value = "x"
        mock_stats.return_value = MagicMock()
        with patch("aura_cli.core.ui.display_tool_call", create=True):
            result = analyze_project_structure(
                str(tmp_path),
                include_subprojects=True,
                analyze_architecture=True,
                analyze_dependencies=True,
                analyze_tests=True,
            )
        assert "architecture" in result
        assert "dependencies" in result
        assert "tests" in result
