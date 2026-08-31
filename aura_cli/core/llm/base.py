"""Base module for LLM interaction in Aura CLI via LiteLLM.

Provides query_with_fallback() (automatic per-provider fallback + exponential
backoff retry), truncate_conversation() (token-aware history trimming),
get_recommended_model() (task-type routing), and function-calling helpers.
MODEL_PRESETS defines per-provider fallback lists.
"""

import contextlib
import io
import os
import re
import threading
import time
from typing import Any, Dict, List, Optional
from uuid import uuid4

from aura_cli.core.constants import (
    DEFAULT_LLM_TIMEOUT,
    FALLBACK_CHARS_PER_TOKEN,
    MAX_BACKOFF_SECONDS,
    MAX_LLM_RETRIES,
)
from aura_cli.core.exceptions import RateLimitError
from aura_cli.core.llm.model_utils import (
    DEFAULT_MODEL,
    get_default_model_for_provider,
    get_models_for_provider,
    normalize_model_name,
    normalize_provider_name,
)
from aura_cli.core.llm.provider_policy import (
    provider_policy,
    structural_completion_params,
)
from aura_cli.core.llm.rate_limiter import get_rate_limiter
from aura_cli.core.logger import get_logger

_thread_local = threading.local()

_LLM_ENV_KEYS = [
    "GOOGLE_API_KEY",
    "GEMINI_API_KEY",
    "OPENAI_API_KEY",
    "ANTHROPIC_API_KEY",
    "OPENROUTER_API_KEY",
    "NVIDIA_API_KEY",
    "CEREBRAS_API_KEY",
    "GROQ_API_KEY",
    "GEMINI_API_VERSION",
    "GOOGLE_API_VERSION",
]

# Lazy-loaded heavy dependencies
_litellm = None
_console = None
_litellm_configured = False


def _get_litellm():
    """Lazy-load litellm on first use (~6s import)."""
    global _litellm, _litellm_configured
    if _litellm is None:
        import litellm

        _litellm = litellm
    if not _litellm_configured:
        _litellm.api_version = "v1"
        _litellm.vertex_ai_api_version = "v1"
        _litellm.set_verbose = False
        _litellm.suppress_debug_info = True
        _litellm.drop_params = True
        _litellm_configured = True
    return _litellm


def _get_console():
    """Lazy-load Rich Console on first use."""
    global _console
    if _console is None:
        from rich.console import Console

        _console = Console()
    return _console


logger = get_logger(__name__)

from aura_cli.application.execution_feedback import (
    LoadingState,
    show_llm_feedback,
)
from aura_cli.core.llm.circuit_breaker import get_circuit_breaker


def __getattr__(name):
    """Expose lazy-loaded modules as attributes for backward compat (mock.patch)."""
    if name == "litellm":
        return _get_litellm()
    if name == "console":
        return _get_console()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def get_llm_client():
    """
    Returns a simple synchronous/async LLM client wrapping query_with_fallback.

    Used by paint_tools and other modules that need a lightweight client object
    rather than calling query_with_fallback directly.

    Returns an object with:
        .query(model, messages, **kwargs) -> str
        .query_async(model, messages, **kwargs) -> Awaitable[str]
    """

    class _SimpleLLMClient:
        """Thin client providing .query / .query_async over query_with_fallback."""

        def query(self, model: str, messages: list, **kwargs):
            """Synchronous query using the fallback chain."""
            return query_with_fallback(model, messages, **kwargs)

        async def query_async(self, model: str, messages: list, **kwargs):
            """Async query — runs sync fallback in a thread pool."""
            import asyncio

            return await asyncio.to_thread(
                query_with_fallback, model, messages, **kwargs
            )

    return _SimpleLLMClient()


def _capture_env(keys: List[str]) -> Dict[str, Optional[str]]:
    """Capture selected environment variables for later restoration."""
    return {key: os.environ.get(key) for key in keys}


def _restore_env(snapshot: Dict[str, Optional[str]]) -> None:
    """Restore environment variables from snapshot."""
    for key, value in snapshot.items():
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = value


def _execute_llm_call(
    current_model: str,
    messages: List[Dict[str, str]],
    completion_params: Dict[str, Any],
    loading: Optional[Any] = None,
) -> Any:
    """
    Execute a single LLM API call with circuit breaker protection.

    Args:
        current_model: Model name to use
        messages: Conversation messages
        completion_params: Parameters for LiteLLM completion
        loading: Optional loading indicator

    Returns:
        LLM response

    Raises:
        Exception: If call fails or circuit breaker is open
    """
    if not current_model:
        current_model = DEFAULT_MODEL

    model_lower = current_model.lower()
    current_provider = provider_policy(model_lower).runtime_name

    if (
        current_provider == "openrouter"
        and completion_params.get("stream") is True
        and completion_params.get("tools")
    ):
        completion_params["stream"] = False
    current_model = (
        normalize_model_name(current_model) or current_model
        if current_model
        else DEFAULT_MODEL
    )

    current_circuit_breaker = get_circuit_breaker(current_provider)

    def _make_llm_call():
        """
        Execute LLM call with stderr suppression.

        Captures and logs LiteLLM stderr output without displaying it to console,
        as it may contain verbose debug information.

        Returns:
            LiteLLM completion response

        Raises:
            Exception: Any exception from litellm.completion()
        """
        stderr_capture = io.StringIO()
        with contextlib.redirect_stderr(stderr_capture):
            try:
                return _get_litellm().completion(**completion_params)
            except Exception:
                captured_stderr = stderr_capture.getvalue()
                if captured_stderr:
                    logger.debug(
                        f"LiteLLM stderr (suppressed from console): {captured_stderr}"
                    )
                raise

    try:
        response = current_circuit_breaker.call(_make_llm_call)
        return response
    except Exception as circuit_error:
        if "Circuit breaker is OPEN" in str(circuit_error):
            logger.warning(
                f"Circuit breaker OPEN for {current_provider}. "
                f"Skipping {current_model}. Error: {circuit_error}"
            )
        raise


def _should_retry(error: Exception, attempt: int, max_retries: int) -> bool:
    """
    Determine if an error should trigger a retry.

    Args:
        error: The exception that occurred
        attempt: Current attempt number (0-indexed)
        max_retries: Maximum number of retries

    Returns:
        True if should retry, False otherwise
    """
    if attempt >= max_retries - 1:
        return False

    return _is_retryable_error(error)


def _is_retryable_error(error: Exception) -> bool:
    """Check if an error is transient and eligible for retry/fallback."""
    error_str = str(error).lower()
    is_503 = "503" in str(error) or "overloaded" in error_str
    is_429 = "429" in str(error) or "rate limit" in error_str or "quota" in error_str
    is_timeout = "timeout" in error_str

    return is_503 or is_429 or is_timeout


def _calculate_backoff(attempt: int) -> float:
    """
    Calculate backoff delay for retry.

    Args:
        attempt: Current attempt number (0-indexed)

    Returns:
        Backoff delay in seconds (capped at MAX_BACKOFF_SECONDS)
    """
    return min(2**attempt, MAX_BACKOFF_SECONDS)


def _handle_llm_error(
    error: Exception,
    current_model: str,
    attempt: int,
    max_retries: int,
    loading: Optional[Any] = None,
) -> None:
    """
    Handle LLM error and prepare for retry if applicable.

    Args:
        error: The exception that occurred
        current_model: Model name that failed
        attempt: Current attempt number
        max_retries: Maximum retries
        loading: Optional loading indicator
    """
    error_str = str(error).lower()
    is_503 = "503" in str(error) or "overloaded" in error_str
    is_429 = "429" in str(error) or "rate limit" in error_str or "quota" in error_str
    is_timeout = "timeout" in error_str

    if is_503 or is_429 or is_timeout:
        if attempt < max_retries - 1:
            backoff = _calculate_backoff(attempt)
            if loading:
                loading.update(
                    LoadingState.PROCESSING,
                    f"Aguardando {backoff}s...",
                )
            logger.debug(
                f"Erro recuperável ({current_model}): {error}. "
                f"Retry {attempt + 1}/{max_retries} em {backoff}s"
            )
            time.sleep(backoff)
    else:
        logger.warning(f"Erro não recuperável ({current_model}): {error}")


def _setup_api_keys() -> None:
    """Load API keys into request-local storage without mutating the environment."""
    try:
        from aura_cli.core.llm.provider_credentials import load_provider_credentials

        _thread_local.api_keys = load_provider_credentials()
    except Exception as e:
        logger.debug(f"Error loading API keys: {e}")


def _resolve_model(model: str, messages: List[Dict[str, str]]) -> str:
    """Normalize model name and auto-select via TaskRouter when 'auto'.

    Uses TaskRouter.select_model() as the single entry point for model
    selection. TaskRouter internally consults ModelProfileManager for user
    preferences before falling back to its task-type mapping.
    """
    model = normalize_model_name(model) or model
    if model in ("auto", ""):
        try:
            from aura_cli.core.llm.task_router import get_task_router

            prompt_text = next(
                (
                    m.get("content", "")
                    for m in reversed(messages)
                    if m.get("role") == "user"
                ),
                "",
            )
            model = get_task_router().select_model(prompt_text)
            logger.debug(f"TaskRouter.select_model selecionou: {model}")
        except Exception as e:
            logger.debug(f"TaskRouter indisponível: {e}")
            model = DEFAULT_MODEL
    return model or DEFAULT_MODEL


def _detect_provider(model_lower: str) -> Optional[str]:
    """Detect the LLM provider from a normalised model name string."""
    return provider_policy(model_lower).name


def _build_models_list(
    model: str,
    fallback_models: Optional[List[str]],
    cross_provider_fallback: bool,
) -> List[str]:
    """Build ordered list of models to try: primary → same-provider → cross-provider."""
    model_lower = model.lower()
    provider = _detect_provider(model_lower)

    preset_key = provider_policy(model).preset

    if fallback_models:
        models = [model] + [m for m in fallback_models if m != model]
    elif preset_key:
        preset_models = get_models_for_provider(preset_key)
        models = [model] + [m for m in preset_models if m != model]
    else:
        models = [model]

    if cross_provider_fallback:
        _append_cross_provider_fallbacks(models, provider)
    return models


def _append_cross_provider_fallbacks(
    models: list, current_provider: Optional[str]
) -> None:
    """Append cross-provider fallback models that have an available API key."""
    try:
        from aura_cli.core.api_keys import get_api_keys_dict

        available_keys = get_api_keys_dict()

        def catalog_model(provider: str, index: int, fallback: str) -> str:
            models = get_models_for_provider(provider)
            return models[index] if len(models) > index else fallback

        candidates = [
            ("gemini", catalog_model("gemini", 0, DEFAULT_MODEL), "GOOGLE_API_KEY"),
            (
                "cerebras",
                catalog_model("cerebras", 0, DEFAULT_MODEL),
                "CEREBRAS_API_KEY",
            ),
            (
                "openrouter",
                catalog_model("openrouter", 0, DEFAULT_MODEL),
                "OPENROUTER_API_KEY",
            ),
            ("gpt", catalog_model("gpt", 1, "gpt-4o-mini"), "OPENAI_API_KEY"),
            (
                "anthropic",
                catalog_model("claude", 1, "claude-haiku-4-5-20251001"),
                "ANTHROPIC_API_KEY",
            ),
            (
                "nvidia",
                catalog_model("nvidia", 0, DEFAULT_MODEL),
                "NVIDIA_API_KEY",
            ),
            (
                "groq",
                catalog_model("groq", 0, "groq/openai/gpt-oss-20b"),
                "GROQ_API_KEY",
            ),
        ]
        for cp, cp_model, cp_key in candidates:
            if (
                cp != current_provider
                and available_keys.get(cp_key)
                and cp_model not in models
            ):
                models.append(cp_model)
    except Exception as e:
        logger.debug(f"Error building fallback model list: {e}")


def _apply_cache_control(
    messages: List[Dict[str, Any]], model: str
) -> List[Dict[str, Any]]:
    """
    Apply prompt caching headers to messages for supported providers.

    For Anthropic (claude-*) and Google (gemini-*) models, adds
    `cache_control: {"type": "ephemeral"}` to the system message and
    optionally to the first user message if it's large (>1000 chars).
    This enables prompt caching via litellm, reducing costs by 40-60%
    for repeated system prompts.

    For other providers (OpenAI, OpenRouter), messages are returned unchanged
    as they either handle caching automatically or don't support it.

    Args:
        messages: List of message dicts (role, content, etc.)
        model: Model name string (used to detect provider)

    Returns:
        New list of messages with cache_control applied where appropriate.
        Original list is not mutated.
    """
    if not messages:
        return messages

    model_lower = model.lower() if model else ""
    supports_caching = "claude" in model_lower or "gemini" in model_lower

    if not supports_caching:
        return messages

    # Check if caching is enabled in config (default: True)
    try:
        from aura_cli.core.config import get_config_manager

        config = get_config_manager()
        if config.get("prompt_caching") is False:
            return messages
    except Exception:
        pass  # If config unavailable, default to enabled

    # Deep copy messages to avoid mutating the original list
    cached_messages: List[Dict[str, Any]] = []
    for msg in messages:
        cached_messages.append(dict(msg))

    # Add cache_control to system message
    for msg in cached_messages:
        if msg.get("role") == "system" and msg.get("content"):
            msg["cache_control"] = {"type": "ephemeral"}
            break

    # Add cache_control to the first user message if it's large (>1000 chars)
    # This caches large context injections (project summaries, file contents, etc.)
    for msg in cached_messages:
        if msg.get("role") == "user" and len(msg.get("content", "")) > 1000:
            msg["cache_control"] = {"type": "ephemeral"}
            break

    return cached_messages


def _build_completion_params(
    current_model: str, messages: list, tools: Any, timeout: float, **kwargs: Any
) -> dict:
    """Build litellm completion params with provider-specific settings.

    THREAD-SAFE: Reads API keys from thread-local storage instead of os.environ.
    Passes api_key directly to litellm via params to avoid env var races.

    If an explicit api_key is provided via kwargs (e.g. from NativeBackend's
    llm_config), it takes priority over thread-local and env var resolution.
    """
    # Extract explicit api_key from kwargs before spreading into params
    explicit_api_key = kwargs.pop("api_key", None)

    params: dict = {
        "model": current_model,
        "messages": messages,
        "timeout": timeout,
        **kwargs,
    }
    model_lower = current_model.lower()

    if explicit_api_key:
        params["api_key"] = explicit_api_key
        _apply_provider_structural_params(params, model_lower)
    else:
        _resolve_provider_params(params, model_lower)

    if tools:
        params["tools"] = tools
        params["tool_choice"] = "auto"
    return params


def _apply_provider_structural_params(params: dict, model_lower: str) -> None:
    """Set non-key provider params (api_version, api_base, thinking) when an explicit key is supplied."""
    params.update(structural_completion_params(model_lower))


def _resolve_provider_params(params: dict, model_lower: str) -> None:
    """Resolve API key and provider-specific params from thread-local storage + env vars."""
    from aura_cli.core.llm.key_rotation import has_multiple_keys, next_key

    api_keys = getattr(_thread_local, "api_keys", None) or {}
    policy = provider_policy(model_lower)

    if policy.name == "gemini":
        _resolve_gemini_params(
            params, model_lower, api_keys, has_multiple_keys, next_key
        )
        return

    if policy.name == "openrouter":
        if has_multiple_keys("openrouter"):
            params["api_key"] = next_key("openrouter")
        else:
            key = api_keys.get("OPENROUTER_API_KEY") or os.environ.get(
                "OPENROUTER_API_KEY"
            )
            if key:
                params["api_key"] = key
        return

    params.update(structural_completion_params(model_lower))
    for key_name in policy.key_names:
        key = api_keys.get(key_name) or os.environ.get(key_name)
        if key:
            params["api_key"] = key
            return


def _resolve_gemini_params(
    params: dict,
    model_lower: str,
    api_keys: dict,
    has_multiple_keys: Any,
    next_key: Any,
) -> None:
    """Set Gemini-specific params: api_version, thinking budget, and API key."""
    params.update(structural_completion_params(model_lower))
    if has_multiple_keys("google"):
        params["api_key"] = next_key("google")
    else:
        key = (
            api_keys.get("GOOGLE_API_KEY")
            or api_keys.get("GEMINI_API_KEY")
            or os.environ.get("GOOGLE_API_KEY")
            or os.environ.get("GEMINI_API_KEY")
        )
        if key:
            params["api_key"] = key


def _try_single_model(
    current_model: str,
    messages: List[Dict[str, str]],
    tools: Optional[List[Dict[str, Any]]],
    timeout: float,
    max_retries: int,
    rate_limiter: Any,
    loading: Optional[Any],
    model_idx: int,
    event_callback: Optional[Any] = None,
    **kwargs: Any,
) -> Any:
    """Attempt a single model with retry/backoff. Returns response or raises."""
    # Apply prompt caching for supported providers (Anthropic, Google)
    cached_messages = _apply_cache_control(messages, current_model)

    last_error: Optional[Exception] = None
    for attempt in range(max_retries):
        llm_call_id = uuid4().hex
        attempt_started = time.monotonic()
        if event_callback:
            event_callback(
                {
                    "event": "start",
                    "llm_call_id": llm_call_id,
                    "provider": current_model.split("/", 1)[0],
                    "model": current_model,
                    "attempt": attempt + 1,
                    "timeout": timeout,
                    "fallback": model_idx > 0,
                }
            )
        try:
            if loading:
                loading.update(
                    LoadingState.PREPARING if attempt > 0 else LoadingState.THINKING,
                    f"Retry {attempt + 1}/{max_retries}..."
                    if attempt > 0
                    else f"Pensando... ({current_model.split('/')[-1]})",
                )
            completion_params = _build_completion_params(
                current_model, cached_messages, tools, timeout, **kwargs
            )

            if not rate_limiter.wait_if_needed(
                current_model, max_wait=max(timeout, 1.0)
            ):
                raise RateLimitError(
                    message="Rate limiter local excedeu o tempo máximo de espera",
                    model=current_model,
                    retry_after=int(max(timeout, 1.0)),
                )
            try:
                response = _execute_llm_call(
                    current_model, messages, completion_params, loading
                )
            finally:
                rate_limiter.release(current_model)

            if loading:
                loading.complete(
                    f"Sucesso com fallback: {current_model}"
                    if model_idx > 0
                    else "Resposta recebida"
                )
            elif model_idx > 0:
                _get_console().print(
                    f"[yellow]+ Usando modelo fallback: {current_model}[/yellow]"
                )
            if event_callback:
                event_callback(
                    {
                        "event": "succeeded",
                        "llm_call_id": llm_call_id,
                        "duration": time.monotonic() - attempt_started,
                    }
                )
            return response

        except Exception as e:
            if event_callback:
                event_callback(
                    {
                        "event": "failed",
                        "llm_call_id": llm_call_id,
                        "duration": time.monotonic() - attempt_started,
                        "error": f"{type(e).__name__}: {e}"[:500],
                    }
                )
            last_error = e
            if _should_retry(e, attempt, max_retries):
                _handle_llm_error(e, current_model, attempt, max_retries, loading)
                if attempt < max_retries - 1:
                    continue
            break  # non-retryable or exhausted retries

    if last_error is None:
        raise RuntimeError("LLM call failed without capturing an error")
    raise last_error


def query_with_fallback(
    model: str,
    messages: List[Dict[str, str]],
    fallback_models: Optional[List[str]] = None,
    max_retries: int = MAX_LLM_RETRIES,
    timeout: float = DEFAULT_LLM_TIMEOUT,
    tools: Optional[List[Dict[str, Any]]] = None,
    cross_provider_fallback: bool = True,
    event_callback: Optional[Any] = None,
    **kwargs,
) -> Any:
    """Query an LLM with automatic per-provider fallback and exponential-backoff retry.

    Tries the primary model first, then same-provider alternatives from
    MODEL_PRESETS (or a custom fallback_models list). Retries up to
    max_retries times per model with 2^attempt second backoff. Distinguishes
    retryable errors (503, 429, timeout) from fatal ones.

    Args:
        model: Primary model name (LiteLLM format).
        messages: Chat messages list, each with "role" and "content".
        fallback_models: Custom fallback list; overrides MODEL_PRESETS when set.
        max_retries: Attempts per model before moving to the next.
        timeout: Per-request timeout in seconds.
        tools: Optional function-calling tool list (OpenAI format).
        cross_provider_fallback: If True, allows falling back across providers.
        **kwargs: Extra kwargs forwarded to litellm.completion().

    Returns litellm response object; raises if all models exhaust retries.
    """
    loading = None
    original_env = _capture_env(_LLM_ENV_KEYS)
    rate_limiter = get_rate_limiter()

    try:
        _setup_api_keys()
        model = _resolve_model(model, messages)
        models_to_try = _build_models_list(
            model, fallback_models, cross_provider_fallback
        )

        if not loading:
            loading = show_llm_feedback(_get_console(), model)

        last_error: Optional[Exception] = None
        for model_idx, current_model in enumerate(models_to_try):
            current_model = normalize_model_name(current_model) or current_model
            if loading and model_idx > 0:
                short_name = current_model.split("/")[-1]
                loading.update(
                    LoadingState.PREPARING, f"Alternando para {short_name}..."
                )
            try:
                return _try_single_model(
                    current_model,
                    messages,
                    tools,
                    timeout,
                    max_retries,
                    rate_limiter,
                    loading,
                    model_idx,
                    event_callback,
                    **kwargs,
                )
            except Exception as e:
                last_error = e
                if not _is_retryable_error(e) and model_idx >= len(models_to_try) - 1:
                    if loading:
                        loading.error(f"Erro: {type(e).__name__}")
                    raise
                if loading:
                    loading.update(LoadingState.PREPARING, "Tentando próximo modelo...")
                logger.debug(f"{current_model} falhou: {e}. Tentando próximo...")

        # All models exhausted
        last_error_str = str(last_error).lower() if last_error else ""
        is_rate_limit = any(
            x in last_error_str for x in ["429", "rate limit", "quota", "exceeded"]
        )
        if loading:
            loading.error("Limite atingido" if is_rate_limit else "Falha na conexão")
        if is_rate_limit:
            retry_after = None
            if last_error:
                m = re.search(r"retry.*?(\d+)", last_error_str)
                retry_after = int(m.group(1)) if m else None
            raise RateLimitError(
                message="Rate limit exceeded",
                model=models_to_try[-1] if models_to_try else model,
                retry_after=retry_after,
            )
        raise Exception(f"All models failed: {list(models_to_try)}")
    finally:
        _restore_env(original_env)
        for attr in ("api_keys", "original_env"):
            if hasattr(_thread_local, attr):
                delattr(_thread_local, attr)


def get_recommended_model(provider: str = "gemini") -> str:
    """Return the recommended model for a given LLM provider.

    Args:
        provider: Provider name (case-insensitive). Supported values:
            "gemini", "openai", "anthropic", "nvidia", "cerebras", "groq".
            Unknown providers fall back to the default Gemini model.

    Returns:
        Model name string in LiteLLM format.
    """
    return get_default_model_for_provider(normalize_provider_name(provider))


def estimate_tokens(text: str, model: Optional[str] = None) -> int:
    """Estimate the token count of a text (uses tiktoken when available)."""
    try:
        import tiktoken

        if model:
            try:
                encoding = tiktoken.encoding_for_model(model)
                return len(encoding.encode(text))
            except (KeyError, ValueError):
                pass  # Model not recognised by tiktoken — fall back to cl100k_base

        encoding = tiktoken.get_encoding("cl100k_base")
        return len(encoding.encode(text))
    except ImportError:
        return int(len(text) / FALLBACK_CHARS_PER_TOKEN)


def truncate_conversation(
    messages: List[Dict[str, str]], max_tokens: int = 8000
) -> List[Dict[str, str]]:
    """Truncate a conversation to fit within max_tokens.

    Always preserves the system message. Removes oldest non-system messages
    until the estimated token count falls below the limit. Returns the
    original list unchanged if it already fits.
    """
    if not messages:
        return messages

    system_msg = messages[0] if messages[0].get("role") == "system" else None
    conversation = messages[1:] if system_msg else messages

    total_tokens = sum(estimate_tokens(msg.get("content", "")) for msg in messages)

    if total_tokens <= max_tokens:
        return messages

    truncated = []
    current_tokens = 0

    if system_msg:
        current_tokens += estimate_tokens(system_msg.get("content", ""))
        truncated.append(system_msg)

    for msg in reversed(conversation):
        msg_tokens = estimate_tokens(msg.get("content", ""))
        if current_tokens + msg_tokens > max_tokens:
            break
        truncated.insert(1 if system_msg else 0, msg)
        current_tokens += msg_tokens

    return truncated
