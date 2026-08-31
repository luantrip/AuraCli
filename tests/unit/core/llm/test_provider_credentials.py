"""Credential adapter contracts."""

from aura_cli.core.llm import key_rotation
from aura_cli.core.llm.provider_credentials import prepare_provider_credentials


def test_prepare_credentials_configures_rotation_without_mutating_input() -> None:
    source = {
        "GOOGLE_API_KEY": "first, second",
        "OPENROUTER_API_KEY": "router-a,router-b",
    }

    prepared = prepare_provider_credentials(source)

    assert prepared == source
    assert key_rotation.next_key("google") == "first"
    assert key_rotation.next_key("google") == "second"
    assert key_rotation.next_key("openrouter") == "router-a"


def test_prepare_credentials_ignores_empty_values() -> None:
    key_rotation.register_keys("google", "stale")

    assert prepare_provider_credentials({"OPENAI_API_KEY": ""}) == {}
    assert key_rotation.next_key("google") is None
