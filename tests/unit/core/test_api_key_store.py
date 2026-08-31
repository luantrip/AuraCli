"""Tests for centralized API key store."""

from unittest.mock import MagicMock, patch

from aura_cli.core.api_key_store import (
    clear_api_key_for_provider,
    set_api_key_for_provider,
)


@patch("aura_cli.core.api_key_store.clear_env_keys_for_provider")
@patch("aura_cli.core.config.ConfigCompat")
@patch("aura_cli.core.secure_config.secure_config_manager")
def test_clear_api_key_calls_all_backends(mock_secure, mock_compat_cls, mock_clear_env):
    compat = MagicMock()
    mock_compat_cls.return_value = compat

    clear_api_key_for_provider("google")

    mock_secure.delete_api_key.assert_called_once_with("google")
    compat.set_api_key.assert_called_once_with("google", None)
    mock_clear_env.assert_called_once_with("google")


@patch("aura_cli.core.api_key_store.clear_api_key_for_provider")
def test_set_empty_key_clears(mock_clear):
    set_api_key_for_provider("openai", "   ")
    mock_clear.assert_called_once_with("openai")


@patch("aura_cli.core.api_key_store.clear_env_keys_for_provider")
@patch("aura_cli.core.config.ConfigCompat")
def test_set_api_key_persists(mock_compat_cls, mock_clear_env):
    compat = MagicMock()
    mock_compat_cls.return_value = compat

    set_api_key_for_provider("anthropic", "sk-test")

    compat.set_api_key.assert_called_once_with("anthropic", "sk-test")
    mock_clear_env.assert_called_once_with("anthropic")
