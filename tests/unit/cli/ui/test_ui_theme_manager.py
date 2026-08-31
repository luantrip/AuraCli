"""Tests for ui/theme_manager.py - Theme management.

Tests verify:
- ThemeManager: Theme loading and management
- get_theme_manager: Singleton access
- load_theme: Theme loading
- get_current_theme: Current theme retrieval
- list_available_themes: Available themes listing
"""

from unittest.mock import Mock, patch

from aura_cli.cli.ui.theme_manager import (
    ThemeManager,
    get_current_theme,
    get_theme_manager,
    list_available_themes,
    load_theme,
)


class TestThemeManager:
    """Test suite for ThemeManager."""

    def test_theme_manager_singleton(self):
        """Test that ThemeManager is a singleton."""
        manager1 = ThemeManager()
        manager2 = ThemeManager()

        assert manager1 is manager2

    @patch("aura_cli.core.config.config_manager")
    @patch("aura_cli.cli.ui.theme_manager.resources")
    @patch("aura_cli.cli.ui.theme_manager.toml")
    def test_theme_manager_initialization(self, mock_toml, mock_resources, mock_config):
        """Test ThemeManager initialization."""
        mock_config.get.return_value = "nebula"
        mock_resources.files.return_value = []

        # Reset singleton
        ThemeManager._instance = None

        manager = ThemeManager()

        assert manager is not None
        assert hasattr(manager, "colors")
        assert hasattr(manager, "styles")

    def test_theme_manager_get_color(self):
        """Test getting color from theme."""
        ThemeManager._instance = None
        manager = ThemeManager()
        manager.colors = {"primary": "#00ff00"}

        color = manager.get_color("primary")
        assert color == "#00ff00"

    def test_theme_manager_get_icon(self):
        """Test getting icon from theme."""
        ThemeManager._instance = None
        manager = ThemeManager()
        manager.icons = {"status_success": "✓"}

        icon = manager.get_icon("status_success")
        assert icon == "✓"


class TestGetThemeManager:
    """Test suite for get_theme_manager."""

    def test_get_theme_manager_returns_instance(self):
        """Test that get_theme_manager returns ThemeManager instance."""
        manager = get_theme_manager()
        assert isinstance(manager, ThemeManager)


class TestLoadTheme:
    """Test suite for load_theme."""

    @patch("aura_cli.cli.ui.theme_manager.get_theme_manager")
    def test_load_theme_success(self, mock_get_manager):
        """Test loading theme successfully."""
        mock_manager = Mock()
        mock_manager.load_theme.return_value = True
        mock_get_manager.return_value = mock_manager

        result = load_theme("nebula")

        assert result is True
        mock_manager.load_theme.assert_called_with("nebula")

    @patch("aura_cli.cli.ui.theme_manager.get_theme_manager")
    def test_load_theme_failure(self, mock_get_manager):
        """Test loading theme with failure."""
        mock_manager = Mock()
        mock_manager.load_theme.return_value = False
        mock_get_manager.return_value = mock_manager

        result = load_theme("nonexistent")

        assert result is False


class TestGetCurrentTheme:
    """Test suite for get_current_theme."""

    @patch("aura_cli.cli.ui.theme_manager.get_theme_manager")
    def test_get_current_theme(self, mock_get_manager):
        """Test getting current theme."""
        mock_manager = Mock()
        mock_manager.current_theme = "nebula"
        mock_get_manager.return_value = mock_manager

        theme = get_current_theme()

        assert theme == "nebula"


class TestListAvailableThemes:
    """Test suite for list_available_themes."""

    def test_list_available_themes(self):
        """Test listing available themes."""
        themes = list_available_themes()

        assert isinstance(themes, list)
        assert len(themes) > 0
        assert "nebula" in themes
