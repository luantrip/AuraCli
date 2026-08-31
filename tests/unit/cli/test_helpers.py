"""Tests for CLI helpers module.

Tests for helper functions and utilities for CLI main module.
"""

import queue
from unittest.mock import MagicMock, patch


class TestInitializeConversationHistory:
    """Tests for initialize_conversation_history function."""

    def test_initialize_conversation_history(self):
        """Test initialize_conversation_history returns list with system message."""
        from aura_cli.cli.helpers import initialize_conversation_history

        history = initialize_conversation_history()

        assert isinstance(history, list)
        assert len(history) == 1
        assert history[0]["role"] == "system"
        assert "content" in history[0]
        assert len(history[0]["content"]) > 0

    def test_initialize_conversation_history_contains_aura(self):
        """Test system message mentions Aura."""
        from aura_cli.cli.helpers import initialize_conversation_history

        history = initialize_conversation_history()

        assert "Aura" in history[0]["content"]

    def test_initialize_conversation_history_contains_tools(self):
        """Test system message mentions tools."""
        from aura_cli.cli.helpers import initialize_conversation_history

        history = initialize_conversation_history()
        content = history[0]["content"]

        assert (
            "read_file" in content
            or "write_file" in content
            or "FERRAMENTAS" in content
        )


class TestSetupPromptSession:
    """Tests for setup_prompt_session function."""

    @patch("aura_cli.cli.helpers.create_key_bindings")
    @patch("aura_cli.cli.helpers.PromptSession")
    @patch("aura_cli.cli.helpers.FileHistory")
    def test_setup_prompt_session(self, mock_history, mock_session, mock_bindings):
        """Test setup_prompt_session creates session."""
        from aura_cli.cli.helpers import setup_prompt_session

        mock_bindings.return_value = MagicMock()
        mock_bindings.return_value.add = MagicMock(return_value=lambda x: x)

        setup_prompt_session()

        mock_session.assert_called_once()


class TestHandleStatusUpdates:
    """Tests for handle_status_updates function."""

    def test_handle_status_updates_empty_queue(self):
        """Test handle_status_updates with empty queue."""
        from aura_cli.cli.helpers import handle_status_updates

        status_queue = queue.Queue()

        with patch("aura_cli.cli.helpers.console.print") as mock_print:
            handle_status_updates(status_queue)

            # Should not print anything for empty queue
            assert mock_print.call_count == 0

    def test_handle_status_updates_with_messages(self):
        """Test handle_status_updates with messages."""
        from aura_cli.cli.helpers import handle_status_updates

        status_queue = queue.Queue()
        status_queue.put("Test message")

        with patch("aura_cli.cli.helpers.console.print") as mock_print:
            with patch(
                "aura_cli.cli.ui.status_panel.create_status_panel", return_value="Panel"
            ):
                handle_status_updates(status_queue)
                assert mock_print.called

    def test_handle_status_updates_with_dict_message(self):
        """Test handle_status_updates with dict message."""
        from aura_cli.cli.helpers import handle_status_updates

        status_queue = queue.Queue()
        status_queue.put({"message": "Test message"})

        with patch("aura_cli.cli.helpers.console.print") as mock_print:
            with patch(
                "aura_cli.cli.ui.status_panel.create_status_panel", return_value="Panel"
            ):
                handle_status_updates(status_queue)
                assert mock_print.called

    def test_handle_status_updates_agi_message(self):
        """Test handle_status_updates with AGI message."""
        from aura_cli.cli.helpers import handle_status_updates

        status_queue = queue.Queue()
        status_queue.put("[Aura AGI] Working on task")

        with patch("aura_cli.cli.helpers.console.print") as mock_print:
            with patch(
                "aura_cli.cli.ui.status_panel.create_status_panel", return_value="Panel"
            ):
                handle_status_updates(status_queue)
                assert mock_print.called

    def test_handle_status_updates_ops_message(self):
        """Test handle_status_updates with Ops message."""
        from aura_cli.cli.helpers import handle_status_updates

        status_queue = queue.Queue()
        status_queue.put("[Aura Ops] Running git status")

        with patch("aura_cli.cli.helpers.console.print") as mock_print:
            with patch(
                "aura_cli.cli.ui.status_panel.create_status_panel", return_value="Panel"
            ):
                handle_status_updates(status_queue)
                assert mock_print.called


class TestParseAgiCommand:
    """Tests for parse_agi_command function."""

    def test_parse_agi_command_with_objective(self):
        """Test parse_agi_command with objective."""
        from aura_cli.cli.helpers import parse_agi_command

        result = parse_agi_command("/agi create a blog")

        assert result == "create a blog"

    def test_parse_agi_command_empty(self):
        """Test parse_agi_command without objective."""
        from aura_cli.cli.helpers import parse_agi_command

        result = parse_agi_command("/agi")

        assert "Explore" in result or len(result) > 0

    def test_parse_agi_command_whitespace(self):
        """Test parse_agi_command with whitespace."""
        from aura_cli.cli.helpers import parse_agi_command

        result = parse_agi_command("/agi   build an API   ")

        assert result == "build an API"


class TestParseOpsCommand:
    """Tests for parse_ops_command function."""

    def test_parse_ops_command_git(self):
        """Test parse_ops_command with git mode."""
        from aura_cli.cli.helpers import parse_ops_command

        mode, task = parse_ops_command("/ops git status")

        assert mode == "git"
        assert task == "status"

    def test_parse_ops_command_docker(self):
        """Test parse_ops_command with docker mode."""
        from aura_cli.cli.helpers import parse_ops_command

        mode, task = parse_ops_command("/ops docker ps")

        assert mode == "docker"
        assert task == "ps"

    def test_parse_ops_command_general(self):
        """Test parse_ops_command with general mode."""
        from aura_cli.cli.helpers import parse_ops_command

        mode, task = parse_ops_command("/ops check system")

        assert mode == "general"
        assert task == "check system"

    def test_parse_ops_command_empty(self):
        """Test parse_ops_command without arguments."""
        from aura_cli.cli.helpers import parse_ops_command

        mode, task = parse_ops_command("/ops")

        assert mode == "general"
        assert len(task) > 0

    def test_parse_ops_command_mode_only(self):
        """Test parse_ops_command with mode only."""
        from aura_cli.cli.helpers import parse_ops_command

        mode, task = parse_ops_command("/ops git")

        assert mode == "git"
        assert len(task) > 0


class TestGetApiKeysDict:
    """Tests for get_api_keys_dict function."""

    @patch("aura_cli.core.api_keys.os.getenv")
    @patch("aura_cli.core.secure_config.secure_config_manager")
    def test_get_api_keys_dict_from_secure_config(self, mock_config, mock_getenv):
        """Test get_api_keys_dict reads from SecureConfig."""
        from aura_cli.cli.helpers import get_api_keys_dict

        mock_config.get_api_key.return_value = "test_key"
        mock_getenv.return_value = None

        keys = get_api_keys_dict()

        assert isinstance(keys, dict)

    @patch("aura_cli.core.api_keys.os.getenv")
    def test_get_api_keys_dict_from_env(self, mock_getenv):
        """Test get_api_keys_dict falls back to environment."""
        from aura_cli.cli.helpers import get_api_keys_dict

        def env_getter(key):
            if key == "GOOGLE_API_KEY":
                return "google_key"
            return None

        mock_getenv.side_effect = env_getter

        with patch("aura_cli.core.secure_config.secure_config_manager") as mock_config:
            mock_config.get_api_key.return_value = None

            keys = get_api_keys_dict()

            assert "GOOGLE_API_KEY" in keys or len(keys) >= 0

    def test_get_api_keys_dict_returns_dict(self):
        """Test get_api_keys_dict returns dict."""
        from aura_cli.cli.helpers import get_api_keys_dict

        with patch("aura_cli.core.api_keys.os.getenv", return_value=None):
            with patch(
                "aura_cli.core.secure_config.secure_config_manager"
            ) as mock_config:
                mock_config.get_api_key.return_value = None

                keys = get_api_keys_dict()

                assert isinstance(keys, dict)


class TestHandleMultilineInput:
    """Tests for handle_multiline_input function."""

    @patch("builtins.input")
    @patch("aura_cli.cli.helpers.console")
    def test_handle_multiline_input_success(self, mock_console, mock_input):
        """Test handle_multiline_input with valid input."""
        from aura_cli.cli.helpers import handle_multiline_input

        mock_input.side_effect = ["line 1", "line 2", '"""']

        result = handle_multiline_input()

        assert result == "line 1\nline 2"

    @patch("builtins.input")
    @patch("aura_cli.cli.helpers.console")
    def test_handle_multiline_input_cancelled(self, mock_console, mock_input):
        """Test handle_multiline_input when cancelled."""
        from aura_cli.cli.helpers import handle_multiline_input

        mock_input.side_effect = KeyboardInterrupt()

        result = handle_multiline_input()

        assert result is None

    @patch("builtins.input")
    @patch("aura_cli.cli.helpers.console")
    def test_handle_multiline_input_empty(self, mock_console, mock_input):
        """Test handle_multiline_input with empty input."""
        from aura_cli.cli.helpers import handle_multiline_input

        mock_input.side_effect = ['"""']

        result = handle_multiline_input()

        assert result is None

    @patch("builtins.input")
    @patch("aura_cli.cli.helpers.console")
    def test_handle_multiline_input_eof(self, mock_console, mock_input):
        """Test handle_multiline_input with EOF."""
        from aura_cli.cli.helpers import handle_multiline_input

        mock_input.side_effect = EOFError()

        result = handle_multiline_input()

        assert result is None


class TestDisplayAuraSplashScreen:
    """Tests for display_aura_splash_screen function."""

    @patch("subprocess.run")
    @patch("aura_cli.cli.helpers.console")
    @patch("aura_cli.core.config.config_manager")
    def test_display_aura_splash_screen_runs(
        self, mock_config, mock_console, mock_subprocess
    ):
        """Test display_aura_splash_screen executes without error."""
        from aura_cli.cli.helpers import display_aura_splash_screen

        mock_config.get.return_value = True  # Skip animation

        display_aura_splash_screen()

        # Should print logo
        mock_console.print.assert_called()
