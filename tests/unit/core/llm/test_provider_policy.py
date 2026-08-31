"""Pure provider-policy contracts."""

from aura_cli.core.llm.provider_policy import (
    provider_policy,
    structural_completion_params,
)


def test_provider_policy_normalizes_provider_and_preset_names() -> None:
    assert provider_policy("gemini/gemini-2.5-flash").name == "gemini"
    assert provider_policy("claude-sonnet-4").preset == "claude"
    assert provider_policy("gpt-4o").key_names == ("OPENAI_API_KEY",)
    assert provider_policy("unknown-model").name == "google"


def test_structural_params_are_pure_and_provider_specific() -> None:
    assert structural_completion_params("gemini/gemini-2.5-pro") == {
        "api_version": "v1",
        "thinking": {"type": "enabled", "budget_tokens": 2048},
    }
    assert structural_completion_params("nvidia/nemotron") == {
        "api_base": "https://integrate.api.nvidia.com/v1"
    }
    assert structural_completion_params("gpt-4o") == {}
