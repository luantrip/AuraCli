"""Functional tests for CLI helpers module.

Tests for actual functionality of CLI helper functions.
"""

import queue
from unittest.mock import patch


class TestParseAgiCommand:
    """Tests for parse_agi_command function."""

    def test_parse_with_objective(self):
        """Test parsing /agi with objective."""
        from aura_cli.cli.helpers import parse_agi_command

        result = parse_agi_command("/agi create a REST API")
        assert result == "create a REST API"

    def test_parse_without_objective(self):
        """Test parsing /agi without objective."""
        from aura_cli.cli.helpers import parse_agi_command

        result = parse_agi_command("/agi")
        assert "Explore" in result or "diretório" in result

    def test_parse_with_whitespace(self):
        """Test parsing /agi with extra whitespace."""
        from aura_cli.cli.helpers import parse_agi_command

        result = parse_agi_command("/agi   create something  ")
        assert result.strip() == "create something"

    def test_parse_empty_objective(self):
        """Test parsing /agi with only whitespace."""
        from aura_cli.cli.helpers import parse_agi_command

        result = parse_agi_command("/agi   ")
        assert len(result) > 10  # Default objective should be long


class TestParseOpsCommand:
    """Tests for parse_ops_command function."""

    def test_parse_git_command(self):
        """Test parsing /ops git status."""
        from aura_cli.cli.helpers import parse_ops_command

        mode, task = parse_ops_command("/ops git status")
        assert mode == "git"
        assert task == "status"

    def test_parse_docker_command(self):
        """Test parsing /ops docker ps."""
        from aura_cli.cli.helpers import parse_ops_command

        mode, task = parse_ops_command("/ops docker ps")
        assert mode == "docker"
        assert task == "ps"

    def test_parse_general_command(self):
        """Test parsing /ops with general task."""
        from aura_cli.cli.helpers import parse_ops_command

        mode, task = parse_ops_command("/ops check system health")
        assert mode == "general"
        assert "check system health" in task

    def test_parse_empty_command(self):
        """Test parsing /ops without args."""
        from aura_cli.cli.helpers import parse_ops_command

        mode, task = parse_ops_command("/ops")
        assert mode == "general"
        assert "Analise" in task or "infraestrutura" in task

    def test_parse_mode_only(self):
        """Test parsing /ops with only mode."""
        from aura_cli.cli.helpers import parse_ops_command

        mode, task = parse_ops_command("/ops git")
        assert mode == "git"
        assert "Analise" in task  # Default task


class TestGetApiKeysDict:
    """Tests for get_api_keys_dict function."""

    def test_get_keys_from_env(self, monkeypatch):
        """Test getting API keys from environment variables."""
        from aura_cli.cli.helpers import get_api_keys_dict

        # Set up test environment
        monkeypatch.setenv("GOOGLE_API_KEY", "test-google-key")
        monkeypatch.setenv("OPENAI_API_KEY", "test-openai-key")

        # Mock SecureConfig module
        with patch("aura_cli.core.secure_config.secure_config_manager") as mock_config:
            mock_config.get_api_key.return_value = None

            keys = get_api_keys_dict()

            # Should get keys from environment
            assert "GOOGLE_API_KEY" in keys or "OPENAI_API_KEY" in keys


class TestInitializeConversationHistory:
    """Tests for initialize_conversation_history function."""


    def test_contains_system_message(self):
        """Test that list contains system message."""
        from aura_cli.cli.helpers import initialize_conversation_history

        result = initialize_conversation_history()
        assert len(result) > 0
        assert result[0]["role"] == "system"

    def test_system_message_content(self):
        """Test system message content."""
        from aura_cli.cli.helpers import initialize_conversation_history

        result = initialize_conversation_history()
        content = result[0]["content"]

        # Check for key content
        assert "Aura" in content
        assert "ferramentas" in content.lower() or "tools" in content.lower()


class TestHandleStatusUpdates:
    """Tests for handle_status_updates function."""


    def test_queue_with_string_message(self):
        """Test handling queue with string message."""
        from aura_cli.cli.helpers import handle_status_updates

        status_queue = queue.Queue()
        status_queue.put("Test status message")

        with patch("aura_cli.cli.helpers.console"):
            handle_status_updates(status_queue)

        # Queue should be empty after processing
        assert status_queue.empty()

    def test_queue_with_dict_message(self):
        """Test handling queue with dict message."""
        from aura_cli.cli.helpers import handle_status_updates

        status_queue = queue.Queue()
        status_queue.put({"message": "Test message"})

        with patch("aura_cli.cli.helpers.console"):
            handle_status_updates(status_queue)

        assert status_queue.empty()


class TestSetupPromptSession:
    """Tests for setup_prompt_session function."""


class TestDisplayAuraSplashScreen:
    """Tests for display_aura_splash_screen function."""

