"""Single source of truth for LLM providers (identity, credentials, aliases).

Every provider fact lives here exactly once. The other tables are *derived*:

* ``core/api_key_store.API_PROVIDERS`` / ``PROVIDER_ENV_KEYS``  (storage + UI)
* ``core/api_keys`` provider iteration                           (key resolution)
* ``core/llm/model_utils.PROVIDER_ALIASES`` / ``PROVIDER_ENV_KEYS`` (catalog)
* ``core/llm/provider_policy`` credential names                  (LiteLLM policy)

Two id vocabularies exist for historical reasons and are both modelled:

* ``id``      — storage/UI id (``google``, ``openai``, ``anthropic``)
* ``catalog`` — short name used by the model catalog (``gemini``, ``gpt``, ``claude``)

Pure data, no I/O and no UI imports (safe for ``core/``). Order is the order
providers are shown to the user.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ProviderSpec:
    """Immutable description of one LLM provider."""

    id: str
    catalog: str
    label: str
    env_keys: tuple[str, ...]  # primary first; the rest are accepted aliases
    aliases: tuple[str, ...] = ()  # extra names accepted when normalizing input

    @property
    def primary_env_key(self) -> str:
        """Return the canonical environment variable name for this provider's API key."""
        return self.env_keys[0]


PROVIDER_SPECS: tuple[ProviderSpec, ...] = (
    ProviderSpec(
        "google",
        "gemini",
        "Google Gemini",
        ("GOOGLE_API_KEY", "GEMINI_API_KEY"),
    ),
    ProviderSpec("cerebras", "cerebras", "Cerebras", ("CEREBRAS_API_KEY",)),
    ProviderSpec("groq", "groq", "Groq", ("GROQ_API_KEY",)),
    ProviderSpec("openrouter", "openrouter", "OpenRouter", ("OPENROUTER_API_KEY",)),
    ProviderSpec("openai", "gpt", "OpenAI", ("OPENAI_API_KEY",)),
    ProviderSpec("anthropic", "claude", "Anthropic", ("ANTHROPIC_API_KEY",)),
    ProviderSpec("nvidia", "nvidia", "NVIDIA", ("NVIDIA_API_KEY",)),
)

_BY_ID = {spec.id: spec for spec in PROVIDER_SPECS}
_BY_CATALOG = {spec.catalog: spec for spec in PROVIDER_SPECS}


def provider_by_id(provider_id: str) -> ProviderSpec | None:
    """Look up by storage/UI id (``google``) — case/space insensitive."""
    return _BY_ID.get((provider_id or "").strip().lower())


def provider_by_catalog(catalog_name: str) -> ProviderSpec | None:
    """Look up by catalog short name (``gemini``) — case/space insensitive."""
    return _BY_CATALOG.get((catalog_name or "").strip().lower())


def provider_by_any_name(name: str) -> ProviderSpec | None:
    """Resolve any accepted spelling: id, catalog name or explicit alias."""
    value = (name or "").strip().lower()
    return _BY_ID.get(value) or _BY_CATALOG.get(value) or _BY_ALIAS.get(value)


_BY_ALIAS = {alias: spec for spec in PROVIDER_SPECS for alias in spec.aliases}


def env_keys_for(provider_id: str) -> tuple[str, ...]:
    """All env var names accepted for a provider id (primary first)."""
    spec = provider_by_id(provider_id) or provider_by_catalog(provider_id)
    return spec.env_keys if spec else ()


def all_env_keys() -> tuple[str, ...]:
    """Every credential env var of every provider, de-duplicated, in spec order."""
    seen: dict[str, None] = {}
    for spec in PROVIDER_SPECS:
        for key in spec.env_keys:
            seen.setdefault(key)
    return tuple(seen)


__all__ = [
    "PROVIDER_SPECS",
    "ProviderSpec",
    "all_env_keys",
    "env_keys_for",
    "provider_by_any_name",
    "provider_by_catalog",
    "provider_by_id",
]
