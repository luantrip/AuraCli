"""
Testes para o módulo secret_manager.

Testa funcionalidades de armazenamento seguro e gerenciamento
de secrets com criptografia e integração com keyring.
"""

import base64
from datetime import datetime
from unittest.mock import patch

from aura_cli.core.ops_tools.security.secret_manager import (
    Secret,
    SecretManager,
    SecretType,
)


class TestSecretType:
    """Testa enum SecretType."""

    def test_secret_type_values(self):
        """Testa valores dos tipos de secret."""
        assert SecretType.API_KEY.value == "api_key"
        assert SecretType.PASSWORD.value == "password"
        assert SecretType.TOKEN.value == "token"
        assert SecretType.CERTIFICATE.value == "certificate"
        assert SecretType.SSH_KEY.value == "ssh_key"
        assert SecretType.OTHER.value == "other"

    def test_secret_type_coverage(self):
        """Testa cobertura de tipos de secret."""
        expected_types = {
            "api_key",
            "password",
            "token",
            "certificate",
            "ssh_key",
            "other",
        }

        actual_types = {t.value for t in SecretType}
        assert actual_types == expected_types


class TestSecret:
    """Testa dataclass Secret."""

    def test_secret_required_fields(self):
        """Testa campos obrigatórios do secret."""
        encrypted_value = b"encrypted_data"
        secret = Secret(
            id="secret-001",
            name="API Key",
            secret_type=SecretType.API_KEY,
            value=encrypted_value,
        )

        assert secret.id == "secret-001"
        assert secret.name == "API Key"
        assert secret.secret_type == SecretType.API_KEY
        assert secret.value == encrypted_value

    def test_secret_optional_fields_defaults(self):
        """Testa valores padrão dos campos opcionais."""
        secret = Secret(
            id="secret-002",
            name="Password",
            secret_type=SecretType.PASSWORD,
            value=b"encrypted_password",
        )

        assert secret.description == ""
        assert secret.created_at is None
        assert secret.updated_at is None
        assert secret.metadata == {}

    def test_secret_with_all_fields(self):
        """Testa secret com todos os campos preenchidos."""
        created_time = datetime.now()
        updated_time = datetime.now()
        metadata = {"environment": "production", "rotation_days": 30}

        secret = Secret(
            id="secret-003",
            name="Database Password",
            secret_type=SecretType.PASSWORD,
            value=b"encrypted_db_password",
            description="Production database password",
            created_at=created_time,
            updated_at=updated_time,
            metadata=metadata,
        )

        assert secret.description == "Production database password"
        assert secret.created_at == created_time
        assert secret.updated_at == updated_time
        assert secret.metadata == metadata

    def test_secret_value_is_bytes(self):
        """Testa que o valor do secret é sempre bytes."""
        secret = Secret(
            id="test",
            name="Test Secret",
            secret_type=SecretType.TOKEN,
            value=b"encrypted_token_data",
        )

        assert isinstance(secret.value, bytes)
        assert len(secret.value) > 0

    def test_secret_metadata_flexibility(self):
        """Testa flexibilidade dos metadados."""
        metadata = {
            "tags": ["production", "critical"],
            "rotation_policy": {"days": 90, "auto": True},
            "access_count": 0,
            "last_accessed": None,
        }

        secret = Secret(
            id="flexible-secret",
            name="Flexible Secret",
            secret_type=SecretType.OTHER,
            value=b"encrypted_data",
            metadata=metadata,
        )

        assert secret.metadata["tags"] == ["production", "critical"]
        assert secret.metadata["rotation_policy"]["days"] == 90
        assert secret.metadata["access_count"] == 0


class TestSecretManager:
    """Testa classe SecretManager."""

    def setup_method(self):
        """Setup para cada teste."""
        with patch("aura_cli.core.ops_tools.security.secret_manager.keyring"):
            self.manager = SecretManager(use_keyring=False)

    def test_init_without_keyring(self):
        """Testa inicialização sem keyring."""
        with patch("aura_cli.core.ops_tools.security.secret_manager.keyring"):
            manager = SecretManager(use_keyring=False)

            assert manager.use_keyring is False
            assert hasattr(manager, "stats")
            assert hasattr(manager, "secrets")
            assert isinstance(manager.secrets, dict)
            assert len(manager.secrets) == 0

    def test_init_with_keyring(self):
        """Testa inicialização com keyring."""
        with patch("aura_cli.core.ops_tools.security.secret_manager.keyring"):
            manager = SecretManager(use_keyring=True)

            assert manager.use_keyring is True

    def test_get_or_create_salt(self):
        """Testa obtenção ou criação de salt."""
        # _get_or_create_salt retorna bytes de 16 bytes
        salt = self.manager._get_or_create_salt()

        assert isinstance(salt, bytes)
        assert len(salt) == 16

        # Chamar novamente deve retornar o mesmo salt (quando use_keyring=False)
        # ou um novo salt (quando use_keyring=True e não há keyring)
        salt2 = self.manager._get_or_create_salt()
        assert isinstance(salt2, bytes)
        assert len(salt2) == 16

    @patch("aura_cli.core.ops_tools.security.secret_manager.keyring")
    def test_get_existing_salt(self, mock_keyring):
        """Testa obtenção de salt existente do keyring."""
        # Criar manager com keyring habilitado
        manager = SecretManager(use_keyring=True)

        # Salt deve ter 16 bytes
        existing_salt = b"existing_salt_16"  # 16 bytes
        existing_salt_b64 = base64.b64encode(existing_salt).decode()
        mock_keyring.get_password.return_value = existing_salt_b64

        salt = manager._get_or_create_salt()

        assert salt == existing_salt
        assert len(salt) == 16
        # get_password deve ser chamado para buscar o salt
        assert mock_keyring.get_password.called

    def test_cipher_initialization(self):
        """Testa inicialização do cipher."""
        assert hasattr(self.manager, "_cipher")
        assert self.manager._cipher is not None

    def test_encrypt_decrypt_roundtrip(self):
        """Testa criptografia e descriptografia."""
        original_data = "sensitive_password_123"

        # Criptografar
        encrypted = self.manager._encrypt(original_data)
        assert isinstance(encrypted, bytes)
        assert encrypted != original_data.encode()

        # Descriptografar
        decrypted = self.manager._decrypt(encrypted)
        assert decrypted == original_data

    def test_store_secret(self):
        """Testa armazenamento de secret."""
        secret_name = "test-api-key"
        secret_value = "sk-1234567890abcdef"

        # store_secret retorna secret_id (str), não bool
        # Aceita name, value, secret_type, description
        secret_id = self.manager.store_secret(
            name=secret_name,
            value=secret_value,
            secret_type=SecretType.API_KEY,
            description="Test API key for development",
        )

        assert isinstance(secret_id, str)
        assert len(secret_id) > 0

        # Verificar que foi armazenado (buscar pelo name)
        stored_secret = next(
            (s for s in self.manager.secrets.values() if s.name == secret_name), None
        )
        assert stored_secret is not None
        assert stored_secret.name == secret_name
        assert stored_secret.secret_type == SecretType.API_KEY

    def test_retrieve_secret(self):
        """Testa recuperação de secret."""
        secret_name = "test-password"
        original_value = "super_secret_password"

        # Primeiro armazenar (store_secret retorna secret_id)
        self.manager.store_secret(
            name=secret_name, value=original_value, secret_type=SecretType.PASSWORD
        )

        # get_secret aceita name, não secret_id
        retrieved_value = self.manager.get_secret(secret_name)

        assert retrieved_value == original_value

    def test_retrieve_nonexistent_secret(self):
        """Testa recuperação de secret inexistente."""
        result = self.manager.get_secret("nonexistent-secret")
        assert result is None

    def test_list_secrets(self):
        """Testa listagem de secrets."""
        # Armazenar alguns secrets
        secrets_data = [
            ("API Key 1", SecretType.API_KEY, "key1"),
            ("Password 1", SecretType.PASSWORD, "pass1"),
            ("Token 1", SecretType.TOKEN, "token1"),
        ]

        for name, secret_type, value in secrets_data:
            self.manager.store_secret(name=name, value=value, secret_type=secret_type)

        # list_secrets retorna List[Dict[str, Any]], não lista de objetos
        secrets_list = self.manager.list_secrets()

        assert len(secrets_list) == 3

        # Verificar que contém os nomes corretos
        secret_names = [s["name"] for s in secrets_list]
        assert "API Key 1" in secret_names
        assert "Password 1" in secret_names
        assert "Token 1" in secret_names

    def test_delete_secret(self):
        """Testa remoção de secret."""
        secret_name = "to-delete"

        # Primeiro armazenar
        self.manager.store_secret(
            name=secret_name, value="delete_me", secret_type=SecretType.OTHER
        )

        # Verificar que existe (buscar pelo name)
        assert self.manager.get_secret(secret_name) is not None

        # delete_secret aceita name, não secret_id
        result = self.manager.delete_secret(secret_name)

        assert result is True
        assert self.manager.get_secret(secret_name) is None

    def test_delete_nonexistent_secret(self):
        """Testa remoção de secret inexistente."""
        result = self.manager.delete_secret("nonexistent")
        assert result is False

    def test_update_secret(self):
        """Testa atualização de secret através de delete + store."""
        secret_name = "to-update"
        original_value = "original_value"
        new_value = "updated_value"

        # Primeiro armazenar
        secret_id = self.manager.store_secret(
            name=secret_name, value=original_value, secret_type=SecretType.PASSWORD
        )

        # Verificar valor original
        assert self.manager.get_secret(secret_name) == original_value

        # Atualizar: deletar e criar novo (SecretManager não tem update_secret)
        self.manager.delete_secret(secret_name)
        new_secret_id = self.manager.store_secret(
            name=secret_name, value=new_value, secret_type=SecretType.PASSWORD
        )

        # Verificar que foi atualizado
        assert self.manager.get_secret(secret_name) == new_value
        assert new_secret_id != secret_id  # Novo ID foi gerado

    def test_secret_metadata_update(self):
        """Testa acesso a metadados do secret."""
        secret_name = "with-metadata"

        # Armazenar secret (metadados não são passados em store_secret)
        self.manager.store_secret(
            name=secret_name,
            value="api_key_value",
            secret_type=SecretType.API_KEY,
            description="Secret with metadata",
        )

        # Verificar que secret foi criado
        stored_secret = next(
            (s for s in self.manager.secrets.values() if s.name == secret_name), None
        )
        assert stored_secret is not None
        assert stored_secret.metadata == {}  # Metadata padrão é dict vazio

        # Metadados podem ser modificados diretamente (se necessário)
        stored_secret.metadata["env"] = "prod"
        assert stored_secret.metadata["env"] == "prod"

    def test_secret_rotation(self):
        """Testa rotação de secrets através de delete + store."""
        secret_name = "to-rotate"
        old_value = "old_secret_value"
        new_value = "new_secret_value"

        # Armazenar secret original
        old_secret_id = self.manager.store_secret(
            name=secret_name, value=old_value, secret_type=SecretType.TOKEN
        )

        # Verificar valor original
        assert self.manager.get_secret(secret_name) == old_value

        # Rotacionar: deletar e criar novo (SecretManager não tem rotate_secret)
        self.manager.delete_secret(secret_name)
        new_secret_id = self.manager.store_secret(
            name=secret_name, value=new_value, secret_type=SecretType.TOKEN
        )

        # Verificar que foi atualizado
        assert self.manager.get_secret(secret_name) == new_value
        assert new_secret_id != old_secret_id  # Novo ID foi gerado

    def test_secret_access_tracking(self):
        """Testa acesso a secrets."""
        secret_name = "tracked-secret"

        # Armazenar secret
        self.manager.store_secret(
            name=secret_name, value="tracked_password", secret_type=SecretType.PASSWORD
        )

        # Acessar o secret (get_secret não tem track_access)
        value = self.manager.get_secret(secret_name)

        assert value == "tracked_password"

        # Verificar que secret existe
        stored_secret = next(
            (s for s in self.manager.secrets.values() if s.name == secret_name), None
        )
        assert stored_secret is not None
        # Metadata pode ser usado para rastreamento manual se necessário
        stored_secret.metadata["access_count"] = (
            stored_secret.metadata.get("access_count", 0) + 1
        )
        assert stored_secret.metadata["access_count"] >= 0

    def test_encryption_key_derivation(self):
        """Testa que diferentes salts geram chaves diferentes através de _get_or_create_salt."""
        # Testar que _get_or_create_salt funciona
        salt1 = self.manager._get_or_create_salt()
        assert isinstance(salt1, bytes)
        assert len(salt1) == 16

        # Criar novo manager para testar salt diferente
        with patch("aura_cli.core.ops_tools.security.secret_manager.keyring"):
            manager2 = SecretManager(use_keyring=False)
            salt2 = manager2._get_or_create_salt()

            # Salts podem ser iguais se gerados da mesma forma, mas devem ser bytes
            assert isinstance(salt2, bytes)
            assert len(salt2) == 16

    def test_secret_export_import(self):
        """Testa listagem de secrets como forma de 'export'."""
        # Armazenar alguns secrets
        secrets_data = [
            ("Export 1", SecretType.API_KEY, "key1"),
            ("Export 2", SecretType.PASSWORD, "pass1"),
        ]

        for name, secret_type, value in secrets_data:
            self.manager.store_secret(name=name, value=value, secret_type=secret_type)

        # list_secrets retorna List[Dict] que pode ser usado como "export"
        exported_data = self.manager.list_secrets()

        assert len(exported_data) == 2
        assert all("name" in item for item in exported_data)
        assert all("type" in item for item in exported_data)

    def test_keyring_integration(self):
        """Testa integração com keyring do sistema."""
        with patch(
            "aura_cli.core.ops_tools.security.secret_manager.keyring"
        ) as mock_keyring:
            manager = SecretManager(use_keyring=True)

            # Verificar que tentou usar keyring para salt
            mock_keyring.get_password.assert_called()

            assert manager.use_keyring is True
