"""API key resolution for Aura CLI.

Retrieves API keys from PydanticConfig, SecureConfig and environment variables.
This module lives in core so that both CLI and core layers can use it without
introducing a circular dependency.
"""

from __future__ import annotations

import os
from typing import Dict

from aura_cli.core.logger import get_logger

logger = get_logger(__name__)


def get_api_keys_dict() -> Dict[str, str]:
    """Get dictionary of API keys from SecureConfig and environment variables.

    Resolution order:
        1. PydanticConfig (new system)
        2. SecureConfig (keyring/file)
        3. Environment variables (fallback)

    Returns:
        Dictionary with API key names as keys (e.g. GOOGLE_API_KEY).
    """
    api_keys: Dict[str, str] = {}

    _PYDANTIC_PROVIDERS = [
        ("google", "GOOGLE_API_KEY", "GEMINI_API_KEY"),
        ("openai", "OPENAI_API_KEY", None),
        ("anthropic", "ANTHROPIC_API_KEY", None),
        ("openrouter", "OPENROUTER_API_KEY", None),
        ("nvidia", "NVIDIA_API_KEY", None),
        ("cerebras", "CEREBRAS_API_KEY", None),
        ("groq", "GROQ_API_KEY", None),
    ]
    try:
        from aura_cli.core.config import ConfigCompat

        pydantic_config = ConfigCompat()
        for provider, primary_key, alias_key in _PYDANTIC_PROVIDERS:
            value = pydantic_config.get_api_key(provider)
            if value:
                api_keys[primary_key] = value
                if alias_key:
                    api_keys[alias_key] = value
    except Exception as exc:
        logger.debug(f"Error fetching keys from PydanticConfig: {exc}")

    try:
        from aura_cli.core.secure_config import secure_config_manager

        for provider, primary_key, alias_key in _PYDANTIC_PROVIDERS:
            if primary_key not in api_keys:
                value = secure_config_manager.get_api_key(provider)
                if value:
                    api_keys[primary_key] = value
                    if alias_key and alias_key not in api_keys:
                        api_keys[alias_key] = value
    except Exception as exc:
        logger.debug(f"Error fetching keys from SecureConfig: {exc}")

    _ENV_KEYS = [
        "GOOGLE_API_KEY",
        "GEMINI_API_KEY",
        "OPENAI_API_KEY",
        "ANTHROPIC_API_KEY",
        "OPENROUTER_API_KEY",
        "NVIDIA_API_KEY",
        "CEREBRAS_API_KEY",
        "GROQ_API_KEY",
    ]
    for key in _ENV_KEYS:
        if key not in api_keys:
            env_val = os.getenv(key)
            if env_val:
                api_keys[key] = env_val

    # Ensure Google/Gemini aliases are symmetric
    if "GOOGLE_API_KEY" in api_keys and "GEMINI_API_KEY" not in api_keys:
        api_keys["GEMINI_API_KEY"] = api_keys["GOOGLE_API_KEY"]
    elif "GEMINI_API_KEY" in api_keys and "GOOGLE_API_KEY" not in api_keys:
        api_keys["GOOGLE_API_KEY"] = api_keys["GEMINI_API_KEY"]

    return api_keys
