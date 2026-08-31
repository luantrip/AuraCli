"""
Configuration Management System for Aura CLI.

This module provides a Python dictionary-based configuration system
that persists data in JSON format in the user's home directory. Offers
functionality for:

- Management of default LLM model configurations
- Secure storage of API keys (Google, OpenAI, Anthropic)
- System behavior settings (auto_confirm_tools, auto_mode)
- Automatic persistence to JSON file (~/.aura/config.json)
- Intelligent merging of default configurations with existing values

Compatibility Note:
    This module maintains compatibility with the old configuration system.
    From the current version, the system internally uses the new
    Pydantic-based module (pydantic_config.py) through a compatibility
    wrapper (ConfigCompat), ensuring smooth transition without breaking
    existing code.
"""

import json
import os
from pathlib import Path
import threading
from typing import Any, ClassVar, Dict, Optional, Protocol

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from aura_cli.core.llm.model_utils import (
    DEFAULT_MODEL,
    normalize_model_name,
    resolve_model_option,
)
from aura_cli.core.paths import aura_path, get_aura_home

_logger_instance = None


def _get_logger():
    """Lazy import do logger."""
    global _logger_instance
    if _logger_instance is None:
        from aura_cli.core.logger import get_logger

        _logger_instance = get_logger(__name__)
    return _logger_instance


CONFIG_DIR = get_aura_home()
CONFIG_FILE = CONFIG_DIR / "config.json"

_DEFAULT_MODEL = DEFAULT_MODEL

VALID_PROVIDERS = frozenset(
    {
        "google",
        "openai",
        "anthropic",
        "openrouter",
        "nvidia",
        "cerebras",
        "groq",
    }
)

DEFAULT_CONFIG = {
    "default_model": _DEFAULT_MODEL,
    "api_keys": {
        "google_api_key": None,
        "openai_api_key": None,
        "anthropic_api_key": None,
        "openrouter_api_key": None,
        "nvidia_api_key": None,
        "cerebras_api_key": None,
        "groq_api_key": None,
    },
    "auto_confirm_tools": False,
    "auto_consolidation": False,
    "context_max_history_size": 100,
    "context_compression_threshold": 40,
    "context_max_tokens": 8000,
    "agi_max_tasks": 20,
    "agi_task_timeout": 60,
    "agi_max_retries": 3,
    "agi_adversarial_validation": False,
    "token_budget_warning": 100000,
    "token_budget_hard": 250000,
    "shell_default_timeout": 30,
    "shell_max_timeout": 300,
    "theme_name": "aura_minimal",
    "accessibility": {
        "enabled": False,
        "device": "auto",
        "screen_reader": None,
    },
    "show_tool_args": False,
    "show_execution_time": True,
    "log_level": "INFO",
    "log_to_file": True,
}


class BaseConfigManager:
    """
    Base class for configuration managers.

    Provides common functionality for loading, saving, and accessing
    configuration data. Subclasses can override methods to customize
    behavior (e.g., API key handling, model normalization).
    """

    def __init__(self, path: Path, default_config: Dict[str, Any]):
        """
        Initialize base configuration manager.

        Args:
            path: Path to configuration file
            default_config: Default configuration dictionary
        """
        self.path = path
        self.default_config = default_config
        self.data = self._load()

    _DEPRECATED_MODELS: ClassVar[set] = {
        # Gemini/Gemma without prefix (old format)
        "gemini-1.5-flash",
        "gemini-1.5-pro",
        "gemini-1.0-pro",
        "gemini-pro",
        "gemini-2.0-flash-thinking",
        "gemini-2.0-flash-exp",
        # Claude retired
        "claude-3-5-sonnet-20241022",
        "claude-3-5-haiku-20241022",
        "claude-3-opus-20240229",
        "claude-3-haiku-20240307",
        "claude-3-7-sonnet-20250219",
        # NVIDIA legados
        "openai/nvidia/llama-3.3-nemotron-super-49b-v1",
        "openai/nvidia/llama-3.3-nemotron-super-49b-v1.5",
    }

    def _migrate_model(self, data: dict) -> None:
        """Migrate deprecated model names in-place, saving if changed."""
        old_model = data.get("default_model")
        if not old_model or not isinstance(old_model, str):
            return

        # 1. Explicitly discontinued models → migrate to current default
        if old_model in self._DEPRECATED_MODELS:
            _get_logger().info(
                f"Migrando modelo descontinuado: {old_model} -> {_DEFAULT_MODEL}"
            )
            data["default_model"] = _DEFAULT_MODEL
            self.data = data
            self.save()
            return

        # 2. Gemini/Gemma without prefix → normalise to gemini/...
        if not old_model.startswith("gemini/") and (
            "gemini" in old_model.lower() or "gemma" in old_model.lower()
        ):
            normalized = normalize_model_name(old_model)
            if normalized != old_model:
                _get_logger().debug(
                    f"Normalizando nome do modelo: {old_model} -> {normalized}"
                )
                data["default_model"] = normalized
                self.data = data
                self.save()
            return

        # 3. Cerebras without prefix → add cerebras/ prefix
        if not old_model.startswith("cerebras/") and old_model in {
            "gpt-oss-120b",
            "zai-glm-4.7",
            "llama3.1-8b",
            "qwen-3-32b",
            "llama-3.3-70b",
        }:
            normalized = f"cerebras/{old_model}"
            _get_logger().debug(
                f"Normalizando nome do modelo Cerebras: {old_model} -> {normalized}"
            )
            data["default_model"] = normalized
            self.data = data
            self.save()

    def _load(self) -> Dict[str, Any]:
        """
        Load configuration from JSON file or create default if not exists.

        Returns:
            Dictionary with loaded and merged configuration
        """
        try:
            path_exists = self.path.exists()
        except (PermissionError, OSError):
            path_exists = False

        if not path_exists:
            _get_logger().info("Arquivo de configuração não existe, criando padrão")
            self.data = self.default_config.copy()
            try:
                self.save()
            except (PermissionError, OSError) as e:
                _get_logger().warning(
                    f"Não foi possível persistir configuração inicial em {self.path}: {e}. "
                    "Continuando com configuração em memória."
                )
            return self.data

        try:
            with open(self.path, encoding="utf-8") as f:
                data = json.load(f)

            for key, value in self.default_config.items():
                if key not in data:
                    data[key] = value
                elif isinstance(value, dict):
                    for sub_key, sub_value in value.items():
                        data[key].setdefault(sub_key, sub_value)

            # Migrate deprecated models to current versions
            if "default_model" in data:
                self._migrate_model(data)

            _get_logger().debug("Configuração carregada com sucesso")
            return data
        except json.JSONDecodeError as e:
            _get_logger().error(f"Error parsing configuration JSON: {e}")
            return self.default_config.copy()
        except PermissionError as e:
            _get_logger().error(f"Sem permissão para ler configuração: {e}")
            return self.default_config.copy()
        except OSError as e:
            _get_logger().error(f"Erro de sistema ao carregar configuração: {e}")
            return self.default_config.copy()

    def _prepare_data_for_save(self) -> Dict[str, Any]:
        """
        Prepare data dictionary for saving.

        Subclasses can override to customize save behavior
        (e.g., removing API keys when using keyring).

        Returns:
            Dictionary ready to be saved
        """
        return self.data.copy()

    def save(self) -> None:
        """
        Save configuration to JSON file.

        Raises:
            IOError: If there's an error writing the file
        """
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            data_to_save = self._prepare_data_for_save()
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump(data_to_save, f, indent=4)
            _get_logger().debug("Configuração salva com sucesso")
        except PermissionError as e:
            _get_logger().error(f"Sem permissão para salvar configuração: {e}")
            raise
        except OSError as e:
            _get_logger().error(f"Erro de sistema ao salvar configuração: {e}")
            raise

    def get(self, key: str) -> Optional[Any]:
        """
        Get configuration value by key.

        Args:
            key: Configuration key

        Returns:
            Configuration value or None if not found
        """
        return self.data.get(key)

    def set(self, key: str, value: Any) -> None:
        """
        Set configuration value and save automatically.

        Args:
            key: Configuration key
            value: Value to set
        """
        self.data[key] = value
        self.save()


class Config(BaseConfigManager):
    """Configuration manager for Aura CLI.

    Persistent JSON config stored in the user home directory. Handles
    default model resolution and delegates API key storage to SecureConfig.
    """

    def __init__(self, path: Path = CONFIG_FILE):
        """Initialize with the given config file path (default ~/.aura/config.json)."""
        super().__init__(path, DEFAULT_CONFIG)

    def get(self, key: str) -> Optional[Any]:
        """Return a config value, resolving model aliases for 'default_model'.

        Args:
            key: Configuration key.

        Returns:
            Config value or None if not set.
        """
        value = super().get(key)

        if key == "default_model" and value is not None:
            value = resolve_model_option(value)

        return value

    def set(self, key: str, value: Any) -> None:
        """Set a config value and persist to disk immediately.

        Args:
            key: Configuration key.
            value: Value to store.
        """
        if key == "default_model" and value is not None:
            value = resolve_model_option(value)

        self.data[key] = value
        self.save()

    def get_api_key(self, provider: str) -> Optional[str]:
        """Return the API key for a provider, reading from the OS keyring.

        Args:
            provider: Provider name — "google", "openai", "anthropic", etc.

        Returns:
            API key string, or None if not configured.
        """
        if provider not in VALID_PROVIDERS:
            _get_logger().warning(
                f"Invalid provider: '{provider}'. Valid: {sorted(VALID_PROVIDERS)}"
            )
            return None
        try:
            from aura_cli.core.secure_config import secure_config_manager

            return secure_config_manager.get_api_key(provider)
        except Exception:
            key_name = f"{provider}_api_key"
            return self.data.get("api_keys", {}).get(key_name)

    def set_api_key(self, provider: str, api_key: str) -> None:
        """Store an API key for the given provider in the OS keyring.

        Persists immediately to guarantee availability across sessions.
        Never falls back to plaintext storage — callers that genuinely
        need an insecure file fallback must opt in via SecureConfig.

        Args:
            provider: LLM provider name (e.g. "google", "openai", "anthropic").
            api_key: API key string obtained from the provider.

        Raises:
            ValueError: If provider is not in VALID_PROVIDERS.
            IOError: If keyring or config file write fails.
        """
        if provider not in VALID_PROVIDERS:
            raise ValueError(
                f"Invalid provider: '{provider}'. Valid: {sorted(VALID_PROVIDERS)}"
            )
        from aura_cli.core.secure_config import secure_config_manager

        # Never downgrade to plaintext storage implicitly.  Callers must opt in
        # through SecureConfig if an insecure file fallback is genuinely needed.
        secure_config_manager.set_api_key(provider, api_key)


def get_config_manager():
    """Return the global config manager instance via the DI container.

    Falls back to ConfigCompat or Config if the container is unavailable.
    Thread-safe — the container uses internal locks.
    """
    try:
        from aura_cli.core.di import Services, get_container

        container = get_container()
        if container.has(Services.CONFIG):
            return container.resolve(Services.CONFIG)
    except Exception:
        pass
    # Simple fallback (no globals needed — container handles thread safety)
    try:
        from aura_cli.core.config import ConfigCompat

        return ConfigCompat()
    except ImportError:
        return Config()


_config_manager_instance = None


def _get_config_manager_lazy():
    """Lazy getter para config_manager."""
    global _config_manager_instance
    if _config_manager_instance is None:
        _config_manager_instance = get_config_manager()
    return _config_manager_instance


class _LazyConfigManager:
    """Wrapper lazy para config_manager."""

    def __getattr__(self, name):
        """Allow attribute-style access to config values."""
        return getattr(_get_config_manager_lazy(), name)

    def __call__(self, *args, **kwargs):
        """Allow callable-style access to config values."""
        return _get_config_manager_lazy()(*args, **kwargs)


config_manager = _LazyConfigManager()


# ==========================================================================
# Pydantic-based Settings (consolidated from pydantic_config.py)
# ==========================================================================

_pydantic_logger = None


def _get_pydantic_logger():
    """Lazy import do logger para AppSettings."""
    global _pydantic_logger
    if _pydantic_logger is None:
        from aura_cli.core.logger import get_logger

        _pydantic_logger = get_logger(__name__)
    return _pydantic_logger


_PYDANTIC_CONFIG_FILE = str(aura_path("config.json"))


class ApiKeys(BaseModel):
    """API keys for LLM providers."""

    google: Optional[str] = Field(default=None)
    openai: Optional[str] = Field(default=None)
    anthropic: Optional[str] = Field(default=None)
    openrouter: Optional[str] = Field(default=None)
    nvidia: Optional[str] = Field(default=None)
    cerebras: Optional[str] = Field(default=None)
    groq: Optional[str] = Field(default=None)


class SystemSettings(BaseModel):
    """System and infrastructure settings."""

    nim_binary_path: Optional[str] = Field(default=None)
    log_level: str = Field(default="INFO")
    enable_telemetry: bool = Field(default=True)


class AccessibilitySettings(BaseModel):
    """Opt-in accessibility preferences for compatible devices."""

    enabled: bool = Field(default=False)
    device: str = Field(default="auto")
    screen_reader: Optional[str] = Field(default=None)


class AgentSettings(BaseModel):
    """Agent behaviour settings."""

    auto_approval_threshold: int = Field(default=0)
    max_loops: int = Field(default=50)
    allow_shell_execution: bool = Field(default=True)
    timeout_seconds: int = Field(default=300)


class MemorySettings(BaseModel):
    """Memory and RAG settings."""

    # Default is "keyword" (zero extra deps). Set to "chromadb" after
    # installing the [vector] extra: pip install -e ".[vector]"
    vector_store_backend: str = Field(default="keyword")
    embed_model: str = Field(default="BAAI/bge-small-en-v1.5")
    max_memory_items: int = Field(default=1000)


class LLMSettings(BaseModel):
    """LLM generation settings."""

    temperature: float = Field(default=0.7)
    max_tokens: int = Field(default=4096)
    top_p: float = Field(default=1.0)
    system_prompt: Optional[str] = Field(default=None)


class AppSettings(BaseSettings):
    """Main application settings backed by Pydantic + JSON file."""

    api_keys: ApiKeys = Field(default_factory=ApiKeys)
    system: SystemSettings = Field(default_factory=SystemSettings)
    agents: AgentSettings = Field(default_factory=AgentSettings)
    memory: MemorySettings = Field(default_factory=MemorySettings)
    llm: LLMSettings = Field(default_factory=LLMSettings)
    accessibility: AccessibilitySettings = Field(default_factory=AccessibilitySettings)
    default_model: str = Field(default=DEFAULT_MODEL)
    theme_name: str = Field(default="aura_minimal")

    model_config = SettingsConfigDict(
        env_nested_delimiter="__",
        validate_assignment=True,
        extra="allow",
    )

    def save(self) -> None:
        """Persist settings to JSON file."""
        JsonConfigRepository().save(self)

    @classmethod
    def load(cls) -> "AppSettings":
        """Load settings from JSON file or return defaults."""
        return JsonConfigRepository().load()


class ConfigRepository(Protocol):
    """Persistence port for the typed application configuration."""

    def load(self) -> AppSettings: ...

    def save(self, settings: AppSettings) -> None: ...


class JsonConfigRepository:
    """Canonical JSON repository for :class:`AppSettings`."""

    _API_KEY_MIGRATIONS: ClassVar[dict[str, str]] = {
        "google_api_key": "google",
        "openai_api_key": "openai",
        "anthropic_api_key": "anthropic",
        "openrouter_api_key": "openrouter",
        "nvidia_api_key": "nvidia",
        "cerebras_api_key": "cerebras",
        "groq_api_key": "groq",
    }

    def __init__(self, path: str | Path | None = None) -> None:
        self.path = Path(path or _PYDANTIC_CONFIG_FILE)

    def load(self) -> AppSettings:
        """Load, validate and migrate settings; invalid files fail to defaults."""
        if not os.path.exists(self.path):
            return AppSettings()
        try:
            with open(self.path, encoding="utf-8") as config_file:
                data = json.load(config_file)
            migrated = self._migrate(data)
            settings = AppSettings.model_validate(data)
            if migrated:
                self.save(settings)
            return settings
        except (OSError, json.JSONDecodeError, TypeError, ValueError) as exc:
            _get_pydantic_logger().warning(
                "Configuração inválida em %s; usando defaults: %s", self.path, exc
            )
            return AppSettings()

    def save(self, settings: AppSettings) -> None:
        """Atomically persist one validated configuration snapshot."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(f"{self.path.suffix}.tmp")
        try:
            with open(temporary, "w", encoding="utf-8") as config_file:
                json.dump(
                    settings.model_dump(), config_file, indent=2, ensure_ascii=False
                )
            os.replace(temporary, self.path)
        except Exception as exc:
            temporary.unlink(missing_ok=True)
            _get_pydantic_logger().error(f"Error saving settings: {exc}")
            raise

    def _migrate(self, data: Dict[str, Any]) -> bool:
        migrated = False
        display = data.get("display")
        if (
            isinstance(display, dict)
            and "accessible" in display
            and "accessibility" not in data
        ):
            data["accessibility"] = {
                "enabled": bool(display["accessible"]),
                "device": "auto",
                "screen_reader": None,
            }
            migrated = True
        api_keys = data.get("api_keys")
        if not isinstance(api_keys, dict):
            return migrated
        for old, new in self._API_KEY_MIGRATIONS.items():
            if old in api_keys and new not in api_keys:
                api_keys[new] = api_keys.pop(old)
                migrated = True
        return migrated


class ConfigCompat:
    """
    Compatibility wrapper providing the legacy config_manager interface
    backed by AppSettings (Pydantic).

    All code that calls config_manager.get(), .set(), .get_api_key(), etc.
    continues to work unchanged.
    """

    def __init__(self, repository: ConfigRepository | None = None):
        self._settings: AppSettings | None = None
        self._repository = repository or JsonConfigRepository()
        self._settings_lock = threading.Lock()

    def _ensure_settings(self) -> AppSettings:
        """Lazy-load AppSettings (thread-safe)."""
        if self._settings is None:
            with self._settings_lock:
                if self._settings is None:
                    try:
                        self._settings = self._repository.load()
                    except Exception:
                        self._settings = AppSettings()
        assert self._settings is not None
        return self._settings

    def get(self, key: str, default: Optional[Any] = None) -> Optional[Any]:
        """Get a configuration value by key."""
        s = self._ensure_settings()
        _MAP = {
            "auto_mode": lambda: False,
            "auto_mode_prefer_local": lambda: False,
            "theme_name": lambda: s.theme_name,
            "accessibility": lambda: s.accessibility.model_dump(),
            "accessibility_mode": lambda: s.accessibility.enabled,
            "accessibility_device": lambda: os.environ.get(
                "AURA_ACCESSIBILITY_DEVICE", s.accessibility.device
            ),
            "accessibility_screen_reader": lambda: os.environ.get(
                "AURA_SCREEN_READER", s.accessibility.screen_reader
            ),
            "api_keys": lambda: {
                "google_api_key": s.api_keys.google,
                "openai_api_key": s.api_keys.openai,
                "anthropic_api_key": s.api_keys.anthropic,
                "openrouter_api_key": s.api_keys.openrouter,
                "nvidia_api_key": s.api_keys.nvidia,
                "cerebras_api_key": s.api_keys.cerebras,
                "groq_api_key": s.api_keys.groq,
            },
            "log_level": lambda: s.system.log_level,
            "nim_binary_path": lambda: s.system.nim_binary_path,
            "max_loops": lambda: s.agents.max_loops,
            "enable_shell": lambda: s.agents.allow_shell_execution,
            "vector_backend": lambda: s.memory.vector_store_backend,
            "temperature": lambda: s.llm.temperature,
            "max_tokens": lambda: s.llm.max_tokens,
            "top_p": lambda: s.llm.top_p,
            "system_prompt": lambda: s.llm.system_prompt,
        }
        if key == "default_model":
            return normalize_model_name(s.default_model)
        if key in _MAP:
            return _MAP[key]()
        model_dict = s.model_dump()
        return model_dict.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """Set a configuration value and persist."""
        s = self._ensure_settings()
        _SETTERS: dict = {
            "theme_name": lambda v: setattr(s, "theme_name", v),
            "accessibility_mode": lambda v: setattr(
                s.accessibility, "enabled", bool(v)
            ),
            "accessibility_device": lambda v: setattr(
                s.accessibility, "device", str(v)
            ),
            "accessibility_screen_reader": lambda v: setattr(
                s.accessibility, "screen_reader", v if v else None
            ),
            "log_level": lambda v: setattr(s.system, "log_level", v),
            "nim_binary_path": lambda v: setattr(s.system, "nim_binary_path", v),
            "max_loops": lambda v: setattr(s.agents, "max_loops", int(v)),
            "enable_shell": lambda v: setattr(
                s.agents, "allow_shell_execution", bool(v)
            ),
            "vector_backend": lambda v: setattr(s.memory, "vector_store_backend", v),
            "temperature": lambda v: setattr(s.llm, "temperature", float(v)),
            "max_tokens": lambda v: setattr(s.llm, "max_tokens", int(v)),
            "top_p": lambda v: setattr(s.llm, "top_p", float(v)),
            "system_prompt": lambda v: setattr(
                s.llm, "system_prompt", v if v else None
            ),
        }
        if key == "default_model":
            s.default_model = normalize_model_name(value) or s.default_model
        elif key in ("auto_mode", "auto_mode_prefer_local"):
            pass  # Deprecated, ignore silently
        elif key == "api_keys" and isinstance(value, dict):
            _KEY_MAP = {
                "google_api_key": "google",
                "openai_api_key": "openai",
                "anthropic_api_key": "anthropic",
                "openrouter_api_key": "openrouter",
                "nvidia_api_key": "nvidia",
                "cerebras_api_key": "cerebras",
                "groq_api_key": "groq",
            }
            valid_providers = set(_KEY_MAP.values())
            for legacy_key, secret in value.items():
                provider = _KEY_MAP.get(legacy_key, legacy_key)
                if provider in valid_providers:
                    self.set_api_key(provider, secret)
            return
        elif key in _SETTERS:
            _SETTERS[key](value)
        else:
            setattr(s, key, value)
        self._repository.save(s)

    def get_api_key(self, provider: str) -> Optional[str]:
        """Get API key for a provider."""
        settings = self._ensure_settings()
        return getattr(settings.api_keys, provider.lower(), None)

    def set_api_key(self, provider: str, api_key: Optional[str]) -> None:
        """Set API key using SecureConfig as the persistence authority.

        The typed JSON configuration stores only a ``None`` marker for API
        keys.  Secret material is written to the keyring (or to the explicit
        insecure fallback managed by SecureConfig) before the non-sensitive
        settings document is persisted.  This prevents the compatibility
        wrapper from leaking credentials into ``config.json``.
        """
        settings = self._ensure_settings()
        provider_lower = provider.lower().strip()
        if not hasattr(settings.api_keys, provider_lower):
            _get_pydantic_logger().warning(f"Provedor desconhecido: {provider}")
            return

        from aura_cli.core.secure_config import secure_config_manager

        if api_key:
            secure_config_manager.set_api_key(provider_lower, api_key)
        else:
            secure_config_manager.delete_api_key(provider_lower)

        # Keep the typed JSON document free of secret material.  SecureConfig
        # is the only layer that persists the credential itself.
        setattr(settings.api_keys, provider_lower, None)
        self._repository.save(settings)
