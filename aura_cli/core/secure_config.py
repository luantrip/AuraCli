"""Secure configuration management for Aura CLI.

API keys are stored in the OS keyring (macOS Keychain, Windows Credential
Manager, Linux Secret Service) and never written to disk in plain text unless
explicitly opted in. Config file lives at ~/.aura/config.json with None
placeholders for keyring-backed keys. Global singleton via get_config().
"""

from copy import deepcopy
import os
from pathlib import Path
import threading
from typing import Any, ClassVar, Dict, Optional

import keyring

from aura_cli.core.config import BaseConfigManager
from aura_cli.core.logger import get_logger
from aura_cli.core.paths import get_aura_home
from aura_cli.core.reliability.profiles import ProfileStore, validate_profile_name

logger = get_logger(__name__)

CONFIG_DIR = get_aura_home()
CONFIG_FILE = CONFIG_DIR / "config.json"
KEYRING_SERVICE = "aura_cli"

try:
    from aura_cli.core.llm.model_utils import DEFAULT_MODEL as _DEFAULT_MODEL
except ImportError:
    _DEFAULT_MODEL = "cerebras/gpt-oss-120b"

DEFAULT_CONFIG = {
    "default_model": _DEFAULT_MODEL,
    "api_keys": {
        "google_api_key": None,
        "openai_api_key": None,
        "anthropic_api_key": None,
        "openrouter_api_key": None,  # OpenRouter (13+ free models)
        "nvidia_api_key": None,  # NVIDIA API Catalog (nvapi-...)
        "cerebras_api_key": None,  # Cerebras (fast inference)
        "groq_api_key": None,  # GroqCloud (free tier)
    },
    "auto_confirm_tools": False,
    "use_keyring": True,
    "allow_insecure_key_storage": False,
}


class InsecureKeyStorageDisabledError(RuntimeError):
    """Raised when keyring fails and plaintext storage was not explicitly allowed."""


class SecureConfig(BaseConfigManager):
    """Manages API keys using the OS keyring with plaintext fallback."""

    _logged: ClassVar[bool] = False

    def __init__(
        self,
        path: Optional[Path] = None,
        *,
        allow_insecure_file_storage: Optional[bool] = None,
        profile: Optional[str] = None,
    ):
        """Initialize the instance."""
        self.profile = validate_profile_name(profile or os.environ.get("AURA_PROFILE", "default"))
        if path is None:
            path = CONFIG_FILE
            if self.profile != "default":
                profile_store = ProfileStore(get_aura_home() / "profiles")
                path = profile_store.path_for(self.profile).parent / "config.json"
        self.path = Path(path) if not isinstance(path, Path) else path
        self.keyring_service = (
            KEYRING_SERVICE if self.profile == "default" else f"{KEYRING_SERVICE}:{self.profile}"
        )
        # BaseConfigManager may save defaults during initialization, so these
        # fields must exist before calling it.
        self._allow_insecure_file_storage = bool(allow_insecure_file_storage)
        self._use_keyring = not self._allow_insecure_file_storage
        super().__init__(self.path, deepcopy(DEFAULT_CONFIG))
        configured_opt_in = bool(self.data.get("allow_insecure_key_storage", False))
        self._allow_insecure_file_storage = (
            configured_opt_in
            if allow_insecure_file_storage is None
            else allow_insecure_file_storage
        )
        self._use_keyring = not self._allow_insecure_file_storage
        self.data["use_keyring"] = self._use_keyring
        self.data["allow_insecure_key_storage"] = self._allow_insecure_file_storage

        if not SecureConfig._logged:
            logger.info(f"SecureConfig initialized (keyring: {self._use_keyring})")
            SecureConfig._logged = True

    def _prepare_data_for_save(self) -> Dict[str, Any]:
        """
        Prepare data for saving, removing API keys if using keyring.

        Returns:
            Dictionary ready to be saved
        """
        data_to_save = self.data.copy()
        data_to_save["api_keys"] = self.data.get("api_keys", {}).copy()
        data_to_save["use_keyring"] = self._use_keyring
        data_to_save["allow_insecure_key_storage"] = self._allow_insecure_file_storage
        return data_to_save

    def save(self) -> None:
        """Persist configuration and restrict it to the current OS user."""
        super().save()
        try:
            self.path.chmod(0o600)
        except OSError as exc:
            logger.warning(
                f"Não foi possível restringir permissões de {self.path}: {exc}"
            )

    def get_api_key(self, provider: str) -> Optional[str]:
        """Return the API key for a provider from the keyring."""
        key_name = f"{provider}_api_key"

        if self._use_keyring:
            try:
                key = keyring.get_password(self.keyring_service, key_name)
                if key:
                    logger.debug(f"Chave de API {provider} recuperada do keyring")
                    return key
            except Exception as e:
                logger.warning(f"Error accessing keyring: {e}")

        legacy_key = self.data.get("api_keys", {}).get(key_name)
        if legacy_key and self._use_keyring:
            try:
                keyring.set_password(self.keyring_service, key_name, legacy_key)
                if keyring.get_password(self.keyring_service, key_name) == legacy_key:
                    self.data["api_keys"][key_name] = None
                    self.save()
                    logger.info(f"Chave legada de {provider} migrada para o keyring")
            except Exception as exc:
                # Preserve the legacy value when migration cannot be verified.
                logger.warning(f"Migração automática de {provider} adiada: {exc}")
        return legacy_key

    def set_api_key(self, provider: str, api_key: str) -> None:
        """Store an API key for a provider in the keyring."""
        key_name = f"{provider}_api_key"

        if self._use_keyring:
            try:
                keyring.set_password(self.keyring_service, key_name, api_key)
                logger.info(f"Chave de API {provider} armazenada no keyring")
                if "api_keys" in self.data and key_name in self.data["api_keys"]:
                    self.data["api_keys"][key_name] = None
                    self.save()
                return
            except Exception as e:
                logger.error(f"Error saving to keyring: {e}")
                if not self._allow_insecure_file_storage:
                    raise InsecureKeyStorageDisabledError(
                        "Keyring indisponível; armazenamento inseguro em arquivo "
                        "não foi autorizado."
                    ) from e

        if not self._allow_insecure_file_storage:
            raise InsecureKeyStorageDisabledError(
                "Armazenamento inseguro em arquivo não foi autorizado."
            )
        if "api_keys" not in self.data:
            self.data["api_keys"] = {}
        self.data["api_keys"][key_name] = api_key
        self.save()
        if not getattr(self, "_file_storage_warned", None):
            self._file_storage_warned: set[str] = set()
        if provider not in self._file_storage_warned:
            self._file_storage_warned.add(provider)
            warning_msg = (
                f"⚠️  Chave de API {provider} armazenada em arquivo (não seguro). "
                "Use keyring para segurança."
            )
            logger.warning(warning_msg)
            from rich.console import Console

            Console().print(f"[yellow]{warning_msg}[/yellow]")

    def delete_api_key(self, provider: str) -> None:
        """Delete the API key for a provider from the keyring."""
        key_name = f"{provider}_api_key"

        try:
            keyring.delete_password(self.keyring_service, key_name)
            logger.info(f"Chave de API {provider} removida do keyring")
        except Exception as e:
            # "Item not found" is expected when key no longer exists
            error_str = str(e).lower()
            if "item not found" in error_str or "-25300" in error_str:
                logger.debug(
                    f"Chave {provider} não encontrada no keyring (já removida ou nunca existiu)"
                )
            else:
                logger.warning(f"Error removing from keyring: {e}")

        if "api_keys" in self.data and key_name in self.data["api_keys"]:
            self.data["api_keys"][key_name] = None
            self.save()

    def migrate_keys_to_keyring(self) -> int:
        """Migrate plaintext API keys from config to the keyring."""
        migrated = 0
        api_keys = self.data.get("api_keys", {})

        for provider, key in api_keys.items():
            if key and provider.endswith("_api_key"):
                provider_name = provider.replace("_api_key", "")
                try:
                    keyring.set_password(self.keyring_service, provider, key)
                    stored_key = keyring.get_password(self.keyring_service, provider)
                    if stored_key != key:
                        raise RuntimeError("keyring não confirmou a chave persistida")
                    self.data["api_keys"][provider] = None
                    migrated += 1
                    logger.info(f"Chave {provider_name} migrada para keyring")
                except Exception as e:
                    logger.error(f"Error migrating key {provider_name}: {e}")

        if migrated > 0:
            self.save()

        return migrated


_secure_config_instance: Optional[SecureConfig] = None
_secure_config_lock = threading.Lock()


class _LazySecureConfig:
    """Compatibility proxy that avoids filesystem access during imports."""

    def _instance(self) -> SecureConfig:
        global _secure_config_instance
        active_profile = os.environ.get("AURA_PROFILE", "default")
        if _secure_config_instance is None or _secure_config_instance.profile != active_profile:
            with _secure_config_lock:
                if _secure_config_instance is None or _secure_config_instance.profile != active_profile:
                    _secure_config_instance = SecureConfig(profile=active_profile)
        return _secure_config_instance

    def __getattr__(self, name: str) -> Any:
        return getattr(self._instance(), name)


secure_config_manager = _LazySecureConfig()
