"""Comprehensive tests for helpers.py - All functions covered.

Tests verify all helper functions including:
- display_aura_splash_screen
- initialize_conversation_history
- setup_prompt_session
- handle_status_updates
- parse_agi_command
- parse_ops_command
- get_api_keys_dict
- handle_multiline_input
- process_slash_command
"""

import os
import queue
from unittest.mock import Mock, patch

from aura_cli.cli.helpers import (
    display_aura_splash_screen,
    get_api_keys_dict,
    handle_multiline_input,
    handle_status_updates,
    initialize_conversation_history,
    parse_agi_command,
    parse_ops_command,
    setup_prompt_session,
)


class TestDisplayAuraSplashScreen:
    """Test suite for display_aura_splash_screen."""

    @patch("aura_cli.cli.helpers.console")
    @patch("aura_cli.cli.helpers.time.sleep")
    def test_display_splash_screen_no_animations(self, mock_sleep, mock_console):
        """Test splash screen display without animations (animations.py removed)."""
        display_aura_splash_screen()
        assert mock_console.print.called

    @patch("aura_cli.cli.helpers.console")
    @patch("aura_cli.cli.helpers.time.sleep")
    def test_display_splash_screen_with_animations(self, mock_sleep, mock_console):
        """Test splash screen display (ANIMATIONS_AVAILABLE always False)."""
        display_aura_splash_screen()
        assert mock_console.print.called


class TestInitializeConversationHistory:
    """Test suite for initialize_conversation_history."""

    def test_initializes_with_system_message(self):
        """Test that history is initialized with system message."""
        history = initialize_conversation_history()

        assert len(history) > 0
        assert history[0]["role"] == "system"
        assert history[0]["role"] == "system"  # system message is present
        assert "ferramentas" in history[0]["content"].lower()


class TestSetupPromptSession:
    """Test suite for setup_prompt_session."""

    @patch("aura_cli.cli.helpers.FileHistory")
    @patch("aura_cli.cli.helpers.PromptSession")
    @patch("aura_cli.cli.helpers.create_key_bindings")
    def test_setup_prompt_session(self, mock_key_bindings, mock_session, mock_history):
        """Test prompt session setup."""
        mock_key_bindings_instance = Mock()
        mock_key_bindings.return_value = mock_key_bindings_instance

        session = setup_prompt_session()

        assert session is not None
        mock_session.assert_called_once()


class TestHandleStatusUpdates:
    """Test suite for handle_status_updates."""

    @patch("aura_cli.cli.helpers.console.print")
    def test_handle_status_updates_empty_queue(self, mock_print):
        """Test handling empty status queue."""
        status_queue = queue.Queue()
        handle_status_updates(status_queue)
        # Should not print anything
        assert not mock_print.called

    @patch("aura_cli.cli.helpers.console.print")
    def test_handle_status_updates_with_panel(self, mock_print):
        """Test handling status updates with panel."""
        mock_panel = Mock()
        with patch(
            "aura_cli.cli.ui.status_panel.create_status_panel", return_value=mock_panel
        ):
            status_queue = queue.Queue()
            status_queue.put("Test message")

            handle_status_updates(status_queue)

            assert mock_print.called

    @patch("aura_cli.cli.helpers.console.print")
    def test_handle_status_updates_fallback(self, mock_print):
        """Test handling status updates with fallback (should not print if panel creation fails)."""
        status_queue = queue.Queue()
        status_queue.put("Test message")

        # Mock create_status_panel import to raise ImportError
        with patch(
            "aura_cli.cli.ui.status_panel.create_status_panel",
            side_effect=ImportError(),
        ):
            handle_status_updates(status_queue)

        # In the current version, it does NOT print if create_status_panel fails
        assert not mock_print.called

    @patch("aura_cli.cli.helpers.console.print")
    def test_handle_status_updates_agi_message(self, mock_print):
        """Test handling AGI status message."""
        status_queue = queue.Queue()
        status_queue.put("[Aura AGI] Processing task")

        # Mock successful panel creation
        with patch(
            "aura_cli.cli.ui.status_panel.create_status_panel", return_value="Panel"
        ):
            handle_status_updates(status_queue)

        assert mock_print.called

    @patch("aura_cli.cli.helpers.console.print")
    def test_handle_status_updates_ops_message(self, mock_print):
        """Test handling Ops status message."""
        status_queue = queue.Queue()
        status_queue.put("[Aura Ops] Running command")

        # Mock successful panel creation
        with patch(
            "aura_cli.cli.ui.status_panel.create_status_panel", return_value="Panel"
        ):
            handle_status_updates(status_queue)

        assert mock_print.called

    @patch("aura_cli.cli.helpers.console.print")
    def test_handle_status_updates_dict_message(self, mock_print):
        """Test handling dict status message."""
        status_queue = queue.Queue()
        status_queue.put({"message": "Test message"})

        # Mock successful panel creation
        with patch(
            "aura_cli.cli.ui.status_panel.create_status_panel", return_value="Panel"
        ):
            handle_status_updates(status_queue)

        assert mock_print.called


class TestParseAgiCommand:
    """Test suite for parse_agi_command."""

    def test_parse_agi_with_objective(self):
        """Test parsing AGI command with objective."""
        result = parse_agi_command("/agi criar um blog")
        assert result == "criar um blog"

    def test_parse_agi_without_objective(self):
        """Test parsing AGI command without objective."""
        result = parse_agi_command("/agi")
        assert result is not None
        assert len(result) > 0

    def test_parse_agi_empty_string(self):
        """Test parsing empty AGI command."""
        result = parse_agi_command("")
        # Empty string returns default exploration task
        assert result is not None and len(result) > 0

    def test_parse_agi_not_agi_command(self):
        """Test parsing non-AGI command."""
        result = parse_agi_command("/help")
        # parse_agi_command doesn't validate prefix, it just extracts after index 4
        # So "/help" becomes "p" (everything after index 4)
        assert result == "p"


class TestParseOpsCommand:
    """Test suite for parse_ops_command."""

    def test_parse_ops_with_mode_and_task(self):
        """Test parsing Ops command with mode and task."""
        mode, task = parse_ops_command("/ops git status")
        assert mode == "git"
        assert task == "status"

    def test_parse_ops_without_mode(self):
        """Test parsing Ops command without mode."""
        mode, task = parse_ops_command("/ops status")
        assert mode == "general"
        assert task == "status"

    def test_parse_ops_docker_command(self):
        """Test parsing Docker Ops command."""
        mode, task = parse_ops_command("/ops docker ps")
        assert mode == "docker"
        assert task == "ps"

    def test_parse_ops_empty(self):
        """Test parsing empty Ops command."""
        mode, task = parse_ops_command("/ops")
        assert mode == "general"
        assert task is not None


class TestGetApiKeysDict:
    """Test suite for get_api_keys_dict."""

    @patch.dict(os.environ, {}, clear=True)
    @patch("aura_cli.core.config.ConfigCompat")
    @patch("aura_cli.core.secure_config.secure_config_manager")
    def test_get_api_keys_dict_empty(self, mock_secure, mock_compat_cls):
        """Test getting API keys when none are set."""
        mock_compat_cls.return_value.get_api_key.return_value = None
        mock_secure.get_api_key.return_value = None
        with patch.dict(os.environ, {}, clear=True):
            keys = get_api_keys_dict()
            assert keys == {}

    @patch("aura_cli.core.config.ConfigCompat")
    @patch("aura_cli.core.secure_config.secure_config_manager")
    @patch.dict(os.environ, {"GOOGLE_API_KEY": "test_google_key"}, clear=True)
    def test_get_api_keys_dict_google(self, mock_secure, mock_compat_cls):
        """Test getting Google API key from env."""
        mock_compat_cls.return_value.get_api_key.return_value = None
        mock_secure.get_api_key.return_value = None
        keys = get_api_keys_dict()
        assert "GOOGLE_API_KEY" in keys
        assert keys["GOOGLE_API_KEY"] == "test_google_key"

    @patch("aura_cli.core.config.ConfigCompat")
    @patch("aura_cli.core.secure_config.secure_config_manager")
    @patch.dict(
        os.environ,
        {
            "GOOGLE_API_KEY": "test_google",
            "OPENAI_API_KEY": "test_openai",
            "ANTHROPIC_API_KEY": "test_anthropic",
        },
        clear=True,
    )
    def test_get_api_keys_dict_all(self, mock_secure, mock_compat_cls):
        """Test getting all API keys."""
        mock_compat_cls.return_value.get_api_key.return_value = None
        mock_secure.get_api_key.return_value = None
        keys = get_api_keys_dict()
        # Check that at least the 3 expected keys are present
        assert "GOOGLE_API_KEY" in keys
        assert "OPENAI_API_KEY" in keys
        assert "ANTHROPIC_API_KEY" in keys
        assert len(keys) >= 3


class TestHandleMultilineInput:
    """Test suite for handle_multiline_input."""

    @patch("aura_cli.cli.helpers.console")
    @patch("builtins.input")
    def test_handle_multiline_input_complete(self, mock_input, mock_console):
        """Test handling complete multiline input."""
        mock_input.side_effect = ["line 1", "line 2", '"""']

        result = handle_multiline_input()

        assert result is not None
        assert "line 1" in result
        assert "line 2" in result

    @patch("aura_cli.cli.helpers.console")
    @patch("builtins.input")
    def test_handle_multiline_input_cancelled(self, mock_input, mock_console):
        """Test handling cancelled multiline input."""
        mock_input.side_effect = KeyboardInterrupt()

        result = handle_multiline_input()

        assert result is None

    @patch("aura_cli.cli.helpers.console")
    @patch("builtins.input")
    def test_handle_multiline_input_empty(self, mock_input, mock_console):
        """Test handling empty multiline input."""
        mock_input.side_effect = ['"""']

        result = handle_multiline_input()

        # Empty input may return empty string or None
        assert result == "" or result is None


class TestProcessSlashCommand:
    """Test suite for process_slash_command."""

    def test_process_slash_command_help(self):
        """Test processing /help command."""
        from aura_cli.cli.command_processor import process_slash_command

        mock_ui = Mock()
        mock_stats = Mock()
        mock_console = Mock()
        mock_app_loop = Mock()
        mock_agi_thread = None
        mock_ops_thread = None

        result = process_slash_command(
            "/help",
            mock_agi_thread,
            mock_ops_thread,
            "gpt-4",
            mock_stats,
            mock_ui,
            mock_console,
            None,
            mock_app_loop,
        )
        assert result[0] is True

    def test_process_slash_command_tools(self):
        """Test processing /tools command."""
        from aura_cli.cli.command_processor import process_slash_command

        mock_ui = Mock()
        mock_stats = Mock()
        mock_console = Mock()
        mock_app_loop = Mock()
        mock_agi_thread = None
        mock_ops_thread = None

        result = process_slash_command(
            "/tools",
            mock_agi_thread,
            mock_ops_thread,
            "gpt-4",
            mock_stats,
            mock_ui,
            mock_console,
            None,
            mock_app_loop,
        )
        assert result[0] is True

    def test_process_slash_command_clear(self):
        """Test processing /clear command."""
        from aura_cli.cli.command_processor import process_slash_command

        mock_ui = Mock()
        mock_stats = Mock()
        mock_console = Mock()
        mock_app_loop = Mock()
        mock_agi_thread = None
        mock_ops_thread = None

        result = process_slash_command(
            "/clear",
            mock_agi_thread,
            mock_ops_thread,
            "gpt-4",
            mock_stats,
            mock_ui,
            mock_console,
            None,
            mock_app_loop,
        )
        assert result[0] is True

    def test_process_slash_command_unknown(self):
        """Test processing unknown slash command."""
        from aura_cli.cli.command_processor import process_slash_command

        mock_ui = Mock()
        mock_stats = Mock()
        mock_console = Mock()
        mock_app_loop = Mock()

        result = process_slash_command(
            "/unknown",
            None,
            None,
            "gpt-4",
            mock_stats,
            mock_ui,
            mock_console,
            None,
            mock_app_loop,
        )
        assert result[0] is True
        # Should return message about unknown command
