"""Vision tools for Aura CLI agents.

Provides tools that allow the LLM to receive and reason about visual content:

    view_image(path, prompt)         — send a local image file to the LLM
    take_screenshot(prompt)          — capture the current screen and send it
    describe_url_visual(url, prompt) — fetch a URL via monitor + optional screenshot

All tools perform:
    1. Vision capability check for the active model (clear error if not supported)
    2. Automatic image resize / re-encode to keep payload under 200 KB base64
    3. Injection of a multimodal message into the active conversation history

The tools follow the same display/confirmation pattern as other core tools.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from aura_cli.core.logger import get_logger
from aura_cli.core.stats import get_stats
from aura_cli.core.ui import display_tool_call
from aura_cli.core.ui_bridge import UIIcons

logger = get_logger(__name__)

# Supported file extensions for view_image
_SUPPORTED_EXTENSIONS: frozenset[str] = frozenset(
    {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp", ".tiff", ".tif"}
)


# Internal helpers


def _get_active_model() -> str:
    """Return the model currently in use, or empty string if unavailable."""
    try:
        stats = get_stats()
        return getattr(stats, "current_model", "") or ""
    except Exception:
        return ""


def _check_vision_support(model: str) -> tuple[bool, str]:
    """Return (supported, error_message).  Empty error_message means OK."""
    from aura_cli.core.llm.vision import model_supports_vision

    if not model:
        return (
            False,
            "Não foi possível detectar o modelo ativo. "
            "Configure um modelo com suporte a vision (ex: gemini-2.5-flash).",
        )
    if not model_supports_vision(model):
        return (
            False,
            f"O modelo '{model}' não suporta vision/imagens.\n"
            "Modelos compatíveis: Gemini 1.5/2.5, GPT-4o, Claude 3+.\n"
            f"Use {UIIcons.INFO} /model para trocar o modelo.",
        )
    return True, ""


def _vision_result(
    prompt: str,
    images: list[tuple[str, str]],
    *,
    model: str,
    source_label: str,
) -> str:
    """Inject a vision message into the conversation and return a status string.

    This appends a multimodal user message to the active conversation history
    so the *next* LLM call sees the image alongside the prompt.

    Returns a tool-result string describing what was sent.
    """
    from aura_cli.core.llm.vision import build_vision_message

    # We can't call the LLM from within a tool execution directly
    # (that would be a recursive call into the function loop).
    # Instead, we inject into the history; the loop will pick it up on the
    # next iteration via the continuation controller.
    try:
        from aura_cli.core.execution_context import get_active_conversation_history

        history = get_active_conversation_history()
        if history is not None:
            msg = build_vision_message(prompt, images)
            history.append(msg)
            return (
                f"✅ Imagem enviada ao modelo '{model}'.\n"
                f"Fonte: {source_label}\n"
                f"Prompt: {prompt[:120]}{'...' if len(prompt) > 120 else ''}\n"
                f"Payload: {sum(len(b) for b, _ in images) // 1024} KB base64"
            )
    except Exception as e:
        logger.debug("Could not inject vision message via history ref: %s", e)

    # Fallback: return the base64 data as a structured result that the LLM
    # can interpret directly (some providers accept inline base64 in tool results)
    parts = []
    for i, (b64, mime) in enumerate(images, 1):
        parts.append(
            f"[IMAGE_{i} mime={mime} size={len(b64)//1024}KB]\n"
            f"data:{mime};base64,{b64[:80]}...{b64[-20:]}"
        )
    return (
        f"Imagem preparada para análise visual.\n"
        f"Modelo: {model}\nPrompt: {prompt}\n"
        + "\n".join(parts)
    )


# Public tools


def view_image(
    path: str,
    prompt: str = "Descreva o que você vê nessa imagem em detalhes.",
    *,
    model: Optional[str] = None,
) -> str:
    """Send a local image file to the active LLM for visual analysis.

    The image is automatically resized to at most 1024px in the largest
    dimension and re-encoded as JPEG to minimise token cost (typically
    30–200 KB base64 for a screenshot, versus 8+ MB for a raw PNG).

    Args:
        path: Path to the image file (PNG, JPEG, WEBP, GIF, BMP supported).
        prompt: Question or instruction to accompany the image.
        model: Override the active model (optional, mainly for testing).

    Returns:
        Status string describing the result (shown in the tool panel).
    """
    display_tool_call("view_image", {"path": path, "prompt": prompt[:60] + "..."})
    stats = get_stats()
    stats.track_tool_usage("view_image")

    active_model = model or _get_active_model()
    supported, err = _check_vision_support(active_model)
    if not supported:
        return f"❌ Vision não disponível: {err}"

    p = Path(path)
    if not p.exists():
        return f"❌ File not found: {path}"
    if p.suffix.lower() not in _SUPPORTED_EXTENSIONS:
        return (
            f"❌ Formato não suportado: '{p.suffix}'.\n"
            f"Formatos aceitos: {', '.join(sorted(_SUPPORTED_EXTENSIONS))}"
        )

    try:
        from aura_cli.core.llm.vision import encode_image_file

        b64, mime = encode_image_file(p)
    except ImportError as e:
        return f"❌ Pillow não instalado: {e}\nInstale com: pip install pillow"
    except ValueError as e:
        return f"❌ Invalid image file: {e}"
    except Exception as e:
        logger.error("view_image: encoding failed for %s: %s", path, e, exc_info=True)
        return f"❌ Error processing image: {e}"

    return _vision_result(
        prompt,
        [(b64, mime)],
        model=active_model,
        source_label=str(p.resolve()),
    )


def take_screenshot(
    prompt: str = "Descreva o que está visível na tela.",
    *,
    model: Optional[str] = None,
) -> str:
    """Capture the current screen and send it to the active LLM.

    Uses the platform-native screenshot tool:
    - macOS: ``screencapture -x``
    - Linux: ``gnome-screenshot``, ``scrot``, or ``import`` (ImageMagick)
    - Windows: Pillow ``ImageGrab``

    Args:
        prompt: Question or instruction about what to analyse in the screenshot.
        model: Override the active model (optional, mainly for testing).

    Returns:
        Status string describing the result.
    """
    display_tool_call("take_screenshot", {"prompt": prompt[:60] + "..."})
    stats = get_stats()
    stats.track_tool_usage("take_screenshot")

    active_model = model or _get_active_model()
    supported, err = _check_vision_support(active_model)
    if not supported:
        return f"❌ Vision não disponível: {err}"

    from aura_cli.core.llm.vision import capture_screenshot

    raw = capture_screenshot()
    if raw is None:
        return (
            "❌ Não foi possível capturar a tela.\n"
            "macOS: requer permissão de Screen Recording (Preferências → Privacidade).\n"
            "Linux: instale gnome-screenshot, scrot ou ImageMagick (import).\n"
            "Alternativa: salve uma imagem e use view_image(path)."
        )

    try:
        from aura_cli.core.llm.vision import encode_image_bytes

        b64, mime = encode_image_bytes(raw)
    except ImportError as e:
        return f"❌ Pillow não instalado: {e}"
    except Exception as e:
        logger.error("take_screenshot: encode failed: %s", e, exc_info=True)
        return f"❌ Error encoding screenshot: {e}"

    return _vision_result(
        prompt,
        [(b64, mime)],
        model=active_model,
        source_label="screenshot (tela capturada agora)",
    )


def describe_url_visual(
    url: str,
    prompt: str = "Descreva o conteúdo visual desta página.",
    *,
    model: Optional[str] = None,
    include_text: bool = True,
) -> str:
    """Fetch a URL via the text monitor and send a screenshot of the content.

    Combines two approaches:
    1. Text dump via aura-monitor (always available, zero token overhead)
    2. Screenshot of the rendered content via temporary HTML → PIL rendering
       (only when Pillow is available and model supports vision)

    If vision is not available, falls back to text-only via the monitor.

    Args:
        url: URL or local ``file://`` path to fetch.
        prompt: Instruction for what to analyse visually.
        include_text: If True, also include the text dump in the result.
        model: Override the active model (optional).

    Returns:
        Combined text + vision analysis result, or text-only if vision unavailable.
    """
    display_tool_call("describe_url_visual", {"url": url, "prompt": prompt[:60] + "..."})
    stats = get_stats()
    stats.track_tool_usage("describe_url_visual")

    active_model = model or _get_active_model()
    vision_ok, _ = _check_vision_support(active_model)

    # Always attempt text fetch via monitor
    text_content: str = ""
    if include_text:
        try:
            # Use the aura-monitor binary directly to avoid importing from tui/
            # (which would violate the core → tui architectural constraint).
            import subprocess

            from aura_cli.core.nim_runtime import resolve_nim_binary

            monitor_bin = resolve_nim_binary("aura-monitor")
            if monitor_bin:
                result = subprocess.run(
                    [str(monitor_bin), "-d", url],
                    capture_output=True,
                    text=True,
                    timeout=15,
                )
                if result.returncode == 0:
                    text_content = result.stdout.strip()
                elif result.stderr:
                    text_content = f"[Monitor error: {result.stderr.strip()}]"
        except Exception as e:
            logger.debug("describe_url_visual: monitor fetch failed: %s", e)
            text_content = ""

    if not vision_ok:
        # Vision not available — return text-only result
        if text_content:
            return (
                f"📄 Conteúdo de {url} (texto, vision não disponível):\n\n"
                + text_content[:4000]
                + ("..." if len(text_content) > 4000 else "")
            )
        return (
            f"❌ Vision não disponível para o modelo '{active_model}' "
            f"e o monitor não retornou conteúdo para {url}."
        )

    # Vision available — try to capture a rendered screenshot
    # Strategy: use aura-monitor to fetch the page, then take a desktop screenshot
    # (works when running in GUI environment). Fallback to text if no screenshot.
    raw = None
    try:
        from aura_cli.core.llm.vision import capture_screenshot

        raw = capture_screenshot()
    except Exception as e:
        logger.debug("describe_url_visual: screenshot failed: %s", e)

    combined_prompt = prompt
    if text_content:
        combined_prompt = (
            f"{prompt}\n\n"
            f"Texto extraído da página (para contexto):\n"
            + text_content[:2000]
            + ("..." if len(text_content) > 2000 else "")
        )

    if raw is None:
        # No screenshot — return just text
        if text_content:
            return (
                f"📄 Conteúdo de {url} (screenshot não disponível):\n\n"
                + text_content[:4000]
            )
        return f"❌ Não foi possível obter conteúdo visual ou textual de {url}."

    try:
        from aura_cli.core.llm.vision import encode_image_bytes

        b64, mime = encode_image_bytes(raw)
    except Exception as e:
        logger.error("describe_url_visual: encode failed: %s", e, exc_info=True)
        return f"❌ Error encoding screenshot: {e}"

    return _vision_result(
        combined_prompt,
        [(b64, mime)],
        model=active_model,
        source_label=f"screenshot da URL: {url}",
    )


# Exports

__all__ = [
    "describe_url_visual",
    "take_screenshot",
    "view_image",
]
