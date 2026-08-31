"""
API Key Validator for Aura CLI.

This module provides functions to test and validate API keys for all supported
LLM providers before they are saved. This ensures users get immediate feedback
about whether their keys are working.

Supported Providers:
    - Google (Gemini)
    - OpenAI (GPT)
    - Anthropic (Claude)
    - OpenRouter (13+ free models)
    - Cerebras (GPT OSS)
    - GroqCloud (GPT OSS)
    - Cursor (Cloud Agents API)
"""

from dataclasses import dataclass
from enum import Enum
import os
from typing import Optional, Tuple

from aura_cli.core.llm.model_utils import normalize_provider_name

_logger = None


def _get_logger():
    """
    Lazy import of logger.

    Returns:
        Logger instance for this module

    Note:
        Uses lazy initialization to prevent circular dependencies during
        module import.
    """
    global _logger
    if _logger is None:
        from aura_cli.core.logger import get_logger

        _logger = get_logger(__name__)
    return _logger


class ValidationStatus(Enum):
    """Status of API key validation."""

    SUCCESS = "success"
    INVALID_KEY = "invalid_key"
    RATE_LIMITED = "rate_limited"
    NETWORK_ERROR = "network_error"
    TIMEOUT = "timeout"
    UNKNOWN_ERROR = "unknown_error"


@dataclass
class ValidationResult:
    """Result of API key validation."""

    status: ValidationStatus
    provider: str
    message: str
    model_tested: Optional[str] = None
    response_preview: Optional[str] = None


def validate_google_api_key(api_key: str) -> ValidationResult:
    """
    Validate Google (Gemini) API key by making a minimal API call.

    Args:
        api_key: The Google API key to validate

    Returns:
        ValidationResult with status and message
    """
    provider = "Google (Gemini)"
    model = "gemini/gemma-4-27b-it"

    try:
        import litellm

        original_key = os.environ.get("GOOGLE_API_KEY")
        os.environ["GOOGLE_API_KEY"] = api_key
        os.environ["GEMINI_API_KEY"] = api_key

        try:
            response = litellm.completion(
                model=model,
                messages=[{"role": "user", "content": "Hi"}],
                max_tokens=5,
                timeout=15.0,
            )

            if response and response.choices and len(response.choices) > 0:
                preview = (
                    response.choices[0].message.content[:50]
                    if response.choices[0].message.content
                    else "OK"
                )
                return ValidationResult(
                    status=ValidationStatus.SUCCESS,
                    provider=provider,
                    message="✅ API Key válida e funcionando!",
                    model_tested=model,
                    response_preview=preview,
                )
            else:
                return ValidationResult(
                    status=ValidationStatus.UNKNOWN_ERROR,
                    provider=provider,
                    message="⚠️ Resposta vazia do modelo",
                    model_tested=model,
                )

        finally:
            if original_key:
                os.environ["GOOGLE_API_KEY"] = original_key
                os.environ["GEMINI_API_KEY"] = original_key
            else:
                os.environ.pop("GOOGLE_API_KEY", None)
                os.environ.pop("GEMINI_API_KEY", None)

    except Exception as e:
        error_str = str(e).lower()

        if (
            "api key" in error_str
            or "invalid" in error_str
            or "403" in error_str
            or "401" in error_str
        ):
            return ValidationResult(
                status=ValidationStatus.INVALID_KEY,
                provider=provider,
                message=f"❌ API Key inválida: {str(e)[:100]}",
                model_tested=model,
            )
        elif "429" in error_str or "rate" in error_str or "quota" in error_str:
            return ValidationResult(
                status=ValidationStatus.RATE_LIMITED,
                provider=provider,
                message="⚠️ API Key válida, mas com limite de uso atingido",
                model_tested=model,
            )
        elif "timeout" in error_str:
            return ValidationResult(
                status=ValidationStatus.TIMEOUT,
                provider=provider,
                message="⚠️ Timeout na conexão (pode estar funcionando)",
                model_tested=model,
            )
        elif "connection" in error_str or "network" in error_str:
            return ValidationResult(
                status=ValidationStatus.NETWORK_ERROR,
                provider=provider,
                message="❌ Erro de conexão - verifique sua internet",
                model_tested=model,
            )
        else:
            return ValidationResult(
                status=ValidationStatus.UNKNOWN_ERROR,
                provider=provider,
                message=f"❌ Erro: {str(e)[:100]}",
                model_tested=model,
            )


def validate_openai_api_key(api_key: str) -> ValidationResult:
    """
    Validate OpenAI API key by making a minimal API call.

    Args:
        api_key: The OpenAI API key to validate

    Returns:
        ValidationResult with status and message
    """
    provider = "OpenAI (GPT)"
    model = "gpt-4o-mini"  # Use cheaper model for testing

    try:
        import litellm

        original_key = os.environ.get("OPENAI_API_KEY")
        os.environ["OPENAI_API_KEY"] = api_key

        try:
            response = litellm.completion(
                model=model,
                messages=[{"role": "user", "content": "Hi"}],
                max_tokens=5,
                timeout=15.0,
            )

            if response and response.choices and len(response.choices) > 0:
                preview = (
                    response.choices[0].message.content[:50]
                    if response.choices[0].message.content
                    else "OK"
                )
                return ValidationResult(
                    status=ValidationStatus.SUCCESS,
                    provider=provider,
                    message="✅ API Key válida e funcionando!",
                    model_tested=model,
                    response_preview=preview,
                )
            else:
                return ValidationResult(
                    status=ValidationStatus.UNKNOWN_ERROR,
                    provider=provider,
                    message="⚠️ Resposta vazia do modelo",
                    model_tested=model,
                )

        finally:
            if original_key:
                os.environ["OPENAI_API_KEY"] = original_key
            else:
                os.environ.pop("OPENAI_API_KEY", None)

    except Exception as e:
        error_str = str(e).lower()

        if (
            "api key" in error_str
            or "invalid" in error_str
            or "401" in error_str
            or "incorrect" in error_str
        ):
            return ValidationResult(
                status=ValidationStatus.INVALID_KEY,
                provider=provider,
                message=f"❌ API Key inválida: {str(e)[:100]}",
                model_tested=model,
            )
        elif "429" in error_str or "rate" in error_str or "quota" in error_str:
            return ValidationResult(
                status=ValidationStatus.RATE_LIMITED,
                provider=provider,
                message="⚠️ API Key válida, mas com limite de uso atingido",
                model_tested=model,
            )
        elif "timeout" in error_str:
            return ValidationResult(
                status=ValidationStatus.TIMEOUT,
                provider=provider,
                message="⚠️ Timeout na conexão (pode estar funcionando)",
                model_tested=model,
            )
        else:
            return ValidationResult(
                status=ValidationStatus.UNKNOWN_ERROR,
                provider=provider,
                message=f"❌ Erro: {str(e)[:100]}",
                model_tested=model,
            )


def validate_anthropic_api_key(api_key: str) -> ValidationResult:
    """
    Validate Anthropic (Claude) API key by making a minimal API call.

    Args:
        api_key: The Anthropic API key to validate

    Returns:
        ValidationResult with status and message
    """
    provider = "Anthropic (Claude)"
    model = "claude-haiku-4-5-20251001"  # Use cheaper model for testing

    try:
        import litellm

        original_key = os.environ.get("ANTHROPIC_API_KEY")
        os.environ["ANTHROPIC_API_KEY"] = api_key

        try:
            response = litellm.completion(
                model=model,
                messages=[{"role": "user", "content": "Hi"}],
                max_tokens=5,
                timeout=15.0,
            )

            if response and response.choices and len(response.choices) > 0:
                preview = (
                    response.choices[0].message.content[:50]
                    if response.choices[0].message.content
                    else "OK"
                )
                return ValidationResult(
                    status=ValidationStatus.SUCCESS,
                    provider=provider,
                    message="✅ API Key válida e funcionando!",
                    model_tested=model,
                    response_preview=preview,
                )
            else:
                return ValidationResult(
                    status=ValidationStatus.UNKNOWN_ERROR,
                    provider=provider,
                    message="⚠️ Resposta vazia do modelo",
                    model_tested=model,
                )

        finally:
            if original_key:
                os.environ["ANTHROPIC_API_KEY"] = original_key
            else:
                os.environ.pop("ANTHROPIC_API_KEY", None)

    except Exception as e:
        error_str = str(e).lower()
        error_full = str(e)

        if "credit" in error_str or "balance" in error_str or "too low" in error_str:
            return ValidationResult(
                status=ValidationStatus.RATE_LIMITED,  # Treat as rate limited to allow saving
                provider=provider,
                message="⚠️ API Key válida, mas conta sem créditos.\n\n"
                "💡 Acesse https://console.anthropic.com/settings/plans para adicionar créditos.\n"
                "Você pode salvar a chave agora e usar quando tiver créditos.",
                model_tested=model,
            )
        elif (
            "api key" in error_str
            or "invalid" in error_str
            or "401" in error_str
            or "authentication" in error_str
        ):
            return ValidationResult(
                status=ValidationStatus.INVALID_KEY,
                provider=provider,
                message="❌ API Key inválida ou expirada.\n\nVerifique se a chave está correta em https://console.anthropic.com/settings/keys",
                model_tested=model,
            )
        elif "429" in error_str or "rate" in error_str:
            return ValidationResult(
                status=ValidationStatus.RATE_LIMITED,
                provider=provider,
                message="⚠️ API Key válida, mas com limite de uso atingido",
                model_tested=model,
            )
        elif "timeout" in error_str:
            return ValidationResult(
                status=ValidationStatus.TIMEOUT,
                provider=provider,
                message="⚠️ Timeout na conexão (pode estar funcionando)",
                model_tested=model,
            )
        else:
            if "badrequest" in error_str and (
                "credit" in error_full.lower() or "balance" in error_full.lower()
            ):
                return ValidationResult(
                    status=ValidationStatus.RATE_LIMITED,
                    provider=provider,
                    message="⚠️ API Key válida, mas conta sem créditos.\n\n"
                    "💡 Acesse https://console.anthropic.com/settings/plans para adicionar créditos.\n"
                    "Você pode salvar a chave agora e usar quando tiver créditos.",
                    model_tested=model,
                )
            return ValidationResult(
                status=ValidationStatus.UNKNOWN_ERROR,
                provider=provider,
                message=f"❌ Erro: {error_full[:200]}",
                model_tested=model,
            )


def validate_openrouter_api_key(api_key: str) -> ValidationResult:
    """
    Validate OpenRouter API key by making a minimal API call.

    Args:
        api_key: The OpenRouter API key to validate

    Returns:
        ValidationResult with status and message
    """
    provider = "OpenRouter"
    model = "openrouter/nvidia/nemotron-3-super-120b-a12b:free"

    try:
        import litellm

        original_key = os.environ.get("OPENROUTER_API_KEY")
        os.environ["OPENROUTER_API_KEY"] = api_key

        try:
            response = litellm.completion(
                model=model,
                messages=[{"role": "user", "content": "Hi"}],
                max_tokens=5,
                timeout=15.0,
            )

            if response and response.choices and len(response.choices) > 0:
                preview = (
                    response.choices[0].message.content[:50]
                    if response.choices[0].message.content
                    else "OK"
                )
                return ValidationResult(
                    status=ValidationStatus.SUCCESS,
                    provider=provider,
                    message="✅ API Key válida e funcionando!",
                    model_tested=model,
                    response_preview=preview,
                )
            else:
                return ValidationResult(
                    status=ValidationStatus.UNKNOWN_ERROR,
                    provider=provider,
                    message="⚠️ Resposta vazia do modelo",
                    model_tested=model,
                )

        finally:
            if original_key:
                os.environ["OPENROUTER_API_KEY"] = original_key
            else:
                os.environ.pop("OPENROUTER_API_KEY", None)

    except Exception as e:
        error_str = str(e).lower()

        if (
            "api key" in error_str
            or "invalid" in error_str
            or "401" in error_str
            or "unauthorized" in error_str
        ):
            return ValidationResult(
                status=ValidationStatus.INVALID_KEY,
                provider=provider,
                message=f"❌ API Key inválida: {str(e)[:100]}",
                model_tested=model,
            )
        elif "429" in error_str or "rate" in error_str:
            return ValidationResult(
                status=ValidationStatus.RATE_LIMITED,
                provider=provider,
                message="⚠️ API Key válida, mas com limite de uso atingido",
                model_tested=model,
            )
        elif "timeout" in error_str:
            return ValidationResult(
                status=ValidationStatus.TIMEOUT,
                provider=provider,
                message="⚠️ Timeout na conexão (pode estar funcionando)",
                model_tested=model,
            )
        else:
            return ValidationResult(
                status=ValidationStatus.UNKNOWN_ERROR,
                provider=provider,
                message=f"❌ Erro: {str(e)[:100]}",
                model_tested=model,
            )


def validate_nvidia_api_key(api_key: str) -> ValidationResult:
    """
    Validate NVIDIA API Catalog key (nvapi-...) using Nemotron Super 49B.

    Args:
        api_key: The NVIDIA API key to validate

    Returns:
        ValidationResult with status and message
    """
    provider = "NVIDIA (Nemotron)"
    model = "nvidia/nvidia/nemotron-3.5-lightning-30b-a3b"

    try:
        import litellm

        original_key = os.environ.get("NVIDIA_API_KEY")
        os.environ["NVIDIA_API_KEY"] = api_key

        try:
            response = litellm.completion(
                model=model,
                messages=[{"role": "user", "content": "Hi"}],
                max_tokens=5,
                timeout=15.0,
                api_base="https://integrate.api.nvidia.com/v1",
                api_key=api_key,
            )

            if response and response.choices and len(response.choices) > 0:
                preview = (
                    response.choices[0].message.content[:50]
                    if response.choices[0].message.content
                    else "OK"
                )
                return ValidationResult(
                    status=ValidationStatus.SUCCESS,
                    provider=provider,
                    message="✅ NVIDIA API Key válida e funcionando!",
                    model_tested=model,
                    response_preview=preview,
                )
            else:
                return ValidationResult(
                    status=ValidationStatus.UNKNOWN_ERROR,
                    provider=provider,
                    message="⚠️ Resposta vazia do modelo",
                    model_tested=model,
                )

        finally:
            if original_key:
                os.environ["NVIDIA_API_KEY"] = original_key
            else:
                os.environ.pop("NVIDIA_API_KEY", None)

    except Exception as e:
        error_str = str(e).lower()

        if "401" in error_str or "unauthorized" in error_str or "invalid" in error_str:
            return ValidationResult(
                status=ValidationStatus.INVALID_KEY,
                provider=provider,
                message=f"❌ API Key inválida: {str(e)[:100]}",
                model_tested=model,
            )
        elif "429" in error_str or "rate" in error_str:
            return ValidationResult(
                status=ValidationStatus.RATE_LIMITED,
                provider=provider,
                message="⚠️ API Key válida, mas com limite de uso atingido",
                model_tested=model,
            )
        elif "timeout" in error_str:
            return ValidationResult(
                status=ValidationStatus.TIMEOUT,
                provider=provider,
                message="⚠️ Timeout na conexão (pode estar funcionando)",
                model_tested=model,
            )
        else:
            return ValidationResult(
                status=ValidationStatus.UNKNOWN_ERROR,
                provider=provider,
                message=f"❌ Erro: {str(e)[:100]}",
                model_tested=model,
            )


def validate_groq_api_key(api_key: str) -> ValidationResult:
    """Validate a GroqCloud API key with the free-tier GPT OSS model."""
    provider = "GroqCloud"
    model = "groq/openai/gpt-oss-20b"

    try:
        import litellm

        original_key = os.environ.get("GROQ_API_KEY")
        os.environ["GROQ_API_KEY"] = api_key
        try:
            response = litellm.completion(
                model=model,
                messages=[{"role": "user", "content": "Reply with OK."}],
                max_tokens=8,
                timeout=15.0,
                api_key=api_key,
            )
            if response and response.choices:
                content = response.choices[0].message.content or "OK"
                return ValidationResult(
                    status=ValidationStatus.SUCCESS,
                    provider=provider,
                    message="✅ Groq API Key válida e funcionando!",
                    model_tested=model,
                    response_preview=content[:50],
                )
            return ValidationResult(
                status=ValidationStatus.UNKNOWN_ERROR,
                provider=provider,
                message="⚠️ Resposta vazia do modelo",
                model_tested=model,
            )
        finally:
            if original_key:
                os.environ["GROQ_API_KEY"] = original_key
            else:
                os.environ.pop("GROQ_API_KEY", None)
    except Exception as exc:
        error = str(exc)
        lowered = error.lower()
        if "401" in lowered or "api key" in lowered or "unauthorized" in lowered:
            status = ValidationStatus.INVALID_KEY
            message = f"❌ API Key Groq inválida: {error[:100]}"
        elif "429" in lowered or "rate" in lowered:
            status = ValidationStatus.RATE_LIMITED
            message = "⚠️ API Key Groq válida, mas com limite de uso atingido"
        elif "timeout" in lowered:
            status = ValidationStatus.TIMEOUT
            message = "⚠️ Timeout na conexão (pode estar funcionando)"
        else:
            status = ValidationStatus.UNKNOWN_ERROR
            message = f"❌ Erro Groq: {error[:100]}"
        return ValidationResult(
            status=status,
            provider=provider,
            message=message,
            model_tested=model,
        )


def validate_api_key(provider: str, api_key: str) -> ValidationResult:
    """
    Validate an API key for any supported provider.

    Args:
        provider: Provider name (google, openai, anthropic, openrouter)
        api_key: The API key to validate

    Returns:
        ValidationResult with status and message
    """
    validators = {
        "gemini": validate_google_api_key,
        "gpt": validate_openai_api_key,
        "claude": validate_anthropic_api_key,
        "openrouter": validate_openrouter_api_key,
        "nvidia": validate_nvidia_api_key,
        "groq": validate_groq_api_key,
    }

    validator = validators.get(normalize_provider_name(provider))
    if not validator:
        return ValidationResult(
            status=ValidationStatus.UNKNOWN_ERROR,
            provider=provider,
            message=f"❌ Provedor não suportado: {provider}",
        )

    return validator(api_key)


def quick_test_api_key(
    provider: str, api_key: str, timeout: float = 10.0
) -> Tuple[bool, str]:
    """
    Quick test of API key validity.

    Args:
        provider: Provider name (google, openai, anthropic, openrouter)
        api_key: The API key to test
        timeout: Maximum time to wait for response

    Returns:
        Tuple of (success: bool, message: str)
    """
    result = validate_api_key(provider, api_key)

    if (
        result.status == ValidationStatus.SUCCESS
        or result.status == ValidationStatus.RATE_LIMITED
        or result.status == ValidationStatus.TIMEOUT
    ):
        return True, result.message
    else:
        return False, result.message
