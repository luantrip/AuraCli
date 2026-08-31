"""Secret manager for Aura CLI.

Provides secure secret storage with encryption and integration.
"""

import base64
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

# Cryptography is now essential
CRYPTOGRAPHY_AVAILABLE = True
import keyring
from rich.console import Console

from aura_cli.core.logger import get_logger
from aura_cli.core.stats import get_stats

logger = get_logger(__name__)
console = Console()


class SecretType(Enum):
    """Tipos de secret."""

    API_KEY = "api_key"
    PASSWORD = "password"
    TOKEN = "token"
    CERTIFICATE = "certificate"
    SSH_KEY = "ssh_key"
    OTHER = "other"


@dataclass
class Secret:
    """Stored secret (id, name, secret_type, value, description)."""

    id: str
    name: str
    secret_type: SecretType
    value: bytes  # Valor criptografado
    description: str = ""
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class SecretManager:
    """Manages secrets with encryption and access control."""

    def __init__(self, use_keyring: bool = True):
        """Initialise the secret manager."""
        self.use_keyring = use_keyring
        self.stats = get_stats()

        self._cipher = self._init_cipher()

        self.secrets: Dict[str, Secret] = {}

        logger.info(f"SecretManager initialized (use_keyring: {use_keyring})")

    def _get_or_create_salt(self) -> bytes:
        """
        Get or create a unique salt for this installation.

        Salt is stored in keyring for persistence across sessions.

        Returns:
            16-byte salt unique to this installation.
        """
        import secrets as secrets_module

        service_name = "aura_cli"
        salt_key = "encryption_salt"

        if self.use_keyring:
            try:
                salt_b64 = keyring.get_password(service_name, salt_key)
                if salt_b64:
                    return base64.b64decode(salt_b64)
            except Exception as _e:
                logger.debug(f"Ignorado: {_e}")

        salt = secrets_module.token_bytes(16)

        if self.use_keyring:
            try:
                keyring.set_password(
                    service_name, salt_key, base64.b64encode(salt).decode()
                )
            except Exception as _e:
                logger.debug(f"Ignorado: {_e}")

        return salt

    def _init_cipher(self) -> Optional[Fernet]:
        """Initialise the Fernet encryption cipher."""
        try:
            import secrets as secrets_module

            service_name = "aura_cli"
            key_name = "encryption_key"

            if self.use_keyring:
                try:
                    password = keyring.get_password(service_name, key_name)
                    if not password:
                        password = secrets_module.token_urlsafe(32)
                        keyring.set_password(service_name, key_name, password)
                except Exception:
                    password = secrets_module.token_urlsafe(32)
            else:
                password = secrets_module.token_urlsafe(32)

            salt = self._get_or_create_salt()

            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=100000,
            )
            key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
            return Fernet(key)

        except Exception as e:
            logger.error(f"Error initializing cipher: {e}", exc_info=True)
            return None

    def store_secret(
        self,
        name: str,
        value: str,
        secret_type: SecretType = SecretType.OTHER,
        description: str = "",
    ) -> str:
        """Store a secret (value will be encrypted)."""
        from aura_cli.core.ui import display_tool_call
        from aura_cli.core.ui_bridge import UIIcons, UIStyles

        display_tool_call("store_secret", {"name": name, "type": secret_type.value})

        import uuid

        secret_id = str(uuid.uuid4())[:8]

        encrypted_value = self._encrypt(value)

        if self.use_keyring:
            try:
                keyring.set_password("aura_cli", name, value)
            except Exception as e:
                logger.warning(f"Error storing in keyring: {e}")

        secret = Secret(
            id=secret_id,
            name=name,
            secret_type=secret_type,
            value=encrypted_value,
            description=description,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        self.secrets[secret_id] = secret

        logger.info(f"Secret '{name}' armazenado")

        console.print(
            f"[{UIStyles.SUCCESS}]{UIIcons.SUCCESS} "
            f"Secret '{name}' armazenado com sucesso[/{UIStyles.SUCCESS}]"
        )

        self.stats.track_tool_usage("secret_manager")

        return secret_id

    def get_secret(self, name: str) -> Optional[str]:
        """
        Recupera um secret.

        Args:
            name: Nome do secret

        Returns:
            Valor descriptografado ou None
        """
        if self.use_keyring:
            try:
                value = keyring.get_password("aura_cli", name)
                if value:
                    return value
            except Exception as _e:
                logger.debug(f"Ignorado: {_e}")

        for secret in self.secrets.values():
            if secret.name == name:
                return self._decrypt(secret.value)

        return None

    def delete_secret(self, name: str) -> bool:
        """
        Remove um secret.

        Args:
            name: Nome do secret

        Returns:
            True if removed
        """
        if self.use_keyring:
            try:
                keyring.delete_password("aura_cli", name)
            except Exception as _e:
                logger.debug(f"Ignorado: {_e}")

        to_remove = [sid for sid, s in self.secrets.items() if s.name == name]
        for sid in to_remove:
            del self.secrets[sid]

        if to_remove:
            logger.info(f"Secret '{name}' removed")
            return True

        return False

    def list_secrets(self) -> List[Dict[str, Any]]:
        """Return a list of all secrets without their values."""
        return [
            {
                "id": s.id,
                "name": s.name,
                "type": s.secret_type.value,
                "description": s.description,
                "created_at": s.created_at.isoformat() if s.created_at else None,
            }
            for s in self.secrets.values()
        ]

    def _encrypt(self, value: str) -> bytes:
        """
        Criptografa valor.

        Args:
            value: Valor a criptografar

        Returns:
            Valor criptografado
        """
        if self._cipher:
            return self._cipher.encrypt(value.encode())
        else:
            return base64.b64encode(value.encode())

    def _decrypt(self, encrypted_value: bytes) -> str:
        """
        Descriptografa valor.

        Args:
            encrypted_value: Valor criptografado

        Returns:
            Valor descriptografado
        """
        if self._cipher:
            return self._cipher.decrypt(encrypted_value).decode()
        else:
            return base64.b64decode(encrypted_value).decode()


# Factory function for singleton pattern
_secret_manager_instance: Optional[SecretManager] = None


def get_secret_manager() -> SecretManager:
    """
    Get or create SecretManager instance (singleton).

    Returns:
        SecretManager instance
    """
    global _secret_manager_instance
    if _secret_manager_instance is None:
        _secret_manager_instance = SecretManager()
    return _secret_manager_instance
