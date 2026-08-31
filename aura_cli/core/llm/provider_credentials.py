"""Credential loading and key-rotation setup for LLM provider adapters."""

from __future__ import annotations

from collections.abc import Mapping

from aura_cli.core.llm.key_rotation import register_keys


def prepare_provider_credentials(credentials: Mapping[str, str]) -> dict[str, str]:
    """Copy credentials and configure rotators without mutating ``os.environ``."""
    prepared = {name: value for name, value in credentials.items() if value}
    google_keys = prepared.get("GOOGLE_API_KEY") or prepared.get("GEMINI_API_KEY", "")
    register_keys("google", google_keys)
    register_keys("openrouter", prepared.get("OPENROUTER_API_KEY", ""))
    register_keys("groq", prepared.get("GROQ_API_KEY", ""))
    return prepared


def load_provider_credentials() -> dict[str, str]:
    """Load configured secrets through Aura's credential adapter."""
    from aura_cli.core.api_keys import get_api_keys_dict

    return prepare_provider_credentials(get_api_keys_dict())
