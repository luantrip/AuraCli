"""
Testes para Migração de Configurações do Aura CLI.

Este módulo contém testes que verificam o funcionamento do sistema de migração
de configurações do formato antigo (dicionário simples) para o novo formato
baseado em Pydantic. Garante compatibilidade retroativa e migração automática.

Componentes Testados:
    - AppSettings: Configurações baseadas em Pydantic
    - ConfigCompat: Camada de compatibilidade com formato antigo
    - Migração Automática: Conversão de formato antigo para novo

Cenários de Teste:
    - Migração de API Keys: Conversão de google_api_key → api_keys.google
    - Preservação de Campos Extras: Campos customizados são mantidos
    - Compatibilidade Retroativa: ConfigCompat mantém interface antiga
    - Set/Get Genérico: ConfigCompat permite set/get de chaves genéricas
    - Preservação Completa: Todas as configurações são preservadas

Validações:
    - API keys são migradas corretamente
    - Campos extras são preservados
    - ConfigCompat funciona com interface antiga
    - Chaves genéricas podem ser setadas/obtidas
    - Todas as configurações são preservadas na migração

Estrutura de Testes:
    - TestConfigMigration: Classe principal de testes

Formato Antigo:
    ```json
    {
        "api_keys": {
            "google_api_key": "key",
            "openai_api_key": "key"
        }
    }
    ```

Formato Novo:
    ```json
    {
        "api_keys": {
            "google": "key",
            "openai": "key"
        }
    }
    ```

Migração Automática:
    O sistema detecta formato antigo e migra automaticamente:
    1. Carrega configuração antiga
    2. Converte para formato novo
    3. Salva no formato novo
    4. Remove formato antigo

ConfigCompat:
    Camada de compatibilidade que:
    - Mantém interface antiga (get_api_key, etc.)
    - Converte entre formatos automaticamente
    - Permite acesso a campos extras
    - Suporta set/get genérico

Exemplo de Uso:
    ```python
    def test_migration():
        # Cria config antigo
        old_config = {"api_keys": {"google_api_key": "key"}}

        # Carrega (migra automaticamente)
        settings = AppSettings.load()
        assert settings.api_keys.google == "key"
    ```

Dependências:
    - pytest: Framework de testes
    - tempfile: Para criação de arquivos temporários
    - config: Sistema de configuração (AppSettings + ConfigCompat)
"""

import json

from aura_cli.core.config import AppSettings, ConfigCompat


class TestConfigMigration:
    """Testes para migração de configurações."""

    def test_migrate_old_format_api_keys(self, tmp_path, monkeypatch):
        """Testa migração de formato antigo de API keys para novo formato."""
        # Cria arquivo de configuração no formato antigo
        old_config = {
            "default_model": "gemini/gemini-1.5-flash-latest",
            "auto_mode": False,
            "api_keys": {
                "google_api_key": "test_google_key_123",
                "openai_api_key": "test_openai_key_456",
                "anthropic_api_key": "test_anthropic_key_789",
            },
        }

        # Temporariamente muda o CONFIG_FILE para o diretório temporário
        test_config_file = tmp_path / "config.json"
        monkeypatch.setattr(
            "aura_cli.core.config._PYDANTIC_CONFIG_FILE", str(test_config_file)
        )

        # Escreve configuração antiga
        with open(test_config_file, "w") as f:
            json.dump(old_config, f, indent=2)

        # Carrega usando novo sistema (deve migrar automaticamente)
        settings = AppSettings.load()

        # Verifica se as chaves foram migradas corretamente
        assert settings.api_keys.google == "test_google_key_123"
        assert settings.api_keys.openai == "test_openai_key_456"
        assert settings.api_keys.anthropic == "test_anthropic_key_789"

        # Verifica se outros campos foram preservados
        assert settings.default_model == "gemini/gemini-1.5-flash-latest"
        assert settings.auto_mode is False

        # Verifica se o arquivo foi salvo no novo formato
        with open(test_config_file) as f:
            saved_config = json.load(f)

        # Verifica que o formato novo foi salvo
        assert "api_keys" in saved_config
        assert "google" in saved_config["api_keys"]
        assert "openai" in saved_config["api_keys"]
        assert "anthropic" in saved_config["api_keys"]
        # Verifica que formato antigo não está mais presente
        assert "google_api_key" not in saved_config["api_keys"]
        assert "openai_api_key" not in saved_config["api_keys"]
        assert "anthropic_api_key" not in saved_config["api_keys"]

    def test_migrate_with_extra_fields(self, tmp_path, monkeypatch):
        """Testa migração preservando campos extras."""
        # Cria configuração com campos extras
        old_config = {
            "default_model": "gemini/gemini-1.5-flash-latest",
            "auto_mode": True,
            "api_keys": {
                "google_api_key": "test_key",
            },
            "custom_field": "custom_value",
            "another_field": 123,
        }

        test_config_file = tmp_path / "config.json"
        monkeypatch.setattr(
            "aura_cli.core.config._PYDANTIC_CONFIG_FILE", str(test_config_file)
        )

        with open(test_config_file, "w") as f:
            json.dump(old_config, f, indent=2)

        # Carrega e verifica que campos extras são preservados
        settings = AppSettings.load()

        # Campos principais
        assert settings.default_model == "gemini/gemini-1.5-flash-latest"
        assert settings.auto_mode is True

        # Campos extras devem estar acessíveis
        assert hasattr(settings, "custom_field")
        assert settings.custom_field == "custom_value"
        assert hasattr(settings, "another_field")
        assert settings.another_field == 123

    def test_config_compat_backward_compatibility(self, tmp_path, monkeypatch):
        """Testa que ConfigCompat mantém compatibilidade com interface antiga."""
        test_config_file = tmp_path / "config.json"

        # Cria configuração no formato antigo
        old_config = {
            "default_model": "gemini/gemini-2.0-flash-exp",
            "auto_mode": True,
            "api_keys": {
                "google_api_key": "old_google_key",
                "openai_api_key": "old_openai_key",
            },
        }

        with open(test_config_file, "w") as f:
            json.dump(old_config, f, indent=2)

        # Cria AppSettings diretamente usando o arquivo temporário
        # Simulando o que AppSettings.load() faria
        from aura_cli.core.config import AppSettings

        # Monkeypatch temporariamente o CONFIG_FILE
        original_config_file = None
        try:
            import aura_cli.core.config as config_module

            original_config_file = config_module._PYDANTIC_CONFIG_FILE
            config_module._PYDANTIC_CONFIG_FILE = str(test_config_file)

            # Carrega usando o arquivo temporário
            test_settings = AppSettings.load()
            compat = ConfigCompat()
            compat._settings = test_settings

            # Testa get() com chaves antigas
            assert compat.get("default_model") == "gemini/gemini-2.0-flash-exp"
            # auto_mode deprecated -> always False
            assert compat.get("auto_mode") is False

            # Testa get_api_key() com formato antigo
            assert compat.get_api_key("google") == "old_google_key"
            assert compat.get_api_key("openai") == "old_openai_key"

            # Testa get("api_keys") retorna formato antigo
            api_keys_dict = compat.get("api_keys")
            assert isinstance(api_keys_dict, dict)
            assert api_keys_dict["google_api_key"] == "old_google_key"
            assert api_keys_dict["openai_api_key"] == "old_openai_key"
        finally:
            # Restaura CONFIG_FILE original
            if original_config_file:
                config_module._PYDANTIC_CONFIG_FILE = original_config_file

    def test_config_compat_set_and_get_generic_keys(self, tmp_path, monkeypatch):
        """Testa que ConfigCompat pode setar e obter chaves genéricas."""
        test_config_file = tmp_path / "config.json"
        monkeypatch.setattr(
            "aura_cli.core.config._PYDANTIC_CONFIG_FILE", str(test_config_file)
        )

        compat = ConfigCompat()

        # Testa set/get de chave genérica
        compat.set("test_key", "test_value")
        assert compat.get("test_key") == "test_value"

        # Verifica que foi salvo no arquivo
        with open(test_config_file) as f:
            saved = json.load(f)
        assert saved.get("test_key") == "test_value"

    def test_migration_preserves_all_settings(self, tmp_path, monkeypatch):
        """Testa que todas as configurações são preservadas na migração."""
        # Configuração completa no formato antigo
        old_config = {
            "default_model": "claude-sonnet-4-5",
            "auto_mode": False,
            "auto_mode_prefer_local": True,
            "api_keys": {
                "google_api_key": "key1",
                "openai_api_key": "key2",
                "anthropic_api_key": "key3",
            },
            "auto_confirm_tools": True,  # Campo extra
        }

        test_config_file = tmp_path / "config.json"
        monkeypatch.setattr(
            "aura_cli.core.config._PYDANTIC_CONFIG_FILE", str(test_config_file)
        )

        with open(test_config_file, "w") as f:
            json.dump(old_config, f, indent=2)

        # Carrega
        settings = AppSettings.load()

        # Verifica todos os campos principais
        assert settings.default_model == "claude-sonnet-4-5"
        assert settings.auto_mode is False
        assert settings.auto_mode_prefer_local is True

        # Verifica API keys migradas
        assert settings.api_keys.google == "key1"
        assert settings.api_keys.openai == "key2"
        assert settings.api_keys.anthropic == "key3"

        # Verifica campo extra preservado
        assert hasattr(settings, "auto_confirm_tools")
        assert settings.auto_confirm_tools is True
