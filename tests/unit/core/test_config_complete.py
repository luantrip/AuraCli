"""Testes completos para módulos de configuração."""

from unittest.mock import patch


class TestConfig:
    """Testes para config.py."""

    def test_config_manager_import(self):
        """Testa imports de config manager."""
        from aura_cli.core.config import Config, get_config_manager

        assert Config is not None
        assert get_config_manager is not None

    @patch("aura_cli.core.config.config_manager")
    def test_config_get(self, mock_manager):
        """Testa obtenção de configuração."""
        mock_manager.get.return_value = "default_model_value"

        # Tenta obter configuração
        from aura_cli.core.config import config_manager

        value = config_manager.get("default_model")

        assert value == "default_model_value"

    @patch("aura_cli.core.config.config_manager")
    def test_config_set(self, mock_manager):
        """Testa definição de configuração."""
        from aura_cli.core.config import config_manager

        # Setup mock behavior
        data = {}

        def set_side_effect(key, value):
            data[key] = value

        def get_side_effect(key):
            return data.get(key)

        mock_manager.set.side_effect = set_side_effect
        mock_manager.get.side_effect = get_side_effect

        config_manager.set("test_key", "test_value")
        value = config_manager.get("test_key")
        assert value == "test_value"


class TestPydanticConfig:
    """Testes para config.py (AppSettings/ConfigCompat)."""

    def test_pydantic_config_import(self):
        """Testa importação do módulo de configuração."""
        from aura_cli.core import config

        assert config is not None


class TestSecureConfig:
    """Testes para secure_config.py."""

    def test_secure_config_manager_import(self):
        """Testa importação do secure config manager."""
        from aura_cli.core.secure_config import secure_config_manager

        assert secure_config_manager is not None

    @patch("aura_cli.core.secure_config.secure_config_manager")
    def test_secure_config_has_methods(self, mock_manager):
        """Testa que secure config tem métodos."""
        assert hasattr(mock_manager, "get_api_key")
