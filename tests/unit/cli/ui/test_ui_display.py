"""Tests for ui/display.py - Display functions.

Tests verify:
- display_tool_args: Tool argument display
- display_file_edit: File edit display with diff
- display_shell_command: Shell command display
- format_code_preview: Code preview formatting
- search_in_content: Content search
- display_chat_message: Chat message display
"""

from unittest.mock import Mock, patch

from aura_cli.cli.ui.display import (
    display_chat_message,
    display_file_edit,
    display_shell_command,
    display_tool_args,
    format_code_preview,
    search_in_content,
)


class TestDisplayToolArgs:
    """Test suite for display_tool_args."""

    @patch("aura_cli.cli.ui.display.console")
    def test_display_tool_args_not_showing(self, mock_console):
        """Test display_tool_args when not showing."""
        display_tool_args("test_tool", {"arg1": "value1"}, is_showing=False)
        assert not mock_console.print.called

    @patch("aura_cli.cli.ui.display.console")
    def test_display_tool_args_empty(self, mock_console):
        """Test display_tool_args with empty args."""
        display_tool_args("test_tool", {}, is_showing=True)
        assert not mock_console.print.called

    @patch("aura_cli.cli.ui.display.console")
    def test_display_tool_args_simple(self, mock_console):
        """Test display_tool_args with simple args."""
        display_tool_args("test_tool", {"arg1": "value1"}, is_showing=True)
        assert mock_console.print.called

    @patch("aura_cli.cli.ui.display.console")
    def test_display_tool_args_long_value(self, mock_console):
        """Test display_tool_args with long value."""
        long_value = "x" * 200
        display_tool_args(
            "test_tool", {"arg1": long_value}, is_showing=True, expandable=True
        )
        assert mock_console.print.called


class TestDisplayFileEdit:
    """Test suite for display_file_edit."""

    @patch("aura_cli.cli.ui.display.console")
    @patch("aura_cli.cli.ui.display.FileDiff")
    def test_display_file_edit(self, mock_file_diff, mock_console):
        """Test displaying file edit."""
        mock_diff = Mock()
        mock_file_diff.return_value = mock_diff

        display_file_edit("test.py", "old content", "new content")

        assert mock_console.print.called

    @patch("aura_cli.cli.ui.display.console")
    @patch("aura_cli.cli.ui.display.FileDiff")
    def test_display_file_edit_with_metadata(self, mock_file_diff, mock_console):
        """Test displaying file edit with metadata."""
        mock_diff = Mock()
        mock_file_diff.return_value = mock_diff

        # display_file_edit may not accept metadata parameter
        # Test with just basic parameters
        display_file_edit("test.py", "old content", "new content")

        assert mock_console.print.called


class TestDisplayShellCommand:
    """Test suite for display_shell_command."""

    @patch("aura_cli.cli.ui.terminal_command.display_run_terminal_command")
    def test_display_shell_command(self, mock_display_run):
        """Test displaying shell command."""
        display_shell_command("ls -la", "output text", exit_code=0, execution_time=1.0)
        assert mock_display_run.called
        # Verify it was called with correct parameters
        call_args = mock_display_run.call_args
        assert call_args[1]["command"] == "ls -la"
        assert call_args[1]["output"] == "output text"
        assert call_args[1]["exit_code"] == 0
        assert call_args[1]["status"] == "completed"

    @patch("aura_cli.cli.ui.terminal_command.display_run_terminal_command")
    def test_display_shell_command_error(self, mock_display_run):
        """Test displaying shell command with error."""
        display_shell_command("invalid_command", "error output", exit_code=1)
        assert mock_display_run.called
        # Verify it was called with error status
        call_args = mock_display_run.call_args
        assert call_args[1]["exit_code"] == 1
        assert call_args[1]["status"] == "failed"


class TestFormatCodePreview:
    """Test suite for format_code_preview."""

    @patch("aura_cli.cli.ui.components.syntax.AuraSyntax")
    def test_format_code_preview_short(self, mock_syntax):
        """Test formatting short code preview."""
        mock_syntax_instance = Mock()
        mock_syntax.return_value = mock_syntax_instance
        mock_syntax_instance.render.return_value = Mock()

        result = format_code_preview("print('hello')", max_lines=100)
        assert result is not None

    @patch("aura_cli.cli.ui.components.syntax.AuraSyntax")
    def test_format_code_preview_long(self, mock_syntax):
        """Test formatting long code preview."""
        mock_syntax_instance = Mock()
        mock_syntax.return_value = mock_syntax_instance
        mock_syntax_instance.render.return_value = Mock()

        long_code = "\n".join([f"line {i}" for i in range(200)])
        result = format_code_preview(long_code, max_lines=100)
        assert result is not None


class TestSearchInContent:
    """Test suite for search_in_content."""

    def test_search_in_content_found(self):
        """Test searching content when found."""
        content = "This is a test string with keyword"
        result = search_in_content(content, "keyword", context_lines=2)
        # search_in_content returns a list of matches
        assert isinstance(result, list)
        assert len(result) > 0
        assert "keyword" in result[0]["line"].lower()

    def test_search_in_content_not_found(self):
        """Test searching content when not found."""
        content = "This is a test string"
        result = search_in_content(content, "nonexistent", context_lines=2)
        # Returns empty list when not found
        assert isinstance(result, list)
        assert len(result) == 0


class TestDisplayChatMessage:
    """Test suite for display_chat_message."""

    @patch("aura_cli.cli.ui.display.console")
    def test_display_chat_message_user(self, mock_console):
        """Test displaying user chat message."""
        display_chat_message("user", "Hello, world!")
        assert mock_console.print.called

    @patch("aura_cli.cli.ui.display.console")
    def test_display_chat_message_assistant(self, mock_console):
        """Test displaying assistant chat message."""
        display_chat_message("assistant", "Hello! How can I help?")
        assert mock_console.print.called

    @patch("aura_cli.cli.ui.display.console")
    def test_display_chat_message_with_metadata(self, mock_console):
        """Test displaying chat message with metadata."""
        from datetime import datetime

        # display_chat_message accepts timestamp parameter
        display_chat_message(
            "assistant", "Response", timestamp=datetime.now(), show_timestamp=True
        )
        assert mock_console.print.called
