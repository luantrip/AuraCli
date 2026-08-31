"""Paint Tools - Integration with Paint Agent for CLI.

This module provides tools for generating art using the Paint Agent
from the main CLI chat without requiring the Paint TUI application.
"""

import asyncio
from pathlib import Path
from typing import Any, Dict, Optional

from aura_cli.core.logger import get_logger
from aura_cli.core.tools.paint_agent_headless import HeadlessPaintAgent

logger = get_logger(__name__)


def paint_generate_art(
    prompt: str,
    width: int = 80,
    height: int = 24,
    output_file: Optional[str] = None,
    output_format: str = "ans",
    mode: Optional[str] = None,
) -> Dict[str, Any]:
    """Generate ASCII/ANSI art via PaintAgent in headless mode.

    Args:
        prompt: Description of the art to generate.
        width: Canvas width in characters (default 80).
        height: Canvas height in characters (default 24).
        output_file: Save path. If None, auto-generated under artes/.
        output_format: 'ans', 'png', 'svg' or 'html' (default 'ans').
        mode: 'auto', 'ascii', 'primitives' or 'hybrid' (default 'auto').

    Returns:
        Dict with keys: success, file_path, format, width, height, error.
    """
    try:
        from aura_cli.core.llm.base import get_llm_client

        llm_client = get_llm_client()
    except Exception as e:
        logger.debug(f"LLM client not available: {e}")
        llm_client = None

    if not output_file:
        artes_dir = Path("artes")
        artes_dir.mkdir(exist_ok=True)
        timestamp = int(__import__("time").time())
        filename = f"arte_{timestamp}.{output_format}"
        output_file = str(artes_dir / filename)
    else:
        output_file = str(Path(output_file).expanduser().resolve())

    try:
        agent = HeadlessPaintAgent(
            llm_client=llm_client,
            width=width,
            height=height,
        )

        try:
            asyncio.get_running_loop()  # check we are inside a running loop
            # Already inside a running loop — schedule as coroutine and await via thread
            import concurrent.futures

            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                future = pool.submit(asyncio.run, agent.generate_art(prompt, mode=mode))
                result = future.result(timeout=120)
        except RuntimeError:
            # No running loop — safe to use asyncio.run directly
            result = asyncio.run(agent.generate_art(prompt, mode=mode))

        if not result.get("success"):
            return {
                "success": False,
                "error": result.get("error", "Failed to generate art"),
                "file_path": None,
            }

        save_result = agent.save(output_file, output_format=output_format)

        if not save_result.get("success"):
            return {
                "success": False,
                "error": save_result.get("error", "Failed to save file"),
                "file_path": output_file,
            }

        return {
            "success": True,
            "file_path": save_result["file_path"],
            "format": output_format,
            "width": width,
            "height": height,
            "size": save_result.get("size", 0),
        }

    except Exception as e:
        logger.error(f"Error in paint_generate_art: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "file_path": output_file if output_file else None,
        }
