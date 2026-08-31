"""Tests for responsive module.

Tests for terminal size detection and adaptive layouts.
"""

from unittest.mock import MagicMock

import pytest


class TestTerminalSize:
    """Tests for TerminalSize enum."""

    def test_terminal_size_values(self):
        """Test TerminalSize enum has expected values."""
        from aura_cli.cli.ui.responsive import TerminalSize

        assert TerminalSize.SMALL.value == "small"
        assert TerminalSize.MEDIUM.value == "medium"
        assert TerminalSize.LARGE.value == "large"
        assert TerminalSize.XLARGE.value == "xlarge"


class TestResponsiveLayout:
    """Tests for ResponsiveLayout class."""

    @pytest.fixture
    def mock_console(self):
        """Create mock console with configurable size."""
        console = MagicMock()
        console.width = 100
        console.height = 30
        return console

    def test_responsive_layout_creation(self, mock_console):
        """Test ResponsiveLayout can be created."""
        from aura_cli.cli.ui.responsive import ResponsiveLayout

        layout = ResponsiveLayout(mock_console)

        assert layout is not None
        assert layout.width == 100
        assert layout.height == 30

    def test_responsive_layout_default_console(self):
        """Test ResponsiveLayout creates default console."""
        from aura_cli.cli.ui.responsive import ResponsiveLayout

        layout = ResponsiveLayout()

        assert layout.console is not None

    def test_categorize_size_small(self, mock_console):
        """Test categorization for small terminal."""
        from aura_cli.cli.ui.responsive import ResponsiveLayout, TerminalSize

        mock_console.width = 60
        layout = ResponsiveLayout(mock_console)

        assert layout.size_category == TerminalSize.SMALL

    def test_categorize_size_medium(self, mock_console):
        """Test categorization for medium terminal."""
        from aura_cli.cli.ui.responsive import ResponsiveLayout, TerminalSize

        mock_console.width = 100
        layout = ResponsiveLayout(mock_console)

        assert layout.size_category == TerminalSize.MEDIUM

    def test_categorize_size_large(self, mock_console):
        """Test categorization for large terminal."""
        from aura_cli.cli.ui.responsive import ResponsiveLayout, TerminalSize

        mock_console.width = 140
        layout = ResponsiveLayout(mock_console)

        assert layout.size_category == TerminalSize.LARGE

    def test_categorize_size_xlarge(self, mock_console):
        """Test categorization for extra large terminal."""
        from aura_cli.cli.ui.responsive import ResponsiveLayout, TerminalSize

        mock_console.width = 200
        layout = ResponsiveLayout(mock_console)

        assert layout.size_category == TerminalSize.XLARGE

    def test_get_panel_width(self, mock_console):
        """Test get_panel_width calculation."""
        from aura_cli.cli.ui.responsive import ResponsiveLayout

        mock_console.width = 100
        layout = ResponsiveLayout(mock_console)

        width = layout.get_panel_width(0.9)

        assert width == 90

    def test_get_panel_width_default(self, mock_console):
        """Test get_panel_width with default percentage."""
        from aura_cli.cli.ui.responsive import ResponsiveLayout

        mock_console.width = 100
        layout = ResponsiveLayout(mock_console)

        width = layout.get_panel_width()

        assert width == 90  # 0.9 is default

    def test_get_panel_width_clamps_invalid_percentages(self, mock_console):
        from aura_cli.cli.ui.responsive import ResponsiveLayout

        layout = ResponsiveLayout(mock_console)

        assert layout.get_panel_width(-1) == 1
        assert layout.get_panel_width(2) == 100
        assert layout.get_panel_width("invalid") == 90

    def test_get_column_count(self, mock_console):
        """Test get_column_count calculation."""
        from aura_cli.cli.ui.responsive import ResponsiveLayout

        mock_console.width = 120
        layout = ResponsiveLayout(mock_console)

        columns = layout.get_column_count(40)

        assert columns == 3  # 120 / 40 = 3

    def test_get_column_count_minimum(self, mock_console):
        """Test get_column_count returns at least 1."""
        from aura_cli.cli.ui.responsive import ResponsiveLayout

        mock_console.width = 30
        layout = ResponsiveLayout(mock_console)

        columns = layout.get_column_count(100)

        assert columns == 1

    def test_get_column_count_guards_invalid_width(self, mock_console):
        from aura_cli.cli.ui.responsive import ResponsiveLayout

        layout = ResponsiveLayout(mock_console)

        assert layout.get_column_count(0) == 100
        assert layout.get_column_count("invalid") == 2

    def test_should_show_sidebar_large(self, mock_console):
        """Test should_show_sidebar for large terminal."""
        from aura_cli.cli.ui.responsive import ResponsiveLayout

        mock_console.width = 140
        layout = ResponsiveLayout(mock_console)

        assert layout.should_show_sidebar() is True

    def test_should_show_sidebar_small(self, mock_console):
        """Test should_show_sidebar for small terminal."""
        from aura_cli.cli.ui.responsive import ResponsiveLayout

        mock_console.width = 60
        layout = ResponsiveLayout(mock_console)

        assert layout.should_show_sidebar() is False

    def test_should_show_footer_tall(self, mock_console):
        """Test should_show_footer for tall terminal."""
        from aura_cli.cli.ui.responsive import ResponsiveLayout

        mock_console.height = 30
        layout = ResponsiveLayout(mock_console)

        assert layout.should_show_footer() is True

    def test_should_show_footer_short(self, mock_console):
        """Test should_show_footer for short terminal."""
        from aura_cli.cli.ui.responsive import ResponsiveLayout

        mock_console.height = 15
        layout = ResponsiveLayout(mock_console)

        assert layout.should_show_footer() is False

    def test_get_max_lines(self, mock_console):
        """Test get_max_lines calculation."""
        from aura_cli.cli.ui.responsive import ResponsiveLayout

        mock_console.height = 30
        layout = ResponsiveLayout(mock_console)

        max_lines = layout.get_max_lines(reserve=5)

        assert max_lines == 25

    def test_get_max_lines_minimum(self, mock_console):
        """Test get_max_lines returns at least 10."""
        from aura_cli.cli.ui.responsive import ResponsiveLayout

        mock_console.height = 10
        layout = ResponsiveLayout(mock_console)

        max_lines = layout.get_max_lines(reserve=5)

        assert max_lines == 10

    def test_create_adaptive_panel(self, mock_console):
        """Test create_adaptive_panel returns Panel."""
        from rich.panel import Panel

        from aura_cli.cli.ui.responsive import ResponsiveLayout

        layout = ResponsiveLayout(mock_console)

        panel = layout.create_adaptive_panel("content", "Title")

        assert isinstance(panel, Panel)

    def test_create_adaptive_table(self, mock_console):
        """Test create_adaptive_table returns Table."""
        from rich.table import Table

        from aura_cli.cli.ui.responsive import ResponsiveLayout

        layout = ResponsiveLayout(mock_console)

        table = layout.create_adaptive_table()

        assert isinstance(table, Table)

    def test_truncate_text_short(self, mock_console):
        """Test truncate_text with short text."""
        from aura_cli.cli.ui.responsive import ResponsiveLayout

        mock_console.width = 100
        layout = ResponsiveLayout(mock_console)

        result = layout.truncate_text("short text")

        assert result == "short text"

    def test_truncate_text_long(self, mock_console):
        """Test truncate_text with long text."""
        from aura_cli.cli.ui.responsive import ResponsiveLayout

        mock_console.width = 20
        layout = ResponsiveLayout(mock_console)

        result = layout.truncate_text(
            "this is a very long text that should be truncated"
        )

        assert result.endswith("...")
        assert len(result) <= 16 + 3  # 20 * 0.8 + 3

    def test_truncate_text_handles_narrow_terminal(self, mock_console):
        from aura_cli.cli.ui.responsive import ResponsiveLayout

        mock_console.width = 1
        layout = ResponsiveLayout(mock_console)

        assert layout.truncate_text("long text") == "l"

    def test_get_layout_config(self, mock_console):
        """Test get_layout_config returns config dict."""
        from aura_cli.cli.ui.responsive import ResponsiveLayout

        layout = ResponsiveLayout(mock_console)

        config = layout.get_layout_config()

        assert isinstance(config, dict)
        assert "columns" in config
        assert "show_sidebar" in config
        assert "show_footer" in config
        assert "padding" in config
        assert "max_content_width" in config

    def test_check_size_change_no_change(self, mock_console):
        """Test check_size_change when no change."""
        import time

        from aura_cli.cli.ui.responsive import ResponsiveLayout

        layout = ResponsiveLayout(mock_console)
        layout._last_size_check = time.time() - 2  # Force check

        result = layout.check_size_change()

        assert result is False  # No change

    def test_check_size_change_with_change(self, mock_console):
        """Test check_size_change when size changed."""
        import time

        from aura_cli.cli.ui.responsive import ResponsiveLayout

        layout = ResponsiveLayout(mock_console)
        layout._last_size_check = time.time() - 2  # Force check

        # Change size
        mock_console.width = 200

        result = layout.check_size_change()

        assert result is True


class TestResponsiveText:
    """Tests for ResponsiveText class."""

    def test_wrap_text(self):
        """Test wrap_text function."""
        from aura_cli.cli.ui.responsive import ResponsiveText

        text = "This is a long text that should be wrapped"

        result = ResponsiveText.wrap_text(text, width=20)

        assert "\n" in result

    def test_wrap_text_with_indent(self):
        """Test wrap_text with indent."""
        from aura_cli.cli.ui.responsive import ResponsiveText

        text = "Short text"

        result = ResponsiveText.wrap_text(text, width=50, indent=4)

        assert result.startswith("    ")

    def test_ellipsize_short(self):
        """Test ellipsize with short text."""
        from aura_cli.cli.ui.responsive import ResponsiveText

        result = ResponsiveText.ellipsize("short", max_length=20)

        assert result == "short"

    def test_ellipsize_end(self):
        """Test ellipsize at end."""
        from aura_cli.cli.ui.responsive import ResponsiveText

        result = ResponsiveText.ellipsize("this is a long text", max_length=10)

        assert result.endswith("...")
        assert len(result) == 10

    def test_ellipsize_middle(self):
        """Test ellipsize at middle."""
        from aura_cli.cli.ui.responsive import ResponsiveText

        result = ResponsiveText.ellipsize(
            "this is a long text", max_length=13, position="middle"
        )

        assert "..." in result
        assert len(result) <= 13

    def test_ellipsize_start(self):
        """Test ellipsize at start."""
        from aura_cli.cli.ui.responsive import ResponsiveText

        result = ResponsiveText.ellipsize(
            "this is a long text", max_length=10, position="start"
        )

        assert result.startswith("...")
        assert len(result) == 10


class TestHelperFunctions:
    """Tests for module-level helper functions."""

    def test_get_responsive_layout(self):
        """Test get_responsive_layout function."""
        from aura_cli.cli.ui.responsive import ResponsiveLayout, get_responsive_layout

        layout = get_responsive_layout()

        assert isinstance(layout, ResponsiveLayout)

    def test_get_terminal_size(self):
        """Test get_terminal_size function."""
        from aura_cli.cli.ui.responsive import get_terminal_size

        width, height = get_terminal_size()

        assert isinstance(width, int)
        assert isinstance(height, int)
        assert width > 0
        assert height > 0

    def test_is_small_terminal(self):
        """Test is_small_terminal function."""
        from aura_cli.cli.ui.responsive import is_small_terminal

        result = is_small_terminal()

        assert isinstance(result, bool)

    def test_is_large_terminal(self):
        """Test is_large_terminal function."""
        from aura_cli.cli.ui.responsive import is_large_terminal

        result = is_large_terminal()

        assert isinstance(result, bool)
