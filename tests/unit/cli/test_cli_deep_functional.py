"""Deep functional tests for CLI modules.

These tests exercise actual code paths to increase coverage.
"""

import queue
from unittest.mock import MagicMock, patch


class TestUIManagerDeep:
    """Deep tests for UIManager."""

    def test_ui_manager_creation(self):
        """Test UIManager creation."""
        from aura_cli.cli.ui.manager import UIManager

        ui = UIManager()
        assert ui is not None
        assert hasattr(ui, "display_info")
        assert hasattr(ui, "display_error")
        assert hasattr(ui, "display_success")
        assert hasattr(ui, "display_warning")

    def test_ui_manager_status_queue(self):
        """Test UIManager with status queue."""
        from aura_cli.cli.ui.manager import UIManager

        ui = UIManager()
        assert hasattr(ui, "status_queue")

    def test_ui_manager_has_display_methods(self):
        """Test UIManager has display methods."""
        from aura_cli.cli.ui.manager import UIManager

        ui = UIManager()

        assert hasattr(ui, "display_info")
        assert hasattr(ui, "display_error")
        assert hasattr(ui, "display_success")
        assert hasattr(ui, "display_warning")


class TestUIConstantsDeep:
    """Deep tests for UI constants."""

    def test_ui_icons_exist(self):
        """Test that UI icons are defined."""
        from aura_cli.cli.ui.constants import UIIcons

        assert hasattr(UIIcons, "SUCCESS")
        assert hasattr(UIIcons, "ERROR")
        assert hasattr(UIIcons, "WARNING")
        assert hasattr(UIIcons, "INFO")

    def test_ui_styles_exist(self):
        """Test that UI styles are defined."""
        from aura_cli.cli.ui.constants import UIStyles

        assert hasattr(UIStyles, "PRIMARY")
        assert hasattr(UIStyles, "ERROR")
        assert hasattr(UIStyles, "WARNING")
        assert hasattr(UIStyles, "SUCCESS")


class TestKeyBindingsDeep:
    """Deep tests for key bindings."""


class TestFunctionCallHandlerDeep:
    """Deep tests for function call handler."""


class TestCommandProcessorDeep:
    """Deep tests for command processor."""


class TestDashboardHelperDeep:
    """Deep tests for dashboard helper."""


class TestTableFormatterDeep:
    """Deep tests for table formatter."""


class TestLoadingStatesDeep:
    """Deep tests for loading states."""


class TestPresenterDeep:
    """Deep tests for presenter."""


    def test_presenter_display_constitution_missing(self):
        """Presenter should still compose constitution-missing guidance."""
        from aura_cli.cli.ui.presenter import AppPresenter

        console = MagicMock()
        ui = MagicMock()
        stats = MagicMock()

        presenter = AppPresenter(console, ui, stats)

        presenter.display_constitution_missing()

        assert ui.display_info.call_count == 2

    def test_presenter_display_llm_response_uses_message_bubble_path(self):
        """Presenter should render final assistant output with the modern bubble path."""
        from aura_cli.cli.ui.presenter import AppPresenter

        console = MagicMock()
        ui = MagicMock()
        ui.is_tui_mode = (
            False  # must be False or MagicMock attr is truthy → goes TUI branch
        )
        stats = MagicMock()
        stats.tokens_used = 120
        stats.get_files_changed.return_value = False

        presenter = AppPresenter(console, ui, stats)
        presenter.display_llm_response("## Hello\n\nworld", start_time=0.0)

        assert ui.print.called


class TestExceptionsDeep:
    """Deep tests for CLI exceptions."""

    def test_rate_limit_error(self):
        """Test RateLimitError."""
        from aura_cli.cli.utils.exceptions import RateLimitError

        e1 = RateLimitError("Limit exceeded", model="gpt-4", retry_after=60)
        assert e1.model == "gpt-4"
        assert e1.retry_after == 60


class TestHelpersEdgeCases:
    """Edge case tests for helpers."""

    def test_empty_agi_command(self):
        """Test empty /agi command."""
        from aura_cli.cli.helpers import parse_agi_command

        result = parse_agi_command("/agi")
        assert len(result) > 0  # Should have default

    def test_empty_ops_command(self):
        """Test empty /ops command."""
        from aura_cli.cli.helpers import parse_ops_command

        mode, task = parse_ops_command("/ops")
        assert mode == "general"
        assert len(task) > 0  # Should have default


    def test_handle_status_updates_with_messages(self):
        """Test handling status queue with messages."""
        from aura_cli.cli.helpers import handle_status_updates

        status_queue = queue.Queue()
        status_queue.put("Test message 1")
        status_queue.put({"message": "Test message 2"})
        status_queue.put("[Aura AGI] Status update")

        with patch("aura_cli.cli.helpers.console"):
            handle_status_updates(status_queue)

        # Queue should be empty after processing
        assert status_queue.empty()
