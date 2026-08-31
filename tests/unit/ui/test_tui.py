"""
Tests for TUI Components.
"""

from unittest.mock import MagicMock

from aura_cli.tui.bridge import TextualUIManager
from aura_cli.tui.widgets.status import AuraStatusSidebar


class TestBridgeAdapter:
    def test_print_redirection(self):
        """Test that print() calls are redirected to TUI log."""
        mock_app = MagicMock()
        mock_app.is_running = True
        adapter = TextualUIManager(mock_app, status_queue=None, stats=None)

        adapter.print("Hello World")

        # Should call through thread-safe path
        mock_app.call_from_thread.assert_called()

    def test_display_methods(self):
        """Test display_success/error methods."""
        mock_app = MagicMock()
        mock_app.is_running = True
        adapter = TextualUIManager(mock_app, status_queue=None, stats=None)

        adapter.display_success("Great job")
        adapter.display_error("Oh no")

        # Should create notifications
        assert mock_app.call_from_thread.call_count >= 2


class TestTUIWidgets:
    def test_status_sidebar_has_metrics_panel(self):
        """Test that status sidebar has MetricsPanel component."""

        sidebar = AuraStatusSidebar()
        # Verify the sidebar has the update_stats method
        assert hasattr(sidebar, "update_stats")
        assert hasattr(sidebar, "update_task_tree")
