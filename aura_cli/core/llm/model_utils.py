"""
Utility functions for LLM model management in Aura CLI.

This module provides centralized utilities for model name normalization,
default model constants, and model validation. This ensures consistency
across all modules that work with LLM models.

Usage:
    >>> from aura_cli.core.llm.model_utils import normalize_model_name, DEFAULT_MODEL
    >>> model = normalize_model_name("gemini-2.0-flash-exp")
    >>> print(model)  # "gemini/gemini-2.0-flash-exp"
"""

from typing import Optional

# Aura default model — validated against the configured Cerebras endpoint.
DEFAULT_MODEL = "cerebras/gpt-oss-120b"
DEFAULT_GEMINI_MODEL = "gemini/gemini-2.5-flash"
DEFAULT_CEREBRAS_MODEL = "cerebras/gpt-oss-120b"
DEFAULT_CEREBRAS_FAST_MODEL = "cerebras/gpt-oss-120b"
DEFAULT_OPENAI_MODEL = "gpt-4o"
DEFAULT_ANTHROPIC_MODEL = "claude-sonnet-4-6"
DEFAULT_OPENROUTER_MODEL = "openrouter/free"
DEFAULT_NVIDIA_MODEL = "nvidia/nvidia/nemotron-3.5-lightning-30b-a3b"
DEFAULT_GROQ_MODEL = "groq/openai/gpt-oss-20b"

PROVIDER_ALIASES = {
    "google": "gemini",
    "gemini": "gemini",
    "openai": "gpt",
    "gpt": "gpt",
    "anthropic": "claude",
    "claude": "claude",
    "cerebras": "cerebras",
    "openrouter": "openrouter",
    "nvidia": "nvidia",
    "groq": "groq",
}

_PROVIDER_DEFAULTS = {
    "gemini": DEFAULT_GEMINI_MODEL,
    "gpt": DEFAULT_OPENAI_MODEL,
    "claude": DEFAULT_ANTHROPIC_MODEL,
    "openrouter": DEFAULT_OPENROUTER_MODEL,
    "cerebras": DEFAULT_CEREBRAS_MODEL,
    "nvidia": DEFAULT_NVIDIA_MODEL,
    "groq": DEFAULT_GROQ_MODEL,
}


def normalize_provider_name(provider: Optional[str]) -> str:
    """Return the short canonical provider name used by the catalog."""
    value = (provider or "").strip().lower()
    return PROVIDER_ALIASES.get(value, value)


_BUILTIN_MODEL_PRESETS = {
    "gemini": [
        "gemini/gemini-2.5-flash",
        "gemini/gemini-2.5-pro",
        "gemini/gemini-2.5-flash-lite",
        "gemini/gemini-3.8-flash",
        "gemini/gemini-3.5-flash",
    ],
    "cerebras": [
        "cerebras/gpt-oss-120b",
        "cerebras/zai-glm-4.7",
        "cerebras/llama3.1-8b",
    ],
    "openrouter": [
        "openrouter/free",
        "openrouter/nvidia/nemotron-3-super-120b-a12b:free",
        "openrouter/nvidia/nemotron-3-ultra-550b-a55b:free",
        "openrouter/nvidia/nemotron-3.5-super-vl:free",
        "openrouter/cohere/north-mini-code:free",
        "openrouter/qwen/qwen3-coder:free",
    ],
    "gpt": ["gpt-4o", "gpt-4o-mini"],
    "claude": ["claude-sonnet-4-6", "claude-haiku-4-5-20251001"],
    "nvidia": [
        "nvidia/nvidia/nemotron-3.5-lightning-30b-a3b",
        "nvidia/nvidia/nemotron-3-super-120b-a12b",
        "nvidia/nvidia/nemotron-3-ultra-550b-a55b",
        "nvidia/nvidia/nemotron-3.5-lightning-30b-a3b",
        "nvidia/nvidia/nemotron-3.5-super-vl-120b-a12b",
        "nvidia/google/gemma-4-31b-it",
    ],
    "groq": [
        "groq/openai/gpt-oss-20b",
        "groq/openai/gpt-oss-120b",
    ],
}


def _load_model_presets():
    """Load model presets from JSON, with one safe built-in fallback."""
    import json
    from pathlib import Path

    json_path = Path(__file__).with_name("models.json")
    try:
        if json_path.exists():
            with open(json_path, encoding="utf-8") as f:
                loaded = json.load(f)
            if isinstance(loaded, dict) and all(
                isinstance(models, list) for models in loaded.values()
            ):
                return loaded
    except (OSError, json.JSONDecodeError, ValueError) as error:
        import logging

        logging.getLogger(__name__).warning("Failed to load LLM presets: %s", error)
    return {
        provider: models.copy() for provider, models in _BUILTIN_MODEL_PRESETS.items()
    }


MODEL_PRESETS = _load_model_presets()


def get_model_catalog() -> dict[str, list[str]]:
    """Return a defensive copy of the canonical provider → model catalog."""
    return {
        normalize_provider_name(provider): list(models)
        for provider, models in MODEL_PRESETS.items()
    }


def get_models_for_provider(provider: Optional[str]) -> list[str]:
    """Return canonical model IDs for a provider alias."""
    return get_model_catalog().get(normalize_provider_name(provider), [])


def get_default_model_for_provider(provider: Optional[str]) -> str:
    """
    Return the canonical default model for a provider.

    Prefers the centralized preset catalog when present, falling back to the
    exported default constants for stability.
    """
    normalized_provider = normalize_provider_name(provider)
    preset_models = MODEL_PRESETS.get(normalized_provider, [])
    if preset_models:
        return preset_models[0]

    return _PROVIDER_DEFAULTS.get(normalized_provider, DEFAULT_MODEL)


def get_default_multi_model_candidates() -> list[str]:
    """
    Return the canonical default ensemble list for multi-model mode.

    The list is intentionally small and derived from the centralized provider
    catalog so multi-model mode does not maintain its own hardcoded universe.
    """
    provider_order = ("nvidia", "gemini", "gpt")
    candidates: list[str] = []

    for provider in provider_order:
        model = get_default_model_for_provider(provider)
        if model and model not in candidates:
            candidates.append(model)

    if not candidates:
        candidates.append(DEFAULT_MODEL)

    return candidates


def normalize_model_name(model: Optional[str]) -> Optional[str]:
    """Normalise a model name to a canonical LiteLLM format."""
    if not model or not isinstance(model, str):
        return model

    model_lower = model.lower().strip()
    if not model_lower:
        return DEFAULT_MODEL

    if model_lower in PROVIDER_ALIASES:
        return _PROVIDER_DEFAULTS.get(PROVIDER_ALIASES[model_lower], DEFAULT_MODEL)

    # Already-prefixed models — return as-is
    if model_lower.startswith(("google/", "anthropic/")):
        model = model_lower.split("/", 1)[1]
        model_lower = model

    if model_lower.startswith(
        (
            "gemini/",
            "openrouter/",
            "nvidia/",
            "openai/nvidia/",
            "claude-",
            "gpt-",
            "cerebras/",
            "groq/",
        )
    ):
        return model_lower

    if "cerebras" in model_lower:
        return (
            f"cerebras/{model_lower}"
            if not model_lower.startswith("cerebras/")
            else model_lower
        )

    if model_lower.startswith("groq/"):
        return model_lower

    if "gemma" in model_lower:
        return (
            f"gemini/{model_lower}"
            if not model_lower.startswith("gemini/")
            else model_lower
        )
    if "gemini" in model_lower:
        return _normalize_gemini(model, model_lower)
    if "gpt" in model_lower:
        return _normalize_gpt(model, model_lower)
    if "claude" in model_lower:
        return _normalize_claude(model, model_lower)
    if model_lower.startswith(("openai/nvidia/", "nvidia/")):
        return model_lower
    if ":free" in model_lower:
        return (
            model_lower
            if model_lower.startswith("openrouter/")
            else f"openrouter/{model_lower}"
        )
    if "llama" in model_lower or "openrouter" in model_lower:
        return _normalize_openrouter(model, model_lower)
    return model_lower


def _normalize_gemini(model: str, model_lower: str) -> str:
    if model_lower == "gemini" or (
        model_lower.startswith("gemini ") and len(model_lower.split()) <= 2
    ):
        return DEFAULT_GEMINI_MODEL
    if " " in model and not model.startswith("gemini/"):
        parts = model.split()
        version_part = "-".join(parts[1:]).lower()
        return f"gemini/gemini-{version_part}"
    return f"gemini/{model}"


def _normalize_gpt(model: str, model_lower: str) -> str:
    if model_lower.startswith("gpt-"):
        return model_lower
    if " " in model:
        parts = model.split()
        if len(parts) >= 2:
            return f"gpt-{parts[1].lower()}"
    if model_lower.startswith("gpt"):
        return f"gpt-{model_lower[3:]}"
    return model_lower


def _normalize_claude(model: str, model_lower: str) -> str:
    if model_lower.startswith("claude-"):
        return model_lower
    if " " in model:
        claude_models = MODEL_PRESETS.get("claude", [])
        if claude_models:
            return claude_models[0]
    return model_lower


def _normalize_openrouter(model: str, model_lower: str) -> str:
    if model_lower.startswith("openrouter/"):
        return model_lower
    openrouter_models = MODEL_PRESETS.get("openrouter", [])
    if openrouter_models:
        return openrouter_models[0]
    return f"openrouter/{model}"


def resolve_model_option(model: Optional[str]) -> str:
    """Resolve a CLI/TUI model option to ``auto`` or a canonical model ID.

    ``None``, blank input and the explicit ``auto`` option keep automatic task
    routing. Provider aliases such as ``google`` or ``openai`` resolve to the
    catalog default, while model IDs are normalized for LiteLLM.
    """
    if model is None or not str(model).strip() or str(model).strip().lower() == "auto":
        return "auto"
    return normalize_model_name(str(model).strip()) or DEFAULT_MODEL


def get_provider_from_model(model: str) -> Optional[str]:
    """
    Identifica o provedor a partir do nome do modelo.

    Args:
        model: Nome do modelo

    Returns:
        Nome do provedor ('gemini', 'claude', 'gpt', 'openrouter', 'auto') ou None
    """
    if not model:
        return None

    model_lower = model.lower()

    if model_lower == "auto":
        return "auto"
    if model_lower.startswith("cerebras/") or "cerebras" in model_lower:
        return "cerebras"
    if model_lower.startswith(("groq/", "groq-")):
        return "groq"
    if (
        model_lower.startswith(("openai/nvidia/", "nvidia/"))
        or "nemotron" in model_lower
    ):
        return "nvidia"
    elif (
        model_lower.startswith("gemini/")
        or "gemini" in model_lower
        or "gemma" in model_lower
    ):
        return "gemini"
    elif model_lower.startswith("openrouter/") or any(
        x in model_lower
        for x in ["llama-3", "llama-4", "deepseek", "mistral-small", "kimi-vl", ":free"]
    ):
        return "openrouter"
    elif model_lower.startswith("claude-") or "claude" in model_lower:
        return "claude"
    elif model_lower.startswith(("gpt-", "gpt")):
        return "gpt"

    return None


def get_fallback_models(model: str) -> list:
    """Return fallback model list for a provider."""
    provider = get_provider_from_model(model)

    if provider and provider in MODEL_PRESETS:
        models = [model]
        models.extend([m for m in MODEL_PRESETS[provider] if m != model])
        return models

    return [model]


def is_valid_model_format(model: str) -> bool:
    """Return True if the model name follows valid format."""
    if not model or not isinstance(model, str):
        return False

    model_lower = model.lower()
    if "gemini" in model_lower or "gemma" in model_lower:
        return model.startswith("gemini/")
    return True


def format_model_display_name(model_id: str) -> str:
    """Format model ID into a clean, compact display name.

    Produces short identifiers suitable for status lines and footers.
    Rules:
    - Strip provider prefixes (gemini/, openrouter/vendor/)
    - Strip :free suffix
    - Strip date suffixes like -20251001
    - For Claude: simplify version numbers (4-6 → 4, 4-5 → 4.5)
    - Keep the essential model identifier

    Args:
        model_id: Full model ID (e.g. "gemini/gemini-2.5-flash")

    Returns:
        Short display name (e.g. "gemini-2.5-flash")
    """
    import re

    if not model_id or model_id == "auto":
        return "auto"

    name = model_id.strip()

    # Strip provider prefixes
    # openrouter/vendor/model → model
    if name.startswith("openrouter/"):
        parts = name[len("openrouter/") :].split("/")
        name = parts[-1] if len(parts) >= 2 else parts[0]
    elif name.startswith("gemini/"):
        name = name[len("gemini/") :]
    elif name.startswith("openai/nvidia/"):
        name = name[len("openai/nvidia/") :]
    elif name.startswith("nvidia/"):
        name = name[len("nvidia/") :]

    # Strip :free suffix
    name = re.sub(r":free$", "", name)

    # Strip -it suffix (instruction-tuned marker)
    name = re.sub(r"-it$", "", name)

    # Strip date suffixes like -20251001
    name = re.sub(r"-\d{8}$", "", name)

    # Strip -instruct suffix
    name = re.sub(r"-instruct$", "", name)

    # Claude version simplification
    # claude-sonnet-4-6 → claude-sonnet-4
    # claude-haiku-4-5 → claude-haiku-4.5
    claude_match = re.match(r"^(claude-\w+)-(\d+)-(\d+)$", name)
    if claude_match:
        base, major, minor = claude_match.groups()
        name = f"{base}-{major}.{minor}" if minor == "5" else f"{base}-{major}"

    # Strip size suffixes like -a12b, -a55b, -a4b (architecture variants)
    name = re.sub(r"-a\d+b$", "", name)

    return name


def get_valid_models() -> dict:
    """Return the list of valid models for a provider."""
    models = {}
    for _provider, model_list in MODEL_PRESETS.items():
        if not model_list:
            continue
        for model_id in model_list:
            name = format_model_display_name(model_id)
            if model_id == "auto":
                provider_name = "Auto"
            elif model_id.startswith("cerebras/"):
                provider_name = "Cerebras"
            elif model_id.startswith("gemini/"):
                provider_name = "Google"
            elif model_id.startswith("gpt-"):
                provider_name = "OpenAI"
            elif model_id.startswith("claude-"):
                provider_name = "Anthropic"
            elif model_id.startswith("openrouter/"):
                provider_name = "OpenRouter"
            elif model_id.startswith(("openai/nvidia/", "nvidia/")):
                provider_name = "NVIDIA"
            else:
                provider_name = "Unknown"

            models[model_id] = {"name": name, "provider": provider_name}

    return models
