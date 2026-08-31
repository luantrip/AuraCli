"""Framework-neutral LLM settings model and form validation."""

from __future__ import annotations

from dataclasses import asdict, dataclass, fields
from typing import Any, Mapping


@dataclass
class LLMSettings:
    provider: str = "google"
    model: str = "gemini/gemini-2.5-flash"
    temperature: float = 0.7
    max_tokens: int = 4096
    top_p: float = 1.0
    frequency_penalty: float = 0.0
    presence_penalty: float = 0.0
    api_key: str = ""
    base_url: str = ""
    streaming: bool = True
    context_window: int = 8000
    system_prompt: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> LLMSettings:
        accepted = {field.name for field in fields(cls)}
        return cls(**{key: value for key, value in data.items() if key in accepted})


def provider_selector_name(provider: str | None) -> str:
    aliases = {"gemini": "google", "gpt": "openai", "claude": "anthropic"}
    normalized = (provider or "").casefold()
    return aliases.get(normalized, normalized or "google")


def provider_api_key_name(provider: str) -> str:
    return {
        "google": "GOOGLE_API_KEY",
        "cerebras": "CEREBRAS_API_KEY",
        "openrouter": "OPENROUTER_API_KEY",
        "openai": "OPENAI_API_KEY",
        "anthropic": "ANTHROPIC_API_KEY",
        "nvidia": "NVIDIA_API_KEY",
        "groq": "GROQ_API_KEY",
    }.get(provider.casefold(), "")


def parse_llm_settings_form(values: Mapping[str, Any]) -> LLMSettings:
    """Convert string-oriented form values and enforce documented ranges."""
    settings = LLMSettings(
        provider=str(values.get("provider") or "google"),
        model=str(values.get("model") or ""),
        temperature=_number(values, "temperature", 0.7, float),
        max_tokens=_number(values, "max_tokens", 4096, int),
        top_p=_number(values, "top_p", 1.0, float),
        frequency_penalty=_number(values, "frequency_penalty", 0.0, float),
        presence_penalty=_number(values, "presence_penalty", 0.0, float),
        api_key=str(values.get("api_key") or ""),
        base_url=str(values.get("base_url") or ""),
        streaming=bool(values.get("streaming", True)),
        context_window=_number(values, "context_window", 8000, int),
        system_prompt=str(values.get("system_prompt") or ""),
    )
    ranges = {
        "temperature": (settings.temperature, 0.0, 2.0),
        "max_tokens": (settings.max_tokens, 1, 128000),
        "top_p": (settings.top_p, 0.0, 1.0),
        "frequency_penalty": (settings.frequency_penalty, -2.0, 2.0),
        "presence_penalty": (settings.presence_penalty, -2.0, 2.0),
        "context_window": (settings.context_window, 1000, 128000),
    }
    for name, (value, minimum, maximum) in ranges.items():
        if not minimum <= value <= maximum:
            raise ValueError(f"{name} must be between {minimum} and {maximum}")
    return settings


def _number(values: Mapping[str, Any], name: str, default: Any, converter: Any) -> Any:
    raw = values.get(name)
    return converter(default if raw in (None, "") else raw)


__all__ = [
    "LLMSettings",
    "parse_llm_settings_form",
    "provider_api_key_name",
    "provider_selector_name",
]
