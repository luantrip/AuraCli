"""Tests for core/tools/project_insights.py — helper functions."""

import json
from pathlib import Path
from unittest.mock import patch

from aura_cli.core.tools.project_insights import (
    _analyze_structure_issues,
    _check_dependency_vulnerabilities,
    _check_readme_completeness,
    _extract_front_technologies,
    _find_front_differences,
    _find_front_similarities,
    _find_shared_dependencies,
    _generate_documentation_recommendations,
    _generate_quality_recommendations,
    _generate_security_recommendations,
    _parse_directory_listing_simple,
    _parse_duplication_results,
)


class TestParseDuplicationResults:
    def test_empty(self):
        assert _parse_duplication_results("") == []

    def test_finds_duplicate_lines(self):
        result = _parse_duplication_results("Found 3 duplicate blocks\nAnother line")
        assert len(result) == 1
        assert result[0]["severity"] == "medium"

    def test_finds_similar_lines(self):
        result = _parse_duplication_results("Similar code in file_a and file_b")
        assert len(result) == 1

    def test_limits_to_20(self):
        lines = "\n".join(f"duplicate block {i}" for i in range(30))
        result = _parse_duplication_results(lines)
        assert len(result) == 20


class TestParseDirectoryListingSimple:
    def test_empty(self):
        assert _parse_directory_listing_simple("") == []

    def test_parses_file(self):
        result = _parse_directory_listing_simple("┃ 📄 main.py ┃")
        assert len(result) == 1
        assert result[0]["name"] == "main.py"
        assert result[0]["type"] == "file"

    def test_parses_dir(self):
        result = _parse_directory_listing_simple("┃ 📁 src/ ┃")
        assert len(result) == 1
        assert result[0]["type"] == "directory"

    def test_ignores_non_pipe_lines(self):
        result = _parse_directory_listing_simple("no pipe\n┃ 📄 f.py ┃")
        assert len(result) == 1


class TestAnalyzeStructureIssues:
    @patch("aura_cli.core.tools.project_insights.list_directory")
    def test_flat_structure_detected(self, mock_list):
        # 25 files
        lines = "\n".join(f"┃ 📄 file{i}.py ┃" for i in range(25))
        mock_list.return_value = lines
        issues = _analyze_structure_issues(Path("/tmp"))
        assert any("flat_structure" in i["type"] for i in issues)

    @patch("aura_cli.core.tools.project_insights.list_directory")
    def test_few_files_no_issue(self, mock_list):
        lines = "\n".join(f"┃ 📄 file{i}.py ┃" for i in range(5))
        mock_list.return_value = lines
        issues = _analyze_structure_issues(Path("/tmp"))
        assert issues == []

    @patch(
        "aura_cli.core.tools.project_insights.list_directory",
        side_effect=Exception("fail"),
    )
    def test_exception_handled(self, mock_list):
        issues = _analyze_structure_issues(Path("/tmp"))
        assert issues == []


class TestGenerateQualityRecommendations:
    def test_all_issues(self):
        result = {
            "duplication": [{"x": 1}],
            "complexity": [{"x": 1}],
            "smells": [{"x": 1}],
            "structure_issues": [{"x": 1}],
        }
        recs = _generate_quality_recommendations(result)
        assert len(recs) == 4

    def test_no_issues(self):
        recs = _generate_quality_recommendations({})
        assert len(recs) == 1
        assert "boa qualidade" in recs[0]


class TestGenerateSecurityRecommendations:
    def test_with_secrets(self):
        result = {"secrets_found": [{"x": 1}]}
        recs = _generate_security_recommendations(result)
        assert any("secrets" in r.lower() for r in recs)

    def test_with_vulnerabilities(self):
        result = {"vulnerable_dependencies": [{"x": 1}]}
        recs = _generate_security_recommendations(result)
        assert any("vulneráveis" in r.lower() or "atualizar" in r.lower() for r in recs)

    def test_no_issues(self):
        recs = _generate_security_recommendations({})
        assert len(recs) == 2
        assert any("nenhum" in r.lower() for r in recs)


class TestCheckReadmeCompleteness:
    @patch("aura_cli.core.tools.project_insights.read_file")
    def test_no_readme(self, mock_read, tmp_path):
        result = _check_readme_completeness(tmp_path)
        assert result["root_readme"] is False
        assert result["completeness_score"] == 0

    @patch("aura_cli.core.tools.project_insights.read_file")
    def test_with_readme(self, mock_read, tmp_path):
        (tmp_path / "README.md").write_text("x")
        mock_read.return_value = "# Title\n## Installation\n## Usage\n## Contributing\n## License\nDescription here"
        result = _check_readme_completeness(tmp_path)
        assert result["root_readme"] is True
        assert result["completeness_score"] > 0

    @patch(
        "aura_cli.core.tools.project_insights.read_file", side_effect=Exception("err")
    )
    def test_read_error(self, mock_read, tmp_path):
        (tmp_path / "README.md").write_text("x")
        result = _check_readme_completeness(tmp_path)
        assert result["root_readme"] is True


class TestGenerateDocumentationRecommendations:
    def test_no_readme(self):
        recs = _generate_documentation_recommendations(
            {"readme_status": {"root_readme": False}}
        )
        assert any("README" in r for r in recs)

    def test_low_completeness(self):
        recs = _generate_documentation_recommendations(
            {"readme_status": {"root_readme": True, "completeness_score": 30}}
        )
        assert any("completude" in r.lower() for r in recs)

    def test_low_code_docs(self):
        recs = _generate_documentation_recommendations(
            {
                "readme_status": {"root_readme": True, "completeness_score": 90},
                "code_documentation": {"coverage_percentage": 20},
            }
        )
        assert any("docstring" in r.lower() for r in recs)

    def test_all_good(self):
        recs = _generate_documentation_recommendations(
            {
                "readme_status": {"root_readme": True, "completeness_score": 90},
                "code_documentation": {"coverage_percentage": 80},
            }
        )
        assert any("adequada" in r.lower() for r in recs)


class TestExtractFrontTechnologies:
    def test_empty(self):
        assert _extract_front_technologies({}) == []

    def test_nodejs_react(self):
        pkg = json.dumps({"dependencies": {"react": "^18"}})
        techs = _extract_front_technologies({"package.json": pkg})
        assert "Node.js" in techs
        assert "React" in techs

    def test_vue(self):
        pkg = json.dumps({"dependencies": {"vue": "^3"}})
        techs = _extract_front_technologies({"package.json": pkg})
        assert "Vue.js" in techs

    def test_angular(self):
        pkg = json.dumps({"dependencies": {"@angular/core": "^17"}})
        techs = _extract_front_technologies({"package.json": pkg})
        assert "Angular" in techs

    def test_python(self):
        techs = _extract_front_technologies({"requirements.txt": "flask"})
        assert "Python" in techs

    def test_pyproject(self):
        techs = _extract_front_technologies({"pyproject.toml": "[tool.poetry]"})
        assert "Python" in techs

    def test_invalid_json(self):
        techs = _extract_front_technologies({"package.json": "not json"})
        assert "Node.js" in techs  # still detects Node.js from presence of package.json


class TestFindFrontSimilarities:
    def test_empty(self):
        assert _find_front_similarities({}) == []

    def test_shared_tech(self):
        techs = {
            "frontend": ["React", "TypeScript"],
            "backend": ["TypeScript", "Node.js"],
        }
        sims = _find_front_similarities(techs)
        assert len(sims) == 1
        assert "TypeScript" in sims[0]["shared_technologies"]

    def test_no_overlap(self):
        techs = {"frontend": ["React"], "backend": ["Python"]}
        sims = _find_front_similarities(techs)
        assert sims == []


class TestFindFrontDifferences:
    def test_empty(self):
        assert _find_front_differences({}) == []

    def test_different_techs(self):
        techs = {
            "frontend": ["React", "TypeScript"],
            "backend": ["Python", "TypeScript"],
        }
        diffs = _find_front_differences(techs)
        assert len(diffs) == 1
        assert "React" in diffs[0]["frontend_only"]
        assert "Python" in diffs[0]["backend_only"]


class TestFindSharedDependencies:
    def test_empty(self):
        result = _find_shared_dependencies({}, [])
        assert result == []

    def test_with_package_json(self):
        analysis = {"key_files": {"frontend": {"package.json": "{}"}}}
        result = _find_shared_dependencies(analysis, ["frontend"])
        assert len(result) == 1
        assert result[0]["has_dependencies"] is True


class TestCheckDependencyVulnerabilities:
    @patch("aura_cli.core.tools.project_insights.read_file")
    def test_no_package_json(self, mock_read, tmp_path):
        vulns = _check_dependency_vulnerabilities(tmp_path)
        assert vulns == []

    @patch("aura_cli.core.tools.project_insights.read_file")
    def test_vulnerable_dep(self, mock_read, tmp_path):
        (tmp_path / "package.json").write_text("{}")
        mock_read.return_value = json.dumps(
            {
                "dependencies": {"lodash": "4.17.10"},
                "devDependencies": {},
            }
        )
        vulns = _check_dependency_vulnerabilities(tmp_path)
        assert any("lodash" in v["package"] for v in vulns)

    @patch("aura_cli.core.tools.project_insights.read_file")
    def test_safe_deps(self, mock_read, tmp_path):
        (tmp_path / "package.json").write_text("{}")
        mock_read.return_value = json.dumps(
            {
                "dependencies": {"axios": "^1.0.0"},
                "devDependencies": {},
            }
        )
        vulns = _check_dependency_vulnerabilities(tmp_path)
        assert vulns == []
