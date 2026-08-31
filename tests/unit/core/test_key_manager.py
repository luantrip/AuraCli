"""Tests for key_manager.py - API key management.

Tests verify:
- check_api_keys: Verifies API key configuration
- show_settings_menu: Displays and handles settings menu
"""

from unittest.mock import Mock, patch

from aura_cli.cli.key_manager import check_api_keys, show_settings_menu


class TestCheckApiKeys:
    """Test suite for check_api_keys."""

    @patch("aura_cli.cli.key_manager.secure_config_manager")
    @patch("aura_cli.core.config.ConfigCompat")
    def test_check_api_keys_none_configured(self, mock_compat_cls, mock_secure_config):
        """Test checking API keys when none are configured."""
        mock_compat_cls.return_value.get_api_key.return_value = None
        mock_secure_config.get_api_key.return_value = None

        result = check_api_keys()

        assert result is False

    @patch("aura_cli.cli.key_manager.secure_config_manager")
    def test_check_api_keys_google_configured(self, mock_secure_config):
        """Test checking API keys when Google is configured."""

        def side_effect(key):
            if key == "google":
                return "test_key"
            return None

        mock_secure_config.get_api_key.side_effect = side_effect

        result = check_api_keys()

        assert result is True

    @patch("aura_cli.cli.key_manager.secure_config_manager")
    def test_check_api_keys_openai_configured(self, mock_secure_config):
        """Test checking API keys when OpenAI is configured."""

        def side_effect(key):
            if key == "openai":
                return "test_key"
            return None

        mock_secure_config.get_api_key.side_effect = side_effect

        result = check_api_keys()

        assert result is True

    @patch("aura_cli.cli.key_manager.secure_config_manager")
    def test_check_api_keys_anthropic_configured(self, mock_secure_config):
        """Test checking API keys when Anthropic is configured."""

        def side_effect(key):
            if key == "anthropic":
                return "test_key"
            return None

        mock_secure_config.get_api_key.side_effect = side_effect

        result = check_api_keys()

        assert result is True


class TestShowSettingsMenu:
    """Test suite for show_settings_menu."""

    @patch("aura_cli.cli.key_manager.get_api_keys_dict")
    @patch("aura_cli.cli.ui.theme_manager.get_theme_manager")
    @patch("aura_cli.cli.key_manager.console")
    @patch("aura_cli.cli.key_manager.get_config_manager")
    def test_show_settings_menu_display(
        self, mock_get_config, mock_console, mock_get_theme, mock_get_keys
    ):
        """Test that settings menu is displayed."""
        mock_config = Mock()
        # Ensure .get() returns strings or None, not Mocks
        mock_config.get.side_effect = lambda k: (
            "default" if k == "theme_name" else "gpt-4"
        )
        mock_get_config.return_value = mock_config

        mock_theme_manager = Mock()
        mock_theme_manager.current_theme = "default"
        mock_get_theme.return_value = mock_theme_manager

        mock_get_keys.return_value = {}

        # We need to mock _show_settings_tui dependencies effectively
        # Since show_settings_menu imports inside the function, patches might be tricky if not targeting the right path
        # Actually show_settings_menu calls _show_settings_tui which imports radiolist_dialog
        # We should patch radiolist_dialog to avoid TUI interaction

        with patch("aura_cli.cli.key_manager.radiolist_dialog") as mock_dialog:
            mock_dialog.return_value.run.return_value = "exit"
            show_settings_menu()

            assert mock_dialog.called

    @patch("aura_cli.cli.key_manager.get_api_keys_dict")
    @patch("aura_cli.cli.ui.theme_manager.get_theme_manager")
    @patch("aura_cli.cli.key_manager.console")
    @patch("aura_cli.cli.key_manager.get_config_manager")
    def test_show_settings_menu_configure_google(
        self, mock_get_config, mock_console, mock_get_theme, mock_get_keys
    ):
        """Test configuring Google API key."""
        mock_config = Mock()
        mock_config.get.side_effect = lambda k: (
            "default" if k == "theme_name" else "gpt-4"
        )
        mock_get_config.return_value = mock_config

        mock_theme_manager = Mock()
        mock_theme_manager.current_theme = "default"
        mock_get_theme.return_value = mock_theme_manager

        mock_get_keys.return_value = {}

        # Mock radiolist_dialog and input_dialog flow
        with (
            patch("aura_cli.cli.key_manager.radiolist_dialog") as mock_radio,
            patch("aura_cli.cli.key_manager._configure_api_key") as mock_configure,
        ):
            # Sequence: Select 'apis' -> Select 'add_google' -> Configure -> Exit
            mock_radio.return_value.run.side_effect = [
                "apis",
                "add_google",
                "back",
                "exit",
            ]

            show_settings_menu()

            mock_configure.assert_called_with("google", "Google (Gemini)")

    @patch("aura_cli.cli.key_manager.get_api_keys_dict")
    @patch("aura_cli.cli.ui.theme_manager.get_theme_manager")
    @patch("aura_cli.cli.key_manager.console")
    @patch("aura_cli.cli.key_manager.get_config_manager")
    @patch("aura_cli.cli.key_manager._handle_model_menu")
    def test_show_settings_menu_routes_to_model(
        self,
        mock_handle_model,
        mock_get_config,
        mock_console,
        mock_get_theme,
        mock_get_keys,
    ):
        """Test that selecting 'model' calls the model handler."""
        # Setup mocks
        mock_config = Mock()
        mock_config.get.side_effect = lambda k: (
            "default" if k == "theme_name" else "gpt-4"
        )
        mock_get_config.return_value = mock_config

        mock_theme_manager = Mock()
        mock_theme_manager.current_theme = "default"
        mock_get_theme.return_value = mock_theme_manager

        mock_get_keys.return_value = {}

        # Mock radiolist for main menu only
        with patch("aura_cli.cli.key_manager.radiolist_dialog") as mock_radio:
            mock_radio_instance = Mock()
            mock_radio.return_value = mock_radio_instance

            # Sequence: Select 'model' -> then loop -> Select 'exit'
            mock_radio_instance.run.side_effect = ["model", "exit"]

            show_settings_menu()

            # Verify handler was called
            mock_handle_model.assert_called_once()


def test_settings_dialog_wrapper_applies_graphite_style():
    """Every prompt-toolkit settings screen inherits the modal visual contract."""
    with patch("aura_cli.cli.key_manager._radiolist_dialog") as dialog:
        from aura_cli.cli.key_manager import radiolist_dialog

        radiolist_dialog(title="Settings", text="Choose", values=[])

    kwargs = dialog.call_args.kwargs
    assert kwargs["style"] is not None
    assert "#15181d" in repr(kwargs["style"].style_rules)
