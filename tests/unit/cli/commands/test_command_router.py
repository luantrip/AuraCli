"""Tests for command router - Command routing and classification.

Tests verify proper routing of commands to appropriate handlers.
"""

from unittest.mock import Mock, patch

from aura_cli.cli.command_router import route_command


class TestRouteCommand:
    """Test suite for route_command function."""

    @patch("aura_cli.cli.command_router.process_slash_command")
    @patch("aura_cli.cli.command_router.should_execute_directly")
    def test_route_slash_command(self, mock_should_execute, mock_process_slash):
        """Test routing slash command to processor."""
        mock_should_execute.return_value = False
        mock_process_slash.return_value = (True, "Message", None, None, None)

        mock_ui = Mock()
        mock_ui.status_queue = Mock()
        mock_stats = Mock()
        mock_stats.set_notification = Mock()
        mock_console = Mock()
        mock_console.print = Mock()

        result = route_command(
            command="/help",
            agi_thread=None,
            ops_thread=None,
            current_model="auto",
            stats=mock_stats,
            ui=mock_ui,
            console=mock_console,
        )

        assert result[0] is True  # should_continue
        mock_process_slash.assert_called_once()

    @patch("aura_cli.cli.command_router.process_slash_command")
    @patch("aura_cli.cli.command_router.should_execute_directly")
    def test_route_slash_command_with_notification(
        self, mock_should_execute, mock_process_slash
    ):
        """Test slash command that triggers notification."""
        mock_should_execute.return_value = False
        mock_process_slash.return_value = (True, "Aura AGI: ON", None, None, None)

        mock_ui = Mock()
        mock_ui.status_queue = Mock()
        mock_stats = Mock()
        mock_stats.set_notification = Mock()
        mock_console = Mock()

        route_command(
            command="/agi test",
            agi_thread=None,
            ops_thread=None,
            current_model="auto",
            stats=mock_stats,
            ui=mock_ui,
            console=mock_console,
        )

        mock_stats.set_notification.assert_called_once()

    @patch("aura_cli.cli.command_router.process_slash_command")
    @patch("aura_cli.cli.command_router.should_execute_directly")
    def test_route_slash_command_exit(self, mock_should_execute, mock_process_slash):
        """Test slash command that exits (should_continue=False)."""
        mock_should_execute.return_value = False
        mock_process_slash.return_value = (False, None, None, None, None)

        mock_ui = Mock()
        mock_ui.status_queue = Mock()
        mock_stats = Mock()
        mock_console = Mock()

        result = route_command(
            command="/exit",
            agi_thread=None,
            ops_thread=None,
            current_model="auto",
            stats=mock_stats,
            ui=mock_ui,
            console=mock_console,
        )

        assert result[0] is False  # should_continue

    @patch("aura_cli.cli.command_router.execute_shell_command")
    @patch("aura_cli.cli.command_router.extract_shell_command")
    @patch("aura_cli.cli.command_router.should_execute_directly")
    def test_route_shell_command(self, mock_should_execute, mock_extract, mock_execute):
        """Test routing shell command to executor."""
        mock_should_execute.return_value = True
        mock_extract.return_value = "ls -la"
        mock_execute.return_value = (True, "output")

        mock_ui = Mock()
        mock_ui.display_shell_output = Mock()
        mock_console = Mock()
        mock_console.print = Mock()
        mock_stats = Mock()

        result = route_command(
            command="ls -la",
            agi_thread=None,
            ops_thread=None,
            current_model="auto",
            stats=mock_stats,
            ui=mock_ui,
            console=mock_console,
        )

        assert result[0] is True
        assert result[1] is None
        mock_execute.assert_called_once()
        mock_ui.display_shell_output.assert_called_once()

    @patch("aura_cli.cli.command_router.process_slash_command")
    @patch("aura_cli.cli.command_router.should_execute_directly")
    def test_route_llm_query(self, mock_should_execute, mock_process_slash):
        """Test routing regular command to LLM query."""
        mock_should_execute.return_value = False
        mock_process_slash.return_value = None  # Not called for non-slash

        mock_ui = Mock()
        mock_stats = Mock()
        mock_console = Mock()

        result = route_command(
            command="What is Python?",
            agi_thread=None,
            ops_thread=None,
            current_model="auto",
            stats=mock_stats,
            ui=mock_ui,
            console=mock_console,
        )

        assert result[0] is True
        assert result[1] == "llm_query"
        mock_process_slash.assert_not_called()

    @patch("aura_cli.cli.command_router.process_slash_command")
    @patch("aura_cli.cli.command_router.should_execute_directly")
    def test_route_with_threads(self, mock_should_execute, mock_process_slash):
        """Test routing with existing threads."""
        mock_should_execute.return_value = False
        mock_process_slash.return_value = (True, None, None, None, None)

        mock_agi_thread = Mock()
        mock_ops_thread = Mock()
        mock_ui = Mock()
        mock_ui.status_queue = Mock()
        mock_stats = Mock()
        mock_console = Mock()

        result = route_command(
            command="/help",
            agi_thread=mock_agi_thread,
            ops_thread=mock_ops_thread,
            current_model="auto",
            stats=mock_stats,
            ui=mock_ui,
            console=mock_console,
        )

        assert result[0] is True
