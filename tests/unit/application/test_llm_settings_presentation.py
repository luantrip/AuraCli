"""LLM settings model and form contracts."""

import pytest

from aura_cli.application.presentation.llm_settings import (
    LLMSettings,
    parse_llm_settings_form,
    provider_api_key_name,
    provider_selector_name,
)


def test_model_round_trip_ignores_unknown_fields() -> None:
    settings = LLMSettings.from_dict(
        {"provider": "nvidia", "temperature": 0.2, "old": 1}
    )
    assert settings.provider == "nvidia"
    assert settings.to_dict()["temperature"] == 0.2
    assert "old" not in settings.to_dict()


def test_provider_aliases_and_key_names_are_shared_decisions() -> None:
    assert provider_selector_name("gemini") == "google"
    assert provider_selector_name("claude") == "anthropic"
    assert provider_api_key_name("NVIDIA") == "NVIDIA_API_KEY"


def test_form_parses_defaults_booleans_and_numeric_values() -> None:
    settings = parse_llm_settings_form(
        {
            "model": "model",
            "temperature": "0.3",
            "max_tokens": "2048",
            "streaming": False,
        }
    )
    assert settings.temperature == 0.3
    assert settings.max_tokens == 2048
    assert settings.streaming is False


@pytest.mark.parametrize(
    ("field", "value"),
    [("temperature", "2.1"), ("top_p", "-0.1"), ("context_window", "999")],
)
def test_form_enforces_documented_ranges(field: str, value: str) -> None:
    with pytest.raises(ValueError, match=field):
        parse_llm_settings_form({"model": "model", field: value})
