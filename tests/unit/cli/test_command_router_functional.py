"""Functional tests for command router module.

Tests for actual functionality of command routing.
"""

from pathlib import Path
import threading
from unittest.mock import MagicMock, patch

import pytest


class TestRouteCommand:
    """Tests for route_command function."""

    @pytest.fixture
    def mock_dependencies(self):
        """Create mock dependencies for route_command."""
        return {
            "agi_thread": None,
            "ops_thread": None,
            "current_model": "gpt-4",
            "stats": MagicMock(),
            "ui": MagicMock(),
            "console": MagicMock(),
            "project_root": Path.cwd(),
            "app_loop": None,
        }

    def test_route_slash_command_help(self, mock_dependencies):
        """Test routing /help command."""
        from aura_cli.cli.command_router import route_command

        with patch("aura_cli.cli.command_router.process_slash_command") as mock_process:
            mock_process.return_value = (True, "Help message", None, None, None)

            result = route_command(
                "/help",
                mock_dependencies["agi_thread"],
                mock_dependencies["ops_thread"],
                mock_dependencies["current_model"],
                mock_dependencies["stats"],
                mock_dependencies["ui"],
                mock_dependencies["console"],
                mock_dependencies["project_root"],
            )

            assert result[0] is True  # should_continue
            mock_process.assert_called_once()


    def test_route_llm_query(self, mock_dependencies):
        """Test routing regular text as LLM query."""
        from aura_cli.cli.command_router import route_command

        with patch(
            "aura_cli.cli.command_router.should_execute_directly"
        ) as mock_should:
            mock_should.return_value = False

            result = route_command(
                "What is Python?",
                mock_dependencies["agi_thread"],
                mock_dependencies["ops_thread"],
                mock_dependencies["current_model"],
                mock_dependencies["stats"],
                mock_dependencies["ui"],
                mock_dependencies["console"],
            )

            assert result[0] is True  # should_continue
            assert result[1] == "llm_query"

    def test_route_preserves_threads(self, mock_dependencies):
        """Test that routing preserves thread references."""
        from aura_cli.cli.command_router import route_command

        mock_thread = MagicMock(spec=threading.Thread)

        with patch(
            "aura_cli.cli.command_router.should_execute_directly"
        ) as mock_should:
            mock_should.return_value = False

            result = route_command(
                "Hello",
                mock_thread,  # agi_thread
                mock_thread,  # ops_thread
                mock_dependencies["current_model"],
                mock_dependencies["stats"],
                mock_dependencies["ui"],
                mock_dependencies["console"],
            )

            assert result[2] == mock_thread  # agi_thread preserved
            assert result[3] == mock_thread  # ops_thread preserved

    def test_route_preserves_model(self, mock_dependencies):
        """Test that routing preserves model name."""
        from aura_cli.cli.command_router import route_command

        with patch(
            "aura_cli.cli.command_router.should_execute_directly"
        ) as mock_should:
            mock_should.return_value = False

            result = route_command(
                "Hello",
                None,
                None,
                "claude-3-opus",
                mock_dependencies["stats"],
                mock_dependencies["ui"],
                mock_dependencies["console"],
            )

            assert result[4] == "claude-3-opus"  # model preserved

    def test_route_model_command(self, mock_dependencies):
        """Test routing /model command."""
        from aura_cli.cli.command_router import route_command

        with patch("aura_cli.cli.command_router.process_slash_command") as mock_process:
            # Simulating model change
            mock_process.return_value = (
                True,
                "Modelo alterado",
                None,
                None,
                "gpt-4-turbo",
            )

            result = route_command(
                "/model gpt-4-turbo",
                mock_dependencies["agi_thread"],
                mock_dependencies["ops_thread"],
                mock_dependencies["current_model"],
                mock_dependencies["stats"],
                mock_dependencies["ui"],
                mock_dependencies["console"],
            )

            assert result[0] is True
            assert result[4] == "gpt-4-turbo"  # new model


    def test_route_notification_message(self, mock_dependencies):
        """Test that certain messages trigger notifications."""
        from aura_cli.cli.command_router import route_command

        with patch("aura_cli.cli.command_router.process_slash_command") as mock_process:
            mock_process.return_value = (True, "Aura Dev: ativado", None, None, None)

            route_command(
                "/dev",
                mock_dependencies["agi_thread"],
                mock_dependencies["ops_thread"],
                mock_dependencies["current_model"],
                mock_dependencies["stats"],
                mock_dependencies["ui"],
                mock_dependencies["console"],
            )

            # Should trigger notification
            mock_dependencies["stats"].set_notification.assert_called()
