"""Tests for provider coverage in the TUI settings panel."""

from unittest.mock import Mock, patch

from aura_cli.tui.widgets.settings_panel import LLMSettings, LLMSettingsPanel


def test_settings_panel_exposes_nvidia_provider():
    """NVIDIA should be configurable from the TUI settings panel."""
    assert "nvidia" in LLMSettingsPanel.PROVIDERS


def test_settings_panel_keeps_google_and_openrouter_provider_options():
    """The TUI should expose the same major remote providers as the CLI."""
    assert "google" in LLMSettingsPanel.PROVIDERS
    assert "openrouter" in LLMSettingsPanel.PROVIDERS


def test_settings_panel_provider_catalog_is_derived_from_central_presets():
    """The TUI catalog should mirror the central provider presets."""
    assert LLMSettingsPanel.PROVIDERS["google"][0] == "gemini/gemini-2.5-flash"
    assert LLMSettingsPanel.PROVIDERS["openai"][0] == "gpt-4o"
    assert LLMSettingsPanel.PROVIDERS["anthropic"][0] == "claude-sonnet-4-6"


def test_settings_panel_exposes_only_basic_canonical_scope():
    """The TUI settings panel should stay scoped to basic canonical LLM config."""
    assert LLMSettingsPanel.CANONICAL_SCOPE == ("provider", "model", "api_key")


@patch("aura_cli.tui.widgets.settings_panel.get_api_keys_dict")
@patch("aura_cli.tui.widgets.settings_panel.get_config_manager")
def test_settings_panel_loads_initial_settings_from_canonical_config(
    mock_get_config_manager, mock_get_api_keys_dict
):
    """Without explicit settings, the panel should hydrate from canonical config."""
    google_model = "gemini/gemini-2.5-flash"
    mock_config = Mock()
    mock_config.get.return_value = google_model
    mock_get_config_manager.return_value = mock_config
    mock_get_api_keys_dict.return_value = {"GOOGLE_API_KEY": "goog-test"}

    panel = LLMSettingsPanel()

    assert panel.settings.provider == "google"
    assert panel.settings.model == google_model
    assert panel.settings.api_key == "goog-test"


@patch("aura_cli.tui.widgets.settings_panel.set_api_key_for_provider")
@patch("aura_cli.tui.widgets.settings_panel.get_config_manager")
def test_settings_panel_persists_through_canonical_config(
    mock_get_config_manager, mock_set_key
):
    """Saving from the TUI should use the same config path as the CLI."""
    mock_config = Mock()
    mock_get_config_manager.return_value = mock_config

    settings = LLMSettings(
        provider="nvidia",
        model="openai/nvidia/llama-3.3-nemotron-super-49b-v1",
        api_key="nv-test",
    )

    LLMSettingsPanel.persist_settings(settings)

    mock_config.set.assert_called_once_with("default_model", settings.model)
    mock_set_key.assert_called_once_with("nvidia", "nv-test")
