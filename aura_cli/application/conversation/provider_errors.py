"""Provider-neutral classification and presentation of conversation failures."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class ProviderErrorKind(Enum):
    RATE_LIMIT = "rate_limit"
    FREE_TIER_QUOTA = "free_tier_quota"
    AUTHENTICATION = "authentication"
    LEAKED_CREDENTIAL = "leaked_credential"
    CONNECTION = "connection"
    INVALID_REQUEST = "invalid_request"
    MODEL_NOT_FOUND = "model_not_found"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class ProviderErrorResolution:
    kind: ProviderErrorKind
    message: str
    suppression_key: str | None = None
    revoke_credentials: bool = False


def _retry_hint(retry_after: int | None) -> str:
    if not retry_after:
        return ""
    minutes, seconds = divmod(retry_after, 60)
    if minutes:
        return f"\n○  Tente novamente em ~{minutes}min {seconds}s"
    return f"\n○  Tente novamente em ~{seconds}s"


def friendly_provider_error(error: Exception) -> str:
    """Render a stable fallback message from an arbitrary provider exception."""
    error_text = str(error)
    normalized = error_text.lower()
    if "timeout" in normalized or "timed out" in normalized:
        return "▲ Communication timeout\n\nThe request took too long.\n\n▪ Try: waiting and retrying, /model"
    if "connection" in normalized or "network" in normalized:
        return "▲ Connection error\n\nCould not connect to the server.\n\n▪ Check internet or /settings"
    if any(
        marker in normalized
        for marker in (
            "api key",
            "authentication",
            "unauthorized",
            "invalid_api_key",
            "auth",
        )
    ):
        return "▲ Invalid or expired API key\n\n▪ Configure at /settings → API Keys"
    if any(
        marker in normalized
        for marker in (
            "429",
            "rate limit",
            "quota",
            "exceeded",
            "resource_exhausted",
            "too many requests",
        )
    ):
        return "✦ Request limit reached\n\n▪ Wait a few minutes or switch models at /model"
    if "invalid" in normalized or "malformed" in normalized:
        return f"▲ Request error\n\nInvalid format: {error_text[:80]}\n\n▪ Try: /model or restart"
    suffix = "..." if len(error_text) > 100 else ""
    return (
        "▲ Error communicating with model\n\n"
        f"Type: {type(error).__name__}. Details: {error_text[:100]}{suffix}\n\n"
        "▪ Try: ~/.aura/logs/, /model or /settings"
    )


def resolve_provider_error(
    error: Exception,
    *,
    rate_limit: bool = False,
    retry_after: int | None = None,
    model: str | None = None,
) -> ProviderErrorResolution:
    """Classify an exception and produce its user-facing recovery guidance."""
    error_text = str(error)
    normalized = error_text.lower()

    if rate_limit:
        retry_hint = _retry_hint(retry_after)
        if "free_tier" in normalized or "free tier" in normalized:
            heading = "✦ Free Tier Quota Exceeded"
            return ProviderErrorResolution(
                kind=ProviderErrorKind.FREE_TIER_QUOTA,
                message=(
                    f"{heading}\n\nYou have reached the daily limit of the Gemini free plan (20 req/day)."
                    f"{retry_hint}\n\n▪ Try: wait 24h, /settings (another provider) or upgrade at "
                    "ai.google.dev/pricing"
                ),
                suppression_key=heading,
            )
        return ProviderErrorResolution(
            kind=ProviderErrorKind.RATE_LIMIT,
            message=(
                "✦ Usage limit reached\n\nAPI request limit reached "
                f"({model or 'current model'}).{retry_hint}\n\n"
                "▪ Try: wait a few minutes, /model or /settings"
            ),
        )

    if isinstance(error, (ConnectionError, TimeoutError)):
        return ProviderErrorResolution(
            ProviderErrorKind.CONNECTION,
            "▲ Connection error\n\nCould not connect to the server.\n\n▪ Check internet and retry.",
        )
    if isinstance(error, (ValueError, TypeError)):
        if any(
            marker in normalized
            for marker in ("api key", "authentication", "unauthorized")
        ):
            return ProviderErrorResolution(
                ProviderErrorKind.AUTHENTICATION,
                "▲ Authentication error\n\nAPI key rejected.\n\n▪ Try: /settings",
            )
        return ProviderErrorResolution(
            ProviderErrorKind.INVALID_REQUEST,
            f"▲ Request error\n\nInvalid format: {error_text[:80]}\n\n▪ Try: /model or restart",
        )
    if any(
        marker in normalized
        for marker in ("429", "rate limit", "quota", "exceeded", "resource_exhausted")
    ):
        heading = "✦ Free Tier Quota Exceeded"
        if "free_tier" in normalized or "free tier" in normalized:
            return ProviderErrorResolution(
                ProviderErrorKind.FREE_TIER_QUOTA,
                f"{heading}\n\nGemini free plan daily limit (20 req/day).\n\n"
                "▪ Try: wait 24h, /settings or upgrade at ai.google.dev/pricing",
                suppression_key=heading,
            )
        return ProviderErrorResolution(
            ProviderErrorKind.RATE_LIMIT,
            "✦ Usage limit reached\n\nRequest limit reached.\n\n▪ Try: wait, /model or /settings",
        )
    if any(
        marker in normalized
        for marker in ("api key", "403", "permission_denied", "leaked")
    ):
        leaked = "leaked" in normalized
        return ProviderErrorResolution(
            ProviderErrorKind.LEAKED_CREDENTIAL
            if leaked
            else ProviderErrorKind.AUTHENTICATION,
            (
                "▲ Invalid API key\n\nKey deactivated for security.\n\n▪ Try: /settings to add a new key"
                if leaked
                else "▲ Authentication error\n\nAPI key rejected.\n\n▪ Try: /settings"
            ),
            revoke_credentials=leaked,
        )
    if (
        "NotFoundError" in type(error).__name__
        or "not found" in normalized
        or "404" in normalized
    ):
        return ProviderErrorResolution(
            ProviderErrorKind.MODEL_NOT_FOUND,
            "▲ Model not found\n\nThe configured model is not available.\n\n▪ Try: /model or /settings",
        )
    return ProviderErrorResolution(
        ProviderErrorKind.UNKNOWN,
        friendly_provider_error(error),
    )


__all__ = [
    "ProviderErrorKind",
    "ProviderErrorResolution",
    "friendly_provider_error",
    "resolve_provider_error",
]
