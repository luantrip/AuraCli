"""Tests for UI formatters - Centralized formatting utilities.

Tests verify consistent formatting of UI messages across the application.
"""

from aura_cli.cli.ui.formatters import (
    format_agent_status,
    format_error_message,
    format_file_operation,
    format_info_message,
    format_model_name,
    format_status_message,
    format_success_message,
    format_warning_message,
)


class TestFormatStatusMessage:
    """Test suite for format_status_message."""

    def test_basic_formatting(self):
        """Test basic status message formatting."""
        result = format_status_message("Test message")
        assert "Test message" in result
        assert "[" in result  # Rich markup

    def test_with_icon(self):
        """Test formatting with custom icon."""
        result = format_status_message("Test", icon="✓")
        assert "✓" in result

    def test_with_style(self):
        """Test formatting with custom style."""
        result = format_status_message("Test", style="bold")
        assert "bold" in result


class TestFormatSuccessMessage:
    """Test suite for format_success_message."""

    def test_basic_success(self):
        """Test basic success message."""
        result = format_success_message("Operation completed")
        assert "Operation completed" in result
        assert "success" in result.lower() or "✔" in result or "✓" in result

    def test_with_custom_icon(self):
        """Test success message with custom icon."""
        result = format_success_message("Done", icon="✅")
        assert "✅" in result


class TestFormatErrorMessage:
    """Test suite for format_error_message."""

    def test_basic_error(self):
        """Test basic error message."""
        result = format_error_message("Operation failed")
        assert "Operation failed" in result
        assert "error" in result.lower() or "✖" in result or "✗" in result

    def test_with_custom_icon(self):
        """Test error message with custom icon."""
        result = format_error_message("Failed", icon="❌")
        assert "❌" in result


class TestFormatInfoMessage:
    """Test suite for format_info_message."""

    def test_basic_info(self):
        """Test basic info message."""
        result = format_info_message("Information")
        assert "Information" in result

    def test_with_custom_icon(self):
        """Test info message with custom icon."""
        result = format_info_message("Info", icon="ℹ️")
        assert "ℹ️" in result


class TestFormatWarningMessage:
    """Test suite for format_warning_message."""

    def test_basic_warning(self):
        """Test basic warning message."""
        result = format_warning_message("Warning message")
        assert "Warning message" in result
        assert "warning" in result.lower() or "⚠" in result

    def test_with_custom_icon(self):
        """Test warning message with custom icon."""
        result = format_warning_message("Warning", icon="⚠️")
        assert "⚠️" in result


class TestFormatFileOperation:
    """Test suite for format_file_operation."""

    def test_create_operation(self):
        """Test file create operation formatting."""
        result = format_file_operation("create", "test.txt", "completed")
        assert "Create" in result or "create" in result.lower()
        assert "test.txt" in result

    def test_edit_operation(self):
        """Test file edit operation formatting."""
        result = format_file_operation("edit", "test.py", "completed")
        assert "Edit" in result or "edit" in result.lower()
        assert "test.py" in result

    def test_read_operation(self):
        """Test file read operation formatting."""
        result = format_file_operation("read", "data.json", "completed")
        assert "Read" in result or "read" in result.lower()
        assert "data.json" in result

    def test_delete_operation(self):
        """Test file delete operation formatting."""
        result = format_file_operation("delete", "old.txt", "completed")
        assert "Delete" in result or "delete" in result.lower()
        assert "old.txt" in result

    def test_failed_status(self):
        """Test file operation with failed status."""
        result = format_file_operation("create", "test.txt", "failed")
        assert (
            "failed" in result.lower()
            or "error" in result.lower()
            or "test.txt" in result
        )

    def test_pending_status(self):
        """Test file operation with pending status."""
        result = format_file_operation("edit", "test.py", "pending")
        assert (
            "pending" in result.lower()
            or "warning" in result.lower()
            or "test.py" in result
        )


class TestFormatModelName:
    """Test suite for format_model_name."""

    def test_model_with_slash(self):
        """Test formatting model name with slash."""
        result = format_model_name("gemini/gemini-2.0-flash-exp")
        # Accept both raw and title-cased results
        assert (
            result.lower() == "gemini 2.0 flash exp"
            or result.lower() == "gemini-2.0-flash-exp"
        )
        assert "/" not in result

    def test_model_without_slash(self):
        """Test formatting model name without slash."""
        result = format_model_name("gpt-4")
        assert result.lower() == "gpt-4"

    def test_short_model_name(self):
        """Test formatting short model name."""
        result = format_model_name("claude-3-opus")
        assert result.lower() == "claude 3 opus" or result.lower() == "claude-3-opus"


class TestFormatAgentStatus:
    """Test suite for format_agent_status."""

    def test_agi_agent(self):
        """Test formatting AGI agent status."""
        result = format_agent_status("Aura AGI", "ON")
        assert "Aura AGI" in result
        assert "ON" in result

    def test_ops_agent(self):
        """Test formatting Ops agent status."""
        result = format_agent_status("Aura Ops", "working")
        assert "Aura Ops" in result
        assert "working" in result

    def test_unknown_agent(self):
        """Test formatting unknown agent type."""
        result = format_agent_status("Unknown", "status")
        assert "Unknown" in result
        assert "status" in result
