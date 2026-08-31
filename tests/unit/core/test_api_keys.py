"""Testes para core/api_keys.py — TEST-NEW-01."""

import os
from unittest.mock import patch

from aura_cli.core.api_keys import get_api_keys_dict


class TestGetApiKeysDict:
    def test_returns_dict(self):
        result = get_api_keys_dict()
        assert isinstance(result, dict)

    def test_env_fallback(self):
        with (
            patch("aura_cli.core.config.ConfigCompat") as mock_compat,
            patch("aura_cli.core.secure_config.secure_config_manager") as mock_sc,
            patch.dict(os.environ, {"GOOGLE_API_KEY": "test-key-123"}, clear=True),
        ):
            mock_compat.return_value.get_api_key.return_value = None
            mock_sc.get_api_key.return_value = None
            result = get_api_keys_dict()
        assert result.get("GOOGLE_API_KEY") == "test-key-123"

    def test_google_gemini_alias_symmetric(self):
        """Se GOOGLE_API_KEY existe, GEMINI_API_KEY deve ser igual e vice-versa."""
        with (
            patch("aura_cli.core.config.ConfigCompat") as mock_compat,
            patch("aura_cli.core.secure_config.secure_config_manager") as mock_sc,
            patch.dict(os.environ, {"GOOGLE_API_KEY": "gkey"}, clear=True),
        ):
            mock_compat.return_value.get_api_key.return_value = None
            mock_sc.get_api_key.return_value = None
            result = get_api_keys_dict()
        assert result.get("GOOGLE_API_KEY") == "gkey"
        assert result.get("GEMINI_API_KEY") == "gkey"

    def test_pydantic_config_failure_falls_back(self):
        """Falha no config não deve lançar exceção."""
        import builtins

        real_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "aura_cli.core.config":
                raise ImportError("mocked")
            return real_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=mock_import):
            result = get_api_keys_dict()
        assert isinstance(result, dict)

    def test_secure_config_failure_falls_back(self):
        """Falha no SecureConfig não deve lançar exceção."""
        import builtins

        real_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if "secure_config" in name:
                raise ImportError("mocked")
            return real_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=mock_import):
            result = get_api_keys_dict()
        assert isinstance(result, dict)

    def test_openai_key_from_env(self):
        with (
            patch("aura_cli.core.config.ConfigCompat") as mock_compat,
            patch("aura_cli.core.secure_config.secure_config_manager") as mock_sc,
            patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test"}, clear=True),
        ):
            mock_compat.return_value.get_api_key.return_value = None
            mock_sc.get_api_key.return_value = None
            result = get_api_keys_dict()
        assert result.get("OPENAI_API_KEY") == "sk-test"

    def test_anthropic_key_from_env(self):
        with (
            patch("aura_cli.core.config.ConfigCompat") as mock_compat,
            patch("aura_cli.core.secure_config.secure_config_manager") as mock_sc,
            patch.dict(os.environ, {"ANTHROPIC_API_KEY": "ant-test"}, clear=True),
        ):
            mock_compat.return_value.get_api_key.return_value = None
            mock_sc.get_api_key.return_value = None
            result = get_api_keys_dict()
        assert result.get("ANTHROPIC_API_KEY") == "ant-test"

    def test_no_env_returns_dict(self):
        """Sem env vars, deve retornar dict (possivelmente vazio)."""
        with patch("aura_cli.core.api_keys.os.getenv", return_value=None):
            result = get_api_keys_dict()
        assert isinstance(result, dict)
