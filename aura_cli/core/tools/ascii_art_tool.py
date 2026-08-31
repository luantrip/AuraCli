"""ASCII Art Generation Tool for Aura CLI Agents.

Allows Chat and AGI agents to generate ASCII/ANSI art directly in responses.
"""

import asyncio
import logging

logger = logging.getLogger(__name__)


def generate_ascii_art_sync(
    prompt: str, width: int = 60, height: int = 15, mode: str = "auto"
) -> str:
    """Generate ASCII art synchronously (for tool calling).

    Args:
        prompt: What to draw (e.g., "Aura CLI logo", "star icon")
        width: Canvas width in characters (default 60)
        height: Canvas height in lines (default 15)
        mode: Generation mode (auto/ascii/primitives/hybrid)

    Returns:
        ASCII art as string

    Example:
        >>> art = generate_ascii_art_sync("Aura CLI logo")
        >>> print(art)
    """
    try:
        import os
        import sys

        ext_path = os.path.join(os.path.dirname(__file__), "../../../extensions")
        if ext_path not in sys.path:
            sys.path.insert(0, ext_path)

        from paint_background_extension import get_paint_extension

        from aura_cli.core.llm.base import query_with_fallback as query_llm

        class SimpleLLMClient:
            """Minimal LLM client wrapper for ASCII art generation."""

            async def query(self, prompt: str):
                """Query the LLM and return the response text."""
                messages = [{"role": "user", "content": prompt}]
                return await asyncio.to_thread(query_llm, None, messages)  # type: ignore[arg-type]

        ext = get_paint_extension(SimpleLLMClient())
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = None

        if loop is not None and loop.is_running():
            import concurrent.futures

            with concurrent.futures.ThreadPoolExecutor() as pool:
                future = pool.submit(
                    asyncio.run, ext.generate(prompt, width, height, mode)
                )
                result = future.result(timeout=30)
        else:
            result = asyncio.run(ext.generate(prompt, width, height, mode))

        if "error" in result:
            return f"[Error generating art: {result['error']}]"

        return result["art"]

    except Exception as e:
        logger.error(f"ASCII art generation failed: {e}")
        return f"[Error: {e}]"


TOOL_METADATA = {
    "type": "function",
    "function": {
        "name": "generate_ascii_art",
        "description": "Generate ASCII/ANSI art for visual elements in responses. Use for logos, icons, diagrams, or decorative elements.",
        "parameters": {
            "type": "object",
            "properties": {
                "prompt": {
                    "type": "string",
                    "description": "What to draw (e.g., 'Aura CLI logo', 'star icon', 'robot')",
                },
                "width": {
                    "type": "integer",
                    "description": "Canvas width in characters (default 60)",
                    "default": 60,
                },
                "height": {
                    "type": "integer",
                    "description": "Canvas height in lines (default 15)",
                    "default": 15,
                },
                "mode": {
                    "type": "string",
                    "enum": ["auto", "ascii", "primitives", "hybrid"],
                    "description": "Generation mode (default 'auto')",
                    "default": "auto",
                },
            },
            "required": ["prompt"],
        },
    },
}

__all__ = ["TOOL_METADATA", "generate_ascii_art_sync"]
