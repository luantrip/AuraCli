"""Vision utilities for multimodal LLM interactions via LiteLLM.

Handles image encoding (PNG/JPEG/WEBP/GIF/BMP → JPEG or PNG-with-alpha),
automatic resize to stay under MAX_IMAGE_BYTES, and per-provider vision
capability detection. Pillow is imported lazily — zero overhead when unused.

Provider support (2026-10): Gemini 1.5/2.5 ✅, GPT-4o ✅, Claude 3/3.5 ✅,
some OpenRouter routes ✅. Groq GPT OSS, Cerebras, NVIDIA Nemotron, most Llama
variants ❌.
"""

from __future__ import annotations

import base64
import io
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Maximum base64 payload per image (bytes in the encoded string).
# 200 KB covers a 1024px screenshot at JPEG q75 with plenty of headroom.
# Keeping this under 200 KB avoids burning thousands of vision tokens per turn.
MAX_IMAGE_BYTES: int = 200_000  # base64 bytes sent to the API
# Largest dimension (px) used when downscaling before encoding
MAX_IMAGE_DIMENSION: int = 1024
# JPEG quality used for re-encoding (good quality / low size trade-off)
JPEG_QUALITY: int = 75

# Vision-capable model detection

# Model name fragments that indicate vision support.
# Checked via substring match on the normalised model string (lowercased).
_VISION_MODEL_FRAGMENTS: tuple[str, ...] = (
    # Google
    "gemini-1.5",
    "gemini-2.0",
    "gemini-2.5",
    "gemini-pro-vision",
    # OpenAI
    "gpt-4o",
    "gpt-4-turbo",
    "gpt-4-vision",
    # Anthropic
    "claude-3",
    "claude-sonnet",
    "claude-haiku",
    "claude-opus",
    # OpenRouter routes that expose vision
    "gemma-4",
    "pixtral",
    "llava",
    "qwen-vl",
    "internvl",
)

# Model name fragments that are definitely text-only (override vision check).
_VISION_BLOCKLIST_FRAGMENTS: tuple[str, ...] = (
    "cerebras",
    "nemotron",
    "llama-3.3",
    "llama-3.1",
    "llama-3.2",  # llama-3.2-11b-vision exists but not in our catalog
    "mixtral",
    "mistral",
    "codestral",
    "gpt-oss-120b",  # text-only variant in Cerebras catalog
    "gpt-oss-20b",  # text-only variant in Groq catalog
    "zai-glm",
    "qwen-3",
    "gpt-oss-120b",
)


def model_supports_vision(model: str) -> bool:
    """Return True if *model* is known to support image inputs.

    Uses a conservative allowlist approach: when in doubt, returns False.
    This prevents cryptic provider errors from reaching the user.

    Args:
        model: LiteLLM model string (e.g. ``"gemini/gemini-2.5-flash"``).

    Returns:
        True only for explicitly known vision-capable models.
    """
    m = model.lower()
    # Blocklist takes priority over allowlist
    if any(frag in m for frag in _VISION_BLOCKLIST_FRAGMENTS):
        return False
    return any(frag in m for frag in _VISION_MODEL_FRAGMENTS)


# Image encoding


def _pil_to_base64(img: Any, *, has_alpha: bool = False) -> tuple[str, str]:
    """Encode a PIL Image to base64, returning (base64_string, mime_type)."""
    buf = io.BytesIO()
    if has_alpha:
        img.save(buf, format="PNG", optimize=True)
        mime = "image/png"
    else:
        if img.mode not in ("RGB", "L"):
            img = img.convert("RGB")
        img.save(buf, format="JPEG", quality=JPEG_QUALITY, optimize=True)
        mime = "image/jpeg"
    return base64.b64encode(buf.getvalue()).decode("ascii"), mime


def encode_image_file(path: str | Path) -> tuple[str, str]:
    """Read an image file, resize if necessary, and return (base64, mime_type).

    The image is automatically downscaled so the largest dimension is at most
    ``MAX_IMAGE_DIMENSION`` pixels, then re-encoded to JPEG (or PNG if the
    source has an alpha channel) to keep payload size under ``MAX_IMAGE_BYTES``.

    Args:
        path: Path to a PNG / JPEG / WEBP / GIF / BMP file.

    Returns:
        Tuple of (base64_encoded_string, mime_type_string).

    Raises:
        FileNotFoundError: If the file does not exist.
        ValueError: If the file is not a supported image format.
        ImportError: If Pillow is not installed.
    """
    try:
        from PIL import Image, UnidentifiedImageError
    except ImportError as exc:
        raise ImportError(
            "Pillow is required for vision features. "
            "Install it with: pip install pillow"
        ) from exc

    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Image not found: {path}")

    try:
        img = Image.open(p)
        img.load()  # force decode to catch corrupt files early
    except UnidentifiedImageError as exc:
        raise ValueError(f"Unsupported or corrupt image file: {path}") from exc

    has_alpha = img.mode in ("RGBA", "LA", "PA")

    # Downscale if either dimension exceeds the limit
    # Image.Resampling.LANCZOS replaces the deprecated Image.LANCZOS (Pillow ≥ 10)
    _LANCZOS = getattr(Image, "Resampling", Image).LANCZOS
    w, h = img.size
    if max(w, h) > MAX_IMAGE_DIMENSION:
        img_resized: Image.Image = img.copy()
        img_resized.thumbnail((MAX_IMAGE_DIMENSION, MAX_IMAGE_DIMENSION), _LANCZOS)
        logger.debug(
            "view_image: resized %s from %dx%d to %dx%d",
            p.name, w, h, *img_resized.size,
        )
        img = img_resized  # type: ignore[assignment]

    b64, mime = _pil_to_base64(img, has_alpha=has_alpha)

    # If still too large (e.g. very detailed artwork), halve dimensions and retry
    if len(b64) > MAX_IMAGE_BYTES:
        w2, h2 = img.size
        img.thumbnail((w2 // 2, h2 // 2), _LANCZOS)
        b64, mime = _pil_to_base64(img, has_alpha=False)  # drop alpha on hard shrink
        logger.debug(
            "view_image: second resize to %dx%d (payload was too large)", *img.size
        )

    logger.debug(
        "view_image: encoded %s as %s, payload %d bytes base64",
        p.name, mime, len(b64),
    )
    return b64, mime


def encode_image_bytes(data: bytes, mime_hint: str = "image/png") -> tuple[str, str]:
    """Encode raw image bytes (e.g. from a screenshot) to base64.

    Args:
        data: Raw image bytes.
        mime_hint: MIME type hint for format selection fallback.

    Returns:
        Tuple of (base64_encoded_string, mime_type_string).
    """
    try:
        from PIL import Image
    except ImportError as exc:
        raise ImportError(
            "Pillow is required for vision features. Install with: pip install pillow"
        ) from exc

    img = Image.open(io.BytesIO(data))
    img.load()
    has_alpha = img.mode in ("RGBA", "LA", "PA")

    w, h = img.size
    if max(w, h) > MAX_IMAGE_DIMENSION:
        # Image.Resampling.LANCZOS replaces the deprecated Image.LANCZOS (Pillow ≥ 10)
        _LANCZOS = getattr(Image, "Resampling", Image).LANCZOS
        img.thumbnail((MAX_IMAGE_DIMENSION, MAX_IMAGE_DIMENSION), _LANCZOS)

    b64, mime = _pil_to_base64(img, has_alpha=has_alpha)
    if len(b64) > MAX_IMAGE_BYTES:
        w2, h2 = img.size
        _LANCZOS = getattr(Image, "Resampling", Image).LANCZOS
        img.thumbnail((w2 // 2, h2 // 2), _LANCZOS)
        b64, mime = _pil_to_base64(img, has_alpha=False)

    return b64, mime


# LiteLLM message construction


def build_vision_message(
    prompt: str,
    images: list[tuple[str, str]],
    *,
    role: str = "user",
) -> dict[str, Any]:
    """Build a LiteLLM-compatible multimodal message dict.

    Args:
        prompt: Text prompt accompanying the image(s).
        images: List of (base64_string, mime_type) tuples from ``encode_image_file``.
        role: Message role (default ``"user"``).

    Returns:
        A dict ready to be appended to a conversation history list.

    Example::

        b64, mime = encode_image_file("screenshot.png")
        msg = build_vision_message("What error is shown?", [(b64, mime)])
        conversation_history.append(msg)
    """
    content: list[dict[str, Any]] = [{"type": "text", "text": prompt}]
    for b64, mime in images:
        content.append(
            {
                "type": "image_url",
                "image_url": {"url": f"data:{mime};base64,{b64}"},
            }
        )
    return {"role": role, "content": content}


# Screenshot capture


def capture_screenshot() -> bytes | None:
    """Capture a screenshot of the current screen.

    Tries platform-native tools first (lowest overhead), then falls back to
    Pillow's ``ImageGrab`` (macOS / Windows only).

    Returns:
        Raw PNG bytes of the screenshot, or None if capture fails.
    """
    import platform
    import subprocess
    import tempfile

    system = platform.system()

    if system == "Darwin":
        # macOS: screencapture is always available and produces PNG
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            tmp_path = tmp.name
        try:
            result = subprocess.run(
                ["screencapture", "-x", "-t", "png", tmp_path],
                capture_output=True,
                timeout=10,
            )
            if result.returncode == 0:
                data = Path(tmp_path).read_bytes()
                Path(tmp_path).unlink(missing_ok=True)
                return data
        except Exception as e:
            logger.debug("screencapture failed: %s", e)
        finally:
            Path(tmp_path).unlink(missing_ok=True)

    elif system == "Linux":
        # Try gnome-screenshot → scrot → import (ImageMagick) in order
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            tmp_path = tmp.name
        for cmd in [
            ["gnome-screenshot", "-f", tmp_path],
            ["scrot", tmp_path],
            ["import", "-window", "root", tmp_path],
        ]:
            try:
                r = subprocess.run(cmd, capture_output=True, timeout=10)
                if r.returncode == 0 and Path(tmp_path).exists():
                    data = Path(tmp_path).read_bytes()
                    Path(tmp_path).unlink(missing_ok=True)
                    return data
            except (FileNotFoundError, subprocess.TimeoutExpired):
                continue
            except Exception as e:
                logger.debug("%s failed: %s", cmd[0], e)
        Path(tmp_path).unlink(missing_ok=True)

    elif system == "Windows":
        try:
            from PIL import ImageGrab
            img = ImageGrab.grab()
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            return buf.getvalue()
        except Exception as e:
            logger.debug("ImageGrab failed: %s", e)

    return None


__all__ = [
    "JPEG_QUALITY",
    "MAX_IMAGE_BYTES",
    "MAX_IMAGE_DIMENSION",
    "build_vision_message",
    "capture_screenshot",
    "encode_image_bytes",
    "encode_image_file",
    "model_supports_vision",
]
