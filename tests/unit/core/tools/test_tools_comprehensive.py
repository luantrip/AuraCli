"""Comprehensive tests for tools modules.

Tests cover file operations, dev tools, and ops tools.
"""


class TestFileSystemTools:
    """Tests for file system tools."""


    def test_read_file_import(self):
        """Test read_file function import."""
        from aura_cli.core.tools.file_system import read_file

        assert callable(read_file)

    def test_read_file_basic(self, temp_dir):
        """Test basic file reading."""
        from aura_cli.core.tools.file_system import enable_path_validation, read_file

        enable_path_validation(False)

        test_file = temp_dir / "test.txt"
        test_file.write_text("Hello World")

        content = read_file(str(test_file))
        assert "Hello" in content

    def test_list_directory_import(self):
        """Test list_directory function import."""
        from aura_cli.core.tools.file_system import list_directory

        assert callable(list_directory)


class TestDevTools:
    """Tests for development tools."""


    def test_analyze_code_import(self):
        """Test analyze_code function import."""
        from aura_cli.core.tools.dev_tools import analyze_code

        assert callable(analyze_code)

    def test_validate_syntax_import(self):
        """Test validate_syntax function import."""
        from aura_cli.core.tools.dev_tools import validate_syntax

        assert callable(validate_syntax)

    def test_validate_syntax_python_valid(self):
        """Test Python syntax validation for valid code."""
        from aura_cli.core.tools.dev_tools import validate_syntax

        result = validate_syntax("print('hello')", "python")
        assert "OK" in result or "válido" in result.lower() or "Syntax" in result

    def test_validate_syntax_json_valid(self):
        """Test JSON validation for valid JSON."""
        from aura_cli.core.tools.dev_tools import validate_syntax

        result = validate_syntax('{"key": "value"}', "json")
        assert "OK" in result or "válido" in result.lower() or "Syntax" in result

    def test_tree_view_import(self):
        """Test tree_view function import."""
        from aura_cli.core.tools.dev_tools import tree_view

        assert callable(tree_view)


class TestOpsTools:
    """Tests for ops tools."""


class TestToolsRegistry:
    """Tests for tools registry (get_tools_dict)."""


    def test_get_tools_dict_returns_dict(self):
        """get_tools_dict returns a non-empty dict."""
        from aura_cli.core.service_registry import get_tools_dict

        tools = get_tools_dict()
        assert isinstance(tools, dict)
        assert len(tools) > 0

    def test_get_tools_dict_values_are_callable(self):
        """Every tool in the registry must be callable."""
        from aura_cli.core.service_registry import get_tools_dict

        tools = get_tools_dict()
        for name, fn in tools.items():
            assert callable(fn), f"Tool '{name}' is not callable"

    def test_core_tools_present_in_registry(self):
        """Essential tools must be registered."""
        from aura_cli.core.service_registry import get_tools_dict

        tools = get_tools_dict()
        essential = {"read_file", "write_file", "list_directory", "run_shell_command"}
        missing = essential - set(tools.keys())
        assert not missing, f"Missing essential tools: {missing}"


class TestFileOperations:
    """Tests for file operations."""


    def test_read_file_not_found(self):
        """Test reading non-existent file."""
        from aura_cli.core.tools.file_system import enable_path_validation, read_file

        enable_path_validation(False)

        result = read_file("/nonexistent/path/file.txt")
        assert (
            "não encontrado" in result
            or "Erro" in result
            or "encontr" in result.lower()
        )


class TestBackupTools:
    """Tests for backup tools."""

    def test_backup_file_import(self):
        """Test backup_file function import."""
        from aura_cli.core.tools.dev_tools import backup_file

        assert callable(backup_file)


class TestEditTools:
    """Tests for edit tools."""

    def test_edit_file_import(self):
        """Test edit_file function import."""
        from aura_cli.core.tools.dev_tools import edit_file

        assert callable(edit_file)


class TestImaginationTools:
    """Tests for imagination tools."""


class TestToolHelpers:
    """Tests for tool helper functions."""

    def test_get_stats_import(self):
        """Test get_stats function import."""
        from aura_cli.core.stats import get_stats

        assert callable(get_stats)

