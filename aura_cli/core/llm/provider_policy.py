"""Pure provider classification and structural LiteLLM policy."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ProviderPolicy:
    """Provider metadata derived from a normalized model identifier."""

    name: str
    preset: str
    runtime_name: str
    key_names: tuple[str, ...] = ()
    api_base: str | None = None
    api_version: str | None = None
    thinking_budget: int | None = None


def provider_policy(model: str) -> ProviderPolicy:
    """Classify a model without consulting credentials or mutable process state."""
    normalized = model.lower()
    if normalized.startswith("openrouter/") or ":free" in normalized:
        return ProviderPolicy(
            "openrouter", "openrouter", "openrouter", ("OPENROUTER_API_KEY",)
        )
    if normalized.startswith(("nvidia/", "openai/nvidia/")) or "nemotron" in normalized:
        return ProviderPolicy(
            "nvidia",
            "nvidia",
            "nvidia",
            ("NVIDIA_API_KEY",),
            api_base="https://integrate.api.nvidia.com/v1",
        )
    if normalized.startswith("gemini/") or "gemini" in normalized:
        thinking_budget = 2048 if "2.5" in normalized or "2-5" in normalized else None
        return ProviderPolicy(
            "gemini",
            "gemini",
            "google",
            ("GOOGLE_API_KEY", "GEMINI_API_KEY"),
            api_version="v1",
            thinking_budget=thinking_budget,
        )
    if normalized.startswith("cerebras/"):
        return ProviderPolicy("cerebras", "cerebras", "cerebras", ("CEREBRAS_API_KEY",))
    if normalized.startswith(("groq/", "groq-")):
        return ProviderPolicy("groq", "groq", "groq", ("GROQ_API_KEY",))
    if (
        normalized.startswith("claude-")
        or "claude" in normalized
        or "anthropic" in normalized
    ):
        return ProviderPolicy(
            "anthropic", "claude", "anthropic", ("ANTHROPIC_API_KEY",)
        )
    if normalized.startswith(("gpt-", "gpt", "o1-", "o3-")):
        return ProviderPolicy("gpt", "gpt", "openai", ("OPENAI_API_KEY",))
    if "openrouter" in normalized or any(
        family in normalized for family in ("llama-3", "llama-4")
    ):
        return ProviderPolicy(
            "openrouter", "openrouter", "openrouter", ("OPENROUTER_API_KEY",)
        )
    return ProviderPolicy("google", "", "google", ("GOOGLE_API_KEY", "GEMINI_API_KEY"))


def structural_completion_params(model: str) -> dict[str, object]:
    """Return provider parameters independent from secret resolution."""
    policy = provider_policy(model)
    params: dict[str, object] = {}
    if policy.api_base:
        params["api_base"] = policy.api_base
    if policy.api_version:
        params["api_version"] = policy.api_version
    if policy.thinking_budget is not None:
        params["thinking"] = {
            "type": "enabled",
            "budget_tokens": policy.thinking_budget,
        }
    return params
