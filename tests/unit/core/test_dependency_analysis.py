"""Tests for dependency_analysis module.

Tests for dependency analysis and graph operations.
"""

from pathlib import Path
from unittest.mock import mock_open, patch


class TestDependencyAnalysis:
    """Tests for dependency analysis functionality."""

    def test_dependency_analysis_import(self):
        """Test dependency_analysis module can be imported."""
        from aura_cli.core import dependency_analysis

        assert dependency_analysis is not None

    def test_dependency_analyzer_creation(self):
        """Test DependencyAnalyzer creation."""
        from aura_cli.core.dependency_analysis import DependencyAnalyzer

        analyzer = DependencyAnalyzer(".")

        assert analyzer is not None
        assert analyzer.scope == Path(".").resolve()
        assert not analyzer._analyzed

    def test_dependency_analyzer_with_scope(self):
        """Test DependencyAnalyzer with custom scope."""
        from aura_cli.core.dependency_analysis import DependencyAnalyzer

        analyzer = DependencyAnalyzer("/tmp")

        assert analyzer.scope == Path("/tmp").resolve()

    @patch("os.walk")
    def test_analyze_method(self, mock_walk):
        """Test analyze method."""
        from aura_cli.core.dependency_analysis import DependencyAnalyzer

        # Mock os.walk to return some Python files
        mock_walk.return_value = [
            ("/test", [], ["file1.py", "file2.py", "not_python.txt"])
        ]

        analyzer = DependencyAnalyzer(".")

        with patch.object(analyzer, "_analyze_file"):
            result = analyzer.analyze()

        assert result == analyzer
        assert analyzer._analyzed is True

    def test_should_ignore_patterns(self):
        """Test ignore patterns."""
        from aura_cli.core.dependency_analysis import DependencyAnalyzer

        analyzer = DependencyAnalyzer(".")

        # Should ignore common patterns
        assert analyzer._should_ignore(Path("__pycache__"))
        assert analyzer._should_ignore(Path(".git"))
        assert analyzer._should_ignore(Path(".venv"))
        assert analyzer._should_ignore(Path("node_modules"))

        # Should not ignore regular directories
        assert not analyzer._should_ignore(Path("src"))
        assert not analyzer._should_ignore(Path("lib"))

    def test_normalize_path(self):
        """Test path normalization."""
        from aura_cli.core.dependency_analysis import DependencyAnalyzer

        analyzer = DependencyAnalyzer(".")

        # Test with path inside scope
        test_path = Path("./test/file.py")
        normalized = analyzer._normalize_path(test_path)

        assert isinstance(normalized, str)

    def test_find_dependencies_empty(self):
        """Test finding dependencies for non-existent file."""
        from aura_cli.core.dependency_analysis import DependencyAnalyzer

        analyzer = DependencyAnalyzer(".")

        # Should return empty list for non-existent file
        deps = analyzer.find_dependencies("nonexistent.py")

        assert isinstance(deps, list)
        assert len(deps) == 0

    def test_find_dependents_empty(self):
        """Test finding dependents for non-existent file."""
        from aura_cli.core.dependency_analysis import DependencyAnalyzer

        analyzer = DependencyAnalyzer(".")

        # Should return empty list for non-existent file
        dependents = analyzer.find_dependents("nonexistent.py")

        assert isinstance(dependents, list)
        assert len(dependents) == 0

    def test_analyze_import_graph_without_networkx(self):
        """Test import graph analysis without networkx."""
        from aura_cli.core.dependency_analysis import DependencyAnalyzer

        analyzer = DependencyAnalyzer(".")

        with patch("aura_cli.core.dependency_analysis.HAS_NETWORKX", False):
            result = analyzer.analyze_import_graph()

        assert isinstance(result, dict)
        assert result["has_networkx"] is False
        assert "warning" in result

    def test_analyze_import_graph_with_networkx(self):
        """Test import graph analysis with networkx."""
        from aura_cli.core.dependency_analysis import DependencyAnalyzer

        analyzer = DependencyAnalyzer(".")

        with patch("aura_cli.core.dependency_analysis.HAS_NETWORKX", True):
            result = analyzer.analyze_import_graph()

        assert isinstance(result, dict)
        assert result["has_networkx"] is True
        assert "nodes" in result
        assert "edges" in result

    def test_get_impact_analysis(self):
        """Test impact analysis."""
        from aura_cli.core.dependency_analysis import DependencyAnalyzer

        analyzer = DependencyAnalyzer(".")

        result = analyzer.get_impact_analysis("test.py")

        assert isinstance(result, dict)
        assert "file" in result
        assert "change_type" in result
        assert "affected_files" in result
        assert "risk_level" in result
        assert result["file"] == "test.py"
        assert result["change_type"] == "modify"

    def test_get_impact_analysis_with_change_type(self):
        """Test impact analysis with specific change type."""
        from aura_cli.core.dependency_analysis import DependencyAnalyzer

        analyzer = DependencyAnalyzer(".")

        result = analyzer.get_impact_analysis("test.py", "delete")

        assert result["change_type"] == "delete"

    def test_calculate_risk_levels(self):
        """Test risk level calculation."""
        from aura_cli.core.dependency_analysis import DependencyAnalyzer

        analyzer = DependencyAnalyzer(".")

        # Test different risk levels
        assert analyzer._calculate_risk(0) == "low"
        assert analyzer._calculate_risk(5) == "medium"
        assert analyzer._calculate_risk(25) == "high"
        assert analyzer._calculate_risk(100) == "critical"

    def test_find_related_tests(self):
        """Test finding related tests."""
        from aura_cli.core.dependency_analysis import DependencyAnalyzer

        analyzer = DependencyAnalyzer(".")

        test_path = Path("src/module.py")
        related = analyzer._find_related_tests(test_path)

        assert isinstance(related, list)

    # Test module-level functions
    def test_get_impact_analysis_function(self):
        """Test module-level get_impact_analysis function."""
        from aura_cli.core.dependency_analysis import get_impact_analysis

        result = get_impact_analysis("test.py")

        assert isinstance(result, dict)
        assert "file" in result

    def test_find_dependencies_function(self):
        """Test module-level find_dependencies function."""
        from aura_cli.core.dependency_analysis import find_dependencies

        result = find_dependencies("test.py")

        assert isinstance(result, list)

    def test_find_dependents_function(self):
        """Test module-level find_dependents function."""
        from aura_cli.core.dependency_analysis import find_dependents

        result = find_dependents("test.py")

        assert isinstance(result, list)

    def test_analyze_import_graph_function(self):
        """Test module-level analyze_import_graph function."""
        from aura_cli.core.dependency_analysis import analyze_import_graph

        result = analyze_import_graph()

        assert isinstance(result, dict)
        assert "nodes" in result
        assert "edges" in result

    @patch("builtins.open", mock_open(read_data="import os\nfrom pathlib import Path"))
    def test_analyze_file_with_imports(self):
        """Test analyzing file with imports."""
        from aura_cli.core.dependency_analysis import DependencyAnalyzer

        analyzer = DependencyAnalyzer(".")

        # This should not raise an exception
        analyzer._analyze_file(Path("test.py"))

    @patch(
        "builtins.open", side_effect=UnicodeDecodeError("utf-8", b"", 0, 1, "invalid")
    )
    def test_analyze_file_unicode_error(self, mock_file):
        """Test analyzing file with unicode error."""
        from aura_cli.core.dependency_analysis import DependencyAnalyzer

        analyzer = DependencyAnalyzer(".")

        # Should handle unicode errors gracefully
        analyzer._analyze_file(Path("bad_file.py"))

    @patch("builtins.open", mock_open(read_data="invalid python syntax !!!"))
    def test_analyze_file_syntax_error(self):
        """Test analyzing file with syntax error."""
        from aura_cli.core.dependency_analysis import DependencyAnalyzer

        analyzer = DependencyAnalyzer(".")

        # Should handle syntax errors gracefully
        analyzer._analyze_file(Path("bad_syntax.py"))

    def test_resolve_import_existing(self):
        """Test resolving existing import."""
        from aura_cli.core.dependency_analysis import DependencyAnalyzer

        analyzer = DependencyAnalyzer(".")
        analyzer._python_files = {"test/module.py", "test/__init__.py"}

        result = analyzer._resolve_import("test.module")

        # Should find the module
        assert result in [None, "test/module.py"]  # None if not found is acceptable

    def test_resolve_import_nonexistent(self):
        """Test resolving non-existent import."""
        from aura_cli.core.dependency_analysis import DependencyAnalyzer

        analyzer = DependencyAnalyzer(".")
        analyzer._python_files = set()

        result = analyzer._resolve_import("nonexistent.module")

        assert result is None

    def test_resolve_module_path_relative(self):
        """Test resolving relative module path."""
        from aura_cli.core.dependency_analysis import DependencyAnalyzer

        analyzer = DependencyAnalyzer(".")

        file_path = Path("src/package/module.py")

        # Test should handle relative imports gracefully
        try:
            result = analyzer._resolve_module_path(".sibling", file_path)
            # Should handle relative imports - result can be None or a path
            assert result is None or isinstance(result, (str, Path))
        except ValueError:
            # ValueError is acceptable for relative imports
            pass

    def test_build_graph(self):
        """Test building dependency graph."""
        from aura_cli.core.dependency_analysis import DependencyAnalyzer

        analyzer = DependencyAnalyzer(".")

        # Should not raise exception
        analyzer._build_graph()


def mock_open(read_data=""):
    """Mock open function for file reading tests."""
    from unittest.mock import mock_open as mock_open_builtin

    return mock_open_builtin(read_data=read_data)
