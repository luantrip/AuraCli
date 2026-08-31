"""Central API key persistence for Aura CLI (CLI + TUI).

Unifies keyring/file (SecureConfig), Pydantic config (~/.aura/config.json),
and process environment variables.
"""

from __future__ import annotations

import os
from typing import Dict, List, Optional, Tuple

from aura_cli.core.logger import get_logger

logger = get_logger(__name__)

# (provider_id, display_name, primary_env_key)
API_PROVIDERS: Tuple[Tuple[str, str, str], ...] = (
    ("google", "Google Gemini", "GOOGLE_API_KEY"),
    ("cerebras", "Cerebras", "CEREBRAS_API_KEY"),
    ("groq", "Groq", "GROQ_API_KEY"),
    ("openrouter", "OpenRouter", "OPENROUTER_API_KEY"),
    ("openai", "OpenAI", "OPENAI_API_KEY"),
    ("anthropic", "Anthropic", "ANTHROPIC_API_KEY"),
    ("nvidia", "NVIDIA", "NVIDIA_API_KEY"),
)

PROVIDER_ENV_KEYS: Dict[str, List[str]] = {
    "google": ["GOOGLE_API_KEY", "GEMINI_API_KEY"],
    "cerebras": ["CEREBRAS_API_KEY"],
    "groq": ["GROQ_API_KEY"],
    "openrouter": ["OPENROUTER_API_KEY"],
    "openai": ["OPENAI_API_KEY"],
    "anthropic": ["ANTHROPIC_API_KEY"],
    "nvidia": ["NVIDIA_API_KEY"],
}


def _normalize_provider(provider: str) -> str:
    return provider.lower().strip()


def clear_env_keys_for_provider(provider: str) -> None:
    """Remove API key env vars for this process."""
    for env_key in PROVIDER_ENV_KEYS.get(_normalize_provider(provider), []):
        os.environ.pop(env_key, None)


def clear_api_key_for_provider(provider: str) -> None:
    """Remove stored API key for a provider from all backends."""
    provider = _normalize_provider(provider)
    try:
        from aura_cli.core.secure_config import secure_config_manager

        secure_config_manager.delete_api_key(provider)
    except Exception as exc:
        logger.debug("SecureConfig delete failed for %s: %s", provider, exc)

    try:
        from aura_cli.core.config import ConfigCompat

        ConfigCompat().set_api_key(provider, None)
    except Exception as exc:
        logger.debug("Pydantic clear failed for %s: %s", provider, exc)

    clear_env_keys_for_provider(provider)


def set_api_key_for_provider(provider: str, api_key: str) -> None:
    """Persist API key; empty string clears the key."""
    provider = _normalize_provider(provider)
    if not api_key or not api_key.strip():
        clear_api_key_for_provider(provider)
        return

    key = api_key.strip()
    try:
        from aura_cli.core.config import ConfigCompat

        ConfigCompat().set_api_key(provider, key)
    except Exception as exc:
        logger.error("Failed to save API key via ConfigCompat: %s", exc)
        from aura_cli.core.secure_config import secure_config_manager

        secure_config_manager.set_api_key(provider, key)

    clear_env_keys_for_provider(provider)


def provider_key_configured(
    provider: str, api_keys: Optional[Dict[str, str]] = None
) -> bool:
    """Return True if provider has a configured key."""
    provider = _normalize_provider(provider)
    env_name = next((p[2] for p in API_PROVIDERS if p[0] == provider), "")
    if api_keys is None:
        from aura_cli.core.api_keys import get_api_keys_dict

        api_keys = get_api_keys_dict()
    if env_name and api_keys.get(env_name):
        return True
    return bool(provider == "google" and api_keys.get("GEMINI_API_KEY"))


def format_providers_status(api_keys: Optional[Dict[str, str]] = None) -> str:
    """Multi-line status for settings UI."""
    if api_keys is None:
        from aura_cli.core.api_keys import get_api_keys_dict

        api_keys = get_api_keys_dict()
    lines = []
    for pid, label, _ in API_PROVIDERS:
        mark = "✓" if provider_key_configured(pid, api_keys) else "·"
        lines.append(f"  {mark} {label}")
    return "\n".join(lines)


def clear_all_api_keys() -> None:
    """Remove all provider API keys."""
    for pid, _, _ in API_PROVIDERS:
        clear_api_key_for_provider(pid)
