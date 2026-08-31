"""Comprehensive tests for ui/manager.py - UIManager complete coverage.

Tests verify all UIManager methods and functionality.
"""

from queue import Queue
from unittest.mock import Mock

from aura_cli.cli.ui.manager import UIManager


class TestUIManager:
    """Test suite for UIManager."""

    def test_initialization(self):
        """Test UIManager initialization."""
        mock_stats = Mock()
        status_queue = Queue()

        ui = UIManager(stats=mock_stats, status_queue=status_queue)

        assert ui.stats == mock_stats
        assert ui.status_queue == status_queue

    def test_display_info(self):
        """Test display_info method."""
        ui = UIManager(stats=Mock(), status_queue=Queue())
        # Mock internal coordinator directly
        ui._render_coordinator = Mock()
        ui.display_info("Test info message")

        assert ui._render_coordinator.render_info.called
        ui._render_coordinator.render_info.assert_called_once_with("Test info message")

    def test_display_success(self):
        """Test display_success method."""
        ui = UIManager(stats=Mock(), status_queue=Queue())
        ui._render_coordinator = Mock()
        ui.display_success("Test success message")

        assert ui._render_coordinator.render_success.called
        ui._render_coordinator.render_success.assert_called_once_with(
            "Test success message"
        )

    def test_display_error(self):
        """Test display_error method."""
        ui = UIManager(stats=Mock(), status_queue=Queue())
        ui._render_coordinator = Mock()
        ui.display_error("Test error message")

        assert ui._render_coordinator.render_error.called
        ui._render_coordinator.render_error.assert_called_once_with(
            "Test error message"
        )

    def test_display_warning(self):
        """Test display_warning method."""
        ui = UIManager(stats=Mock(), status_queue=Queue())
        ui._render_coordinator = Mock()
        ui.display_warning("Test warning message")

        assert ui._render_coordinator.render_warning.called
        ui._render_coordinator.render_warning.assert_called_once_with(
            "Test warning message"
        )

    def test_prompt(self):
        """Test prompt method."""
        ui = UIManager(stats=Mock(), status_queue=Queue())
        # Mock input manager
        ui._input_manager = Mock()
        ui._input_manager.prompt.return_value = "user input"

        result = ui.prompt()

        assert result == "user input"
        ui._input_manager.prompt.assert_called_once()

    def test_prompt_with_session(self):
        """Test prompt with session."""
        ui = UIManager(stats=Mock(), status_queue=Queue())
        ui._input_manager = Mock()
        ui._input_manager.prompt.return_value = "user input"

        result = ui.prompt()

        assert result == "user input"
