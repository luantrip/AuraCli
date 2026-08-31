"""
Tests for command_processor.py and command handlers.
"""

from unittest.mock import Mock, patch

from aura_cli.cli.command_processor import process_slash_command
from aura_cli.cli.commands.agents import handle_tools
from aura_cli.cli.commands.basic import handle_clear, handle_help
from aura_cli.cli.commands.project import handle_todo


class TestHandleHelp:
    @patch("aura_cli.cli.commands.basic.get_console")
    def test_handle_help_displays_table(self, mock_get_console):
        """Test that handle_help displays help table."""
        mock_console = Mock()
        mock_get_console.return_value = mock_console

        handle_help()

        assert mock_console.print.called


class TestHandleTools:
    @patch("aura_cli.cli.commands.agents.Console")
    @patch("aura_cli.cli.commands.agents.OPS_TOOLS", {})
    @patch("aura_cli.cli.commands.agents.get_tools_dict")
    def test_handle_tools_no_exception(self, mock_get_tools, mock_console_class):
        """Test that handle_tools runs without error."""
        mock_get_tools.return_value = {"tool1": lambda: None}
        mock_console = Mock()
        mock_console_class.return_value = mock_console

        handle_tools()

        # Should print at least 3 panels/messages
        assert mock_console.print.call_count >= 3


class TestHandleTodo:
    @patch("aura_cli.cli.commands.project.Console")
    @patch("aura_cli.core.todo.todo_tracker.TodoTracker")
    @patch("aura_cli.cli.ui.todo_display.create_todo_panel")
    def test_handle_todo_displays_list(
        self, mock_create_panel, mock_tracker_class, mock_console_class
    ):
        """Test that handle_todo renders panel via create_todo_panel."""
        mock_tracker = Mock()
        mock_tracker_class.return_value = mock_tracker
        mock_panel = Mock()
        mock_create_panel.return_value = mock_panel

        mock_console = Mock()
        mock_console_class.return_value = mock_console

        handle_todo()

        mock_create_panel.assert_called_once_with(mock_tracker, max_tasks=20)
        # Should print the panel (plus surrounding blank lines)
        calls = [str(c) for c in mock_console.print.call_args_list]
        assert any(str(mock_panel) in c for c in calls)

    @patch("aura_cli.cli.commands.project.Console")
    @patch("aura_cli.core.todo.todo_tracker.TodoTracker")
    def test_handle_todo_handles_errors(self, mock_tracker_class, mock_console_class):
        """Test that handle_todo handles errors gracefully."""
        mock_tracker_class.side_effect = Exception("Tracker Error")

        mock_console = Mock()
        mock_console_class.return_value = mock_console

        handle_todo()

        # Should print error message
        mock_console.print.assert_called()
        args, _ = mock_console.print.call_args
        # Accept both English and Portuguese messages
        output = str(args[0])
        assert any(word in output for word in ["Failed", "Error", "Falha", "Erro"])


class TestHandleClear:
    @patch("sys.stdout")
    def test_handle_clear(self, mock_stdout):
        """Test handle_clear uses ANSI codes."""
        handle_clear()

        # Verify ANSI codes were written
        mock_stdout.write.assert_called_with("\033[2J\033[H")
        mock_stdout.flush.assert_called()


class TestProcessSlashCommand:
    """Test process_slash_command routing."""

    @patch("aura_cli.cli.command_processor.handle_help")
    def test_route_help(self, mock_help):
        """Test routing to help handler."""
        process_slash_command("/help", None, None, "model", Mock(), Mock(), Mock())
        mock_help.assert_called_once()

    @patch("aura_cli.cli.command_processor.handle_clear")
    def test_route_clear(self, mock_clear):
        """Test routing to clear handler."""
        process_slash_command("/clear", None, None, "model", Mock(), Mock(), Mock())
        mock_clear.assert_called_once()

    def test_route_exit(self):
        """Test routing to exit."""
        cont, _, _, _, _ = process_slash_command(
            "/exit", None, None, "model", Mock(), Mock(), Mock()
        )
        assert cont is False

    @patch("aura_cli.cli.command_processor.handle_tools")
    def test_route_tools(self, mock_tools):
        """Test routing to tools handler."""
        process_slash_command("/tools", None, None, "model", Mock(), Mock(), Mock())
        mock_tools.assert_called_once()
