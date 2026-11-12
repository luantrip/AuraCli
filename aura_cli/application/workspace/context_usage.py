"""Pure context-window usage calculations and per-model window sizes."""

from __future__ import annotations

# Context window per model family (tokens), moved verbatim from the former private
# table in ``core/context/base.py`` so the status bar and history compaction share
# one source. Matching is by substring on the lower-cased model id, in order.
#
# Known gap (kept honest rather than guessed): ids without a documented window in
# this repository -- e.g. ``zai-glm``, ``north-mini``, ``gemma-4``,
# ``mistral-large``, ``gpt-oss-20b``, ``openrouter/free`` -- fall back to the
# conservative default. Add an entry only with a provider-documented value.
_MODEL_CONTEXT_WINDOWS: dict[str, int] = {
    # Google
    "gemini-2.5-flash": 1_048_576,
    "gemini-2.5-pro": 1_048_576,
    "gemini-1.5-pro": 1_048_576,
    "gemini-1.5-flash": 1_048_576,
    # Cerebras / OpenRouter / NVIDIA
    "gpt-oss-120b": 131_072,
    "nemotron": 131_072,
    "llama": 131_072,
    "qwen": 131_072,
    # OpenAI
    "gpt-4o": 128_000,
    "gpt-4o-mini": 128_000,
    "gpt-4-turbo": 128_000,
    # Anthropic
    "claude-3": 200_000,
    "claude-sonnet": 200_000,
    "claude-haiku": 200_000,
    "claude-opus": 200_000,
}
DEFAULT_CONTEXT_WINDOW = 32_000  # conservative fallback for unknown models


def context_window_for_model(model: str | None) -> int:
    """Return the approximate context window (tokens) for a model id.

    Unknown or empty ids get ``DEFAULT_CONTEXT_WINDOW``. Routing aliases such as
    ``openrouter/free`` pick a model server-side, so their real window cannot be
    known; they use the same conservative fallback on purpose.
    """
    model_lower = (model or "").lower()
    for key, size in _MODEL_CONTEXT_WINDOWS.items():
        if key in model_lower:
            return size
    return DEFAULT_CONTEXT_WINDOW


MIN_CONTEXT_HARD_LIMIT = 8_000  # never let the hard cap drop below this
_RESPONSE_HEADROOM = 0.75  # reserve 25% of the window for the reply + tool results


def context_hard_limit_for_model(
    model: str | None, configured_override: int | None = None
) -> int:
    """Return the hard token ceiling for history before compaction must stop.

    The ceiling is derived from the model's real context window so a large-window
    model (e.g. Gemini 2.5, 1M tokens) is not throttled at a fixed 32k. A fraction
    of the window is reserved as headroom for the upcoming response and tool
    results; the rest is available to the conversation history.

    ``configured_override`` lets a user pin an explicit ``context_max_tokens`` in
    settings; when provided and positive it wins (clamped to the minimum), so the
    automatic per-model budget never overrides a deliberate choice. A non-positive
    or ``None`` override means "decide from the model".
    """
    if configured_override is not None and configured_override > 0:
        return max(MIN_CONTEXT_HARD_LIMIT, int(configured_override))
    window = context_window_for_model(model)
    return max(MIN_CONTEXT_HARD_LIMIT, int(window * _RESPONSE_HEADROOM))


def get_context_percentage(tokens_used: int, max_tokens: int) -> float:
    """Return context usage as a percentage."""
    if max_tokens <= 0:
        return 0.0
    return (tokens_used / max_tokens) * 100


def should_compact_context(
    tokens_used: int,
    max_tokens: int,
    threshold: float = 0.8,
) -> bool:
    """Return whether usage reached the configured fractional threshold."""
    return get_context_percentage(tokens_used, max_tokens) >= threshold * 100
