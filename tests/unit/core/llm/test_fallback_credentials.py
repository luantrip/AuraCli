import pytest

from aura_cli.core.llm import base


def _fallbacks(monkeypatch, keys: dict[str, str], current_provider: str) -> list[str]:
    monkeypatch.setattr("aura_cli.core.api_keys.get_api_keys_dict", lambda: keys)
    models: list[str] = []
    base._append_cross_provider_fallbacks(models, current_provider)
    return models


def test_gemini_fallback_accepts_either_credential_name(monkeypatch) -> None:
    only_google = _fallbacks(monkeypatch, {"GOOGLE_API_KEY": "k"}, "cerebras")
    only_gemini = _fallbacks(monkeypatch, {"GEMINI_API_KEY": "k"}, "cerebras")
    assert only_google and only_google == only_gemini


def test_provider_without_a_key_is_not_a_fallback(monkeypatch) -> None:
    assert _fallbacks(monkeypatch, {}, "cerebras") == []


def test_current_provider_is_never_its_own_fallback(monkeypatch) -> None:
    keys = {"CEREBRAS_API_KEY": "k"}
    assert _fallbacks(monkeypatch, keys, "cerebras") == []
    assert _fallbacks(monkeypatch, keys, "gemini")  # someone else gets it


@pytest.mark.parametrize(
    ("env_key", "expected_provider_hint"),
    [
        ("OPENAI_API_KEY", "gpt"),
        ("ANTHROPIC_API_KEY", "claude"),
        ("NVIDIA_API_KEY", "nvidia"),
        ("GROQ_API_KEY", "groq"),
        ("OPENROUTER_API_KEY", "openrouter"),
    ],
)
def test_each_provider_key_unlocks_exactly_one_fallback(
    monkeypatch, env_key: str, expected_provider_hint: str
) -> None:
    result = _fallbacks(monkeypatch, {env_key: "k"}, "cerebras")
    assert len(result) == 1, (env_key, result)
