"""
Language Model (LLM) Integration Module for Aura CLI.

Provides abstraction layer for LLM providers (Gemini, OpenAI, Anthropic).
Uses lazy imports to avoid loading litellm (~20s) until actually needed.

Usage:
    >>> from aura_cli.core.llm import query_with_fallback
    >>> response = query_with_fallback("gemini/gemini-2.5-flash", messages)
"""

from aura_cli.core.llm.model_utils import (
    DEFAULT_MODEL,
    format_model_display_name,
    get_default_model_for_provider,
    get_model_catalog,
    get_models_for_provider,
    normalize_model_name,
    normalize_provider_name,
    resolve_model_option,
)


def __getattr__(name):
    """Lazy-load heavy modules only when accessed."""
    _base_exports = {
        "estimate_tokens",
        "get_recommended_model",
        "query_with_fallback",
        "truncate_conversation",
    }
    _profile_exports = {
        "ModelProfileManager",
        "get_profile_manager",
        "reset_profile_manager",
    }
    _multi_exports = {
        "EnsembleResult",
        "ModelQuality",
        "ModelResponse",
        "MultiModelIntelligence",
        "compare_model_responses",
        "query_multiple_models",
        "smart_model_query",
    }
    _advanced_exports = {
        "AdvancedMultiModelIntelligence",
        "ModelPreferenceLearner",
        "ResponseCache",
        "get_model_recommendation",
        "smart_query_with_learning",
    }
    _rate_exports = {
        "ProviderLimits",
        "RateLimiter",
        "get_rate_limiter",
    }
    _tool_exports = {
        "create_llm_config_with_tools",
        "create_tool_schemas",
        "detect_provider_and_model",
        "extract_function_schema",
    }
    if name in _base_exports:
        from aura_cli.core.llm.base import (
            estimate_tokens,
            get_recommended_model,
            query_with_fallback,
            truncate_conversation,
        )

        return locals()[name]
    if name in _profile_exports:
        from aura_cli.core.llm.model_profiles import (
            ModelProfileManager,
            get_profile_manager,
            reset_profile_manager,
        )

        return locals()[name]
    if name in _multi_exports:
        from aura_cli.core.llm.multi_model import (
            EnsembleResult,
            ModelQuality,
            ModelResponse,
            MultiModelIntelligence,
            compare_model_responses,
            query_multiple_models,
            smart_model_query,
        )

        return locals()[name]
    if name in _advanced_exports:
        from aura_cli.core.llm.multi_model_advanced import (
            AdvancedMultiModelIntelligence,
            ModelPreferenceLearner,
            ResponseCache,
            get_model_recommendation,
            smart_query_with_learning,
        )

        return locals()[name]
    if name in _rate_exports:
        from aura_cli.core.llm.rate_limiter import (
            ProviderLimits,
            RateLimiter,
            get_rate_limiter,
        )

        return locals()[name]
    if name in _tool_exports:
        from aura_cli.core.llm.tool_schemas import (
            create_llm_config_with_tools,
            create_tool_schemas,
            detect_provider_and_model,
            extract_function_schema,
        )

        return locals()[name]
    raise AttributeError(f"module 'aura_cli.core.llm' has no attribute {name!r}")


__all__ = [
    "AdvancedMultiModelIntelligence",
    "EnsembleResult",
    "ModelPreferenceLearner",
    "ModelProfileManager",
    "ModelQuality",
    "ModelResponse",
    "MultiModelIntelligence",
    "ProviderLimits",
    "RateLimiter",
    "ResponseCache",
    "compare_model_responses",
    "create_llm_config_with_tools",
    "create_tool_schemas",
    "detect_provider_and_model",
    "estimate_tokens",
    "extract_function_schema",
    "format_model_display_name",
    "get_default_model_for_provider",
    "get_model_catalog",
    "get_model_recommendation",
    "get_models_for_provider",
    "get_profile_manager",
    "get_rate_limiter",
    "get_recommended_model",
    "normalize_model_name",
    "normalize_provider_name",
    "query_multiple_models",
    "query_with_fallback",
    "reset_profile_manager",
    "resolve_model_option",
    "smart_model_query",
    "smart_query_with_learning",
    "truncate_conversation",
]
