"""Tests for provider-neutral error classification."""

import pytest

from aura_cli.application.conversation.provider_errors import (
    ProviderErrorKind,
    friendly_provider_error,
    resolve_provider_error,
)


@pytest.mark.parametrize(
    ("error", "expected"),
    [
        (TimeoutError("slow"), ProviderErrorKind.CONNECTION),
        (ValueError("malformed request"), ProviderErrorKind.INVALID_REQUEST),
        (ValueError("invalid api key"), ProviderErrorKind.AUTHENTICATION),
        (RuntimeError("429 quota exceeded"), ProviderErrorKind.RATE_LIMIT),
        (RuntimeError("credential leaked"), ProviderErrorKind.LEAKED_CREDENTIAL),
        (RuntimeError("model not found"), ProviderErrorKind.MODEL_NOT_FOUND),
        (RuntimeError("unexpected"), ProviderErrorKind.UNKNOWN),
    ],
)
def test_resolve_provider_error_classifies_failures(
    error: Exception, expected: ProviderErrorKind
) -> None:
    assert resolve_provider_error(error).kind is expected


def test_typed_free_tier_error_carries_suppression_and_retry_guidance() -> None:
    resolution = resolve_provider_error(
        RuntimeError("free_tier exhausted"),
        rate_limit=True,
        retry_after=75,
        model="gemini",
    )

    assert resolution.kind is ProviderErrorKind.FREE_TIER_QUOTA
    assert resolution.suppression_key == "✦ Free Tier Quota Exceeded"
    assert "~1min 15s" in resolution.message


def test_leaked_credential_requests_revocation() -> None:
    assert resolve_provider_error(RuntimeError("API key leaked")).revoke_credentials


def test_friendly_fallback_keeps_error_type_and_truncates_details() -> None:
    message = friendly_provider_error(RuntimeError("x" * 120))
    assert "RuntimeError" in message
    assert "..." in message
