"""Tests for display module.

Tests for formatted display components for rich operation visualization.
"""

from unittest.mock import MagicMock, patch


class TestExpandablePreview:
    """Tests for ExpandablePreview class."""

    def test_expandable_preview_creation(self):
        """Test ExpandablePreview can be created."""
        from aura_cli.cli.ui.display import ExpandablePreview

        preview = ExpandablePreview("Test content", max_preview_length=100)

        assert preview is not None
        assert preview.content == "Test content"
        assert preview.max_preview_length == 100
        assert preview.is_expanded is False

    def test_expandable_preview_toggle(self):
        """Test ExpandablePreview toggle functionality."""
        from aura_cli.cli.ui.display import ExpandablePreview

        preview = ExpandablePreview("Test content")

        assert preview.is_expanded is False
        preview.toggle()
        assert preview.is_expanded is True
        preview.toggle()
        assert preview.is_expanded is False

    def test_expandable_preview_render_short_content(self):
        """Test rendering short content (no truncation needed)."""
        from rich.panel import Panel

        from aura_cli.cli.ui.display import ExpandablePreview

        preview = ExpandablePreview("Short content", max_preview_length=100)

        result = preview.render("Test Title")

        assert isinstance(result, Panel)

    def test_expandable_preview_render_long_content(self):
        """Test rendering long content (truncation applied)."""
        from rich.panel import Panel

        from aura_cli.cli.ui.display import ExpandablePreview

        long_content = "x" * 1000
        preview = ExpandablePreview(long_content, max_preview_length=100)

        result = preview.render("Test Title")

        assert isinstance(result, Panel)

    def test_expandable_preview_render_expanded(self):
        """Test rendering expanded content."""
        from rich.panel import Panel

        from aura_cli.cli.ui.display import ExpandablePreview

        long_content = "x" * 1000
        preview = ExpandablePreview(long_content, max_preview_length=100)
        preview.toggle()  # Expand

        result = preview.render("Test Title")

        assert isinstance(result, Panel)


class TestDisplayToolArgs:
    """Tests for display_tool_args function."""

    def test_display_tool_args_empty_args(self):
        """Test display_tool_args with empty args."""
        from aura_cli.cli.ui.display import display_tool_args

        with patch("aura_cli.cli.ui.display.console") as mock_console:
            display_tool_args("test_tool", {})

            # Should not print anything for empty args
            assert mock_console.print.call_count == 0

    def test_display_tool_args_not_showing(self):
        """Test display_tool_args when is_showing is False."""
        from aura_cli.cli.ui.display import display_tool_args

        with patch("aura_cli.cli.ui.display.console") as mock_console:
            display_tool_args("test_tool", {"key": "value"}, is_showing=False)

            # Should not print anything
            assert mock_console.print.call_count == 0

    def test_display_tool_args_simple_args(self):
        """Test display_tool_args with simple arguments."""
        from aura_cli.cli.ui.display import display_tool_args

        with patch("aura_cli.cli.ui.display.console") as mock_console:
            display_tool_args("test_tool", {"key": "value"}, is_showing=True)

            # Should print arguments
            assert mock_console.print.call_count >= 2

    def test_display_tool_args_long_value(self):
        """Test display_tool_args with long value."""
        from aura_cli.cli.ui.display import display_tool_args

        with patch("aura_cli.cli.ui.display.console") as mock_console:
            long_value = "x" * 200
            display_tool_args("test_tool", {"key": long_value}, is_showing=True)

            # Should print with truncation
            assert mock_console.print.called

    def test_display_tool_args_dict_value(self):
        """Test display_tool_args with dict value."""
        from aura_cli.cli.ui.display import display_tool_args

        with patch("aura_cli.cli.ui.display.console") as mock_console:
            display_tool_args(
                "test_tool", {"key": {"nested": "value"}}, is_showing=True
            )

            assert mock_console.print.called

    def test_display_tool_args_not_expandable(self):
        """Test display_tool_args with expandable=False."""
        from aura_cli.cli.ui.display import display_tool_args

        with patch("aura_cli.cli.ui.display.console") as mock_console:
            display_tool_args(
                "test_tool", {"key": "value"}, is_showing=True, expandable=False
            )

            assert mock_console.print.called


class TestDisplayFileEdit:
    """Tests for display_file_edit function."""

    def test_display_file_edit_no_preview(self):
        """Test display_file_edit with show_preview=False."""
        from aura_cli.cli.ui.display import display_file_edit

        with patch("aura_cli.cli.ui.display.console") as mock_console:
            display_file_edit(
                "test.py", "old content", "new content", show_preview=False
            )

            # Should not print anything
            assert mock_console.print.call_count == 0

    def test_display_file_edit_with_preview(self):
        """Test display_file_edit with preview."""
        from aura_cli.cli.ui.display import display_file_edit

        with patch("aura_cli.cli.ui.display.console") as mock_console:
            with patch("aura_cli.cli.ui.display.FileDiff") as mock_diff:
                mock_diff_instance = MagicMock()
                mock_diff_instance.render.return_value = "diff panel"
                mock_diff.return_value = mock_diff_instance

                display_file_edit(
                    "test.py", "old content", "new content", show_preview=True
                )

                mock_diff_instance.render.assert_called_once()
                assert mock_console.print.called

    def test_display_file_edit_with_max_lines(self):
        """Test display_file_edit with custom max_preview_lines."""
        from aura_cli.cli.ui.display import display_file_edit

        with patch("aura_cli.cli.ui.display.console"):
            with patch("aura_cli.cli.ui.display.FileDiff") as mock_diff:
                mock_diff_instance = MagicMock()
                mock_diff_instance.render.return_value = "diff"
                mock_diff.return_value = mock_diff_instance

                display_file_edit("test.py", "old", "new", max_preview_lines=100)

                mock_diff_instance.render.assert_called_with(
                    file_path="test.py",
                    old_content="old",
                    new_content="new",
                    max_preview_lines=100,
                    show_stats=True,
                )


class TestDisplayShellCommand:
    """Tests for display_shell_command function."""

    def test_display_shell_command_running(self):
        """Test display_shell_command with running status."""
        from aura_cli.cli.ui.display import display_shell_command

        with patch(
            "aura_cli.cli.ui.terminal_command.display_run_terminal_command"
        ) as mock_display:
            display_shell_command("ls -la")

            mock_display.assert_called_once()
            call_kwargs = mock_display.call_args[1]
            assert call_kwargs["status"] == "running"

    def test_display_shell_command_completed(self):
        """Test display_shell_command with completed status."""
        from aura_cli.cli.ui.display import display_shell_command

        with patch(
            "aura_cli.cli.ui.terminal_command.display_run_terminal_command"
        ) as mock_display:
            display_shell_command("ls -la", execution_time=1.5, exit_code=0)

            call_kwargs = mock_display.call_args[1]
            assert call_kwargs["status"] == "completed"
            assert call_kwargs["execution_time"] == 1.5

    def test_display_shell_command_failed(self):
        """Test display_shell_command with failed status."""
        from aura_cli.cli.ui.display import display_shell_command

        with patch(
            "aura_cli.cli.ui.terminal_command.display_run_terminal_command"
        ) as mock_display:
            display_shell_command("invalid_command", exit_code=1)

            call_kwargs = mock_display.call_args[1]
            assert call_kwargs["status"] == "failed"

    def test_display_shell_command_with_output(self):
        """Test display_shell_command with output."""
        from aura_cli.cli.ui.display import display_shell_command

        with patch(
            "aura_cli.cli.ui.terminal_command.display_run_terminal_command"
        ) as mock_display:
            display_shell_command("ls", output="file1\nfile2", show_output=True)

            call_kwargs = mock_display.call_args[1]
            assert call_kwargs["output"] == "file1\nfile2"

    def test_display_shell_command_hide_output(self):
        """Test display_shell_command with show_output=False."""
        from aura_cli.cli.ui.display import display_shell_command

        with patch(
            "aura_cli.cli.ui.terminal_command.display_run_terminal_command"
        ) as mock_display:
            display_shell_command("ls", output="file1\nfile2", show_output=False)

            call_kwargs = mock_display.call_args[1]
            assert call_kwargs["output"] is None


class TestFormatCodePreview:
    """Tests for format_code_preview function."""

    def test_format_code_preview_short_code(self):
        """Test format_code_preview with short code."""
        from rich.panel import Panel

        from aura_cli.cli.ui.display import format_code_preview

        code = "def hello():\n    return 'world'"

        result = format_code_preview(code, language="python", max_lines=20)

        assert isinstance(result, Panel)

    def test_format_code_preview_long_code(self):
        """Test format_code_preview with long code."""
        from rich.panel import Panel

        from aura_cli.cli.ui.display import format_code_preview

        code = "\n".join([f"line {i}" for i in range(100)])

        result = format_code_preview(code, language="python", max_lines=20)

        assert isinstance(result, Panel)

    def test_format_code_preview_not_expandable(self):
        """Test format_code_preview with expandable=False."""
        from rich.panel import Panel

        from aura_cli.cli.ui.display import format_code_preview

        code = "\n".join([f"line {i}" for i in range(100)])

        result = format_code_preview(code, language="python", expandable=False)

        assert isinstance(result, Panel)

    def test_format_code_preview_with_highlight_lines(self):
        """Test format_code_preview with highlight_lines."""
        from rich.panel import Panel

        from aura_cli.cli.ui.display import format_code_preview

        code = "line1\nline2\nline3"

        result = format_code_preview(code, language="python", highlight_lines=[2])

        assert isinstance(result, Panel)


class TestSearchInContent:
    """Tests for search_in_content function."""

    def test_search_in_content_found(self):
        """Test search_in_content when match found."""
        from aura_cli.cli.ui.display import search_in_content

        content = "line1\nline2 target\nline3"

        matches = search_in_content(content, "target")

        assert len(matches) == 1
        assert matches[0]["line_number"] == 2
        assert "target" in matches[0]["line"]

    def test_search_in_content_not_found(self):
        """Test search_in_content when no match."""
        from aura_cli.cli.ui.display import search_in_content

        content = "line1\nline2\nline3"

        matches = search_in_content(content, "notfound")

        assert len(matches) == 0

    def test_search_in_content_multiple_matches(self):
        """Test search_in_content with multiple matches."""
        from aura_cli.cli.ui.display import search_in_content

        content = "target line1\nline2\ntarget line3"

        matches = search_in_content(content, "target")

        assert len(matches) == 2

    def test_search_in_content_case_insensitive(self):
        """Test search_in_content is case insensitive."""
        from aura_cli.cli.ui.display import search_in_content

        content = "TARGET line"

        matches = search_in_content(content, "target")

        assert len(matches) == 1

    def test_search_in_content_with_context(self):
        """Test search_in_content includes context."""
        from aura_cli.cli.ui.display import search_in_content

        content = "ctx1\nctx2\ntarget\nctx3\nctx4"

        matches = search_in_content(content, "target", context_lines=2)

        assert len(matches) == 1
        assert "ctx2" in matches[0]["context"]
        assert "ctx3" in matches[0]["context"]


class TestDisplayChatMessage:
    """Tests for display_chat_message function."""

    def test_display_chat_message_user(self):
        """Test display_chat_message for user role."""
        from aura_cli.cli.ui.display import display_chat_message

        with patch("aura_cli.cli.ui.display.console") as mock_console:
            display_chat_message("user", "Hello")

            mock_console.print.assert_called_once()
            call_args = mock_console.print.call_args[0][0]
            assert "Você" in call_args or "user" in call_args.lower()

    def test_display_chat_message_assistant(self):
        """Test display_chat_message for assistant role."""
        from aura_cli.cli.ui.display import display_chat_message

        with patch("aura_cli.cli.ui.display.console") as mock_console:
            display_chat_message("assistant", "Hi there")

            mock_console.print.assert_called_once()
            call_args = mock_console.print.call_args[0][0]
            assert "Aura" in call_args

    def test_display_chat_message_with_timestamp(self):
        """Test display_chat_message with timestamp."""
        from datetime import datetime

        from aura_cli.cli.ui.display import display_chat_message

        with patch("aura_cli.cli.ui.display.console") as mock_console:
            timestamp = datetime(2024, 1, 1, 12, 30, 45)
            display_chat_message(
                "user", "Hello", timestamp=timestamp, show_timestamp=True
            )

            mock_console.print.assert_called_once()
            call_args = mock_console.print.call_args[0][0]
            assert "12:30:45" in call_args
