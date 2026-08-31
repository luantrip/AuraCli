"""Contract tests for the native Groq provider integration."""

from aura_cli.application.presentation.llm_settings import provider_api_key_name
from aura_cli.cli.utils.worker_readiness import build_worker_readiness
from aura_cli.core.llm.api_validator import (
    ValidationResult,
    ValidationStatus,
    validate_api_key,
)
from aura_cli.core.llm.model_utils import (
    MODEL_PRESETS,
    get_default_model_for_provider,
    get_provider_from_model,
    normalize_model_name,
)
from aura_cli.core.llm.provider_policy import provider_policy
from aura_cli.core.llm.rate_limiter import RateLimiter
from aura_cli.core.llm.tool_schemas import (
    create_llm_config_with_tools,
    detect_provider_and_model,
)


def test_groq_catalog_and_normalization_are_canonical() -> None:
    assert MODEL_PRESETS["groq"] == [
        "groq/openai/gpt-oss-20b",
        "groq/openai/gpt-oss-120b",
    ]
    assert get_default_model_for_provider("groq") == "groq/openai/gpt-oss-20b"
    assert normalize_model_name("groq/openai/gpt-oss-20b") == "groq/openai/gpt-oss-20b"
    assert get_provider_from_model("groq/openai/gpt-oss-120b") == "groq"


def test_groq_policy_uses_groq_credentials() -> None:
    policy = provider_policy("groq/openai/gpt-oss-20b")

    assert policy.name == "groq"
    assert policy.preset == "groq"
    assert policy.runtime_name == "groq"
    assert policy.key_names == ("GROQ_API_KEY",)
    assert provider_api_key_name("groq") == "GROQ_API_KEY"


def test_groq_api_key_validation_is_registered(monkeypatch) -> None:
    expected = ValidationResult(ValidationStatus.SUCCESS, "GroqCloud", "ok")
    monkeypatch.setattr(
        "aura_cli.core.llm.api_validator.validate_groq_api_key",
        lambda api_key: expected,
    )

    assert validate_api_key("groq", "test-key") is expected


def test_groq_rate_limiter_and_readiness_use_groq_credential() -> None:
    limiter = RateLimiter()
    assert limiter._get_provider("groq/openai/gpt-oss-20b") == "groq"

    report = build_worker_readiness(
        worker_type="agi",
        model="groq/openai/gpt-oss-20b",
        api_keys={"GROQ_API_KEY": "configured"},
        project_root=None,
    )
    assert report.ready is True
    assert report.credential_name == "GROQ_API_KEY"


def test_groq_tool_schema_preserves_nested_model_id() -> None:
    provider, model = detect_provider_and_model("groq/openai/gpt-oss-20b")
    config = create_llm_config_with_tools("groq/openai/gpt-oss-20b", "test-key")

    assert (provider, model) == ("groq", "openai/gpt-oss-20b")
    assert config["config_list"][0]["api_type"] == "groq"
    assert config["config_list"][0]["model"] == "openai/gpt-oss-20b"
