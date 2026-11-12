from aura_cli.core import api_key_store
from aura_cli.core.llm import model_utils
from aura_cli.core.llm.provider_policy import provider_policy
from aura_cli.core.llm.provider_spec import (
    PROVIDER_SPECS,
    env_keys_for,
    provider_by_any_name,
    provider_by_catalog,
    provider_by_id,
)


def test_spec_ids_and_catalog_names_are_unique() -> None:
    assert len({s.id for s in PROVIDER_SPECS}) == len(PROVIDER_SPECS)
    assert len({s.catalog for s in PROVIDER_SPECS}) == len(PROVIDER_SPECS)


def test_every_spec_has_a_primary_env_key() -> None:
    for spec in PROVIDER_SPECS:
        assert spec.env_keys and spec.primary_env_key == spec.env_keys[0]


def test_lookups_are_case_and_space_insensitive() -> None:
    assert provider_by_id("  Google ").catalog == "gemini"
    assert provider_by_catalog("GPT").id == "openai"
    assert provider_by_any_name("claude").id == "anthropic"
    assert provider_by_any_name("anthropic").catalog == "claude"
    assert provider_by_any_name("nope") is None
    assert provider_by_id("") is None


def test_env_keys_for_accepts_either_vocabulary() -> None:
    assert env_keys_for("google") == env_keys_for("gemini") == (
        "GOOGLE_API_KEY",
        "GEMINI_API_KEY",
    )
    assert env_keys_for("unknown") == ()


def test_legacy_tables_are_derived_from_the_spec() -> None:
    """The four historical tables must stay views of ProviderSpec."""
    assert [p[0] for p in api_key_store.API_PROVIDERS] == [s.id for s in PROVIDER_SPECS]
    for spec in PROVIDER_SPECS:
        assert api_key_store.PROVIDER_ENV_KEYS[spec.id] == list(spec.env_keys)
        assert model_utils.PROVIDER_ENV_KEYS[spec.catalog] == spec.primary_env_key
        assert model_utils.PROVIDER_ALIASES[spec.id] == spec.catalog
        assert model_utils.PROVIDER_ALIASES[spec.catalog] == spec.catalog


def test_provider_policy_key_names_come_from_the_spec() -> None:
    samples = {
        "gemini/gemini-2.5-flash": "google",
        "cerebras/gpt-oss-120b": "cerebras",
        "groq/openai/gpt-oss-20b": "groq",
        "claude-sonnet-4-6": "anthropic",
        "gpt-4o": "openai",
        "openrouter/free": "openrouter",
        "nvidia/nvidia/nemotron": "nvidia",
    }
    for model, provider_id in samples.items():
        assert provider_policy(model).key_names == env_keys_for(provider_id), model
