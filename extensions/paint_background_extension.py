"""Paint Background Extension for Aura CLI.

Allows Chat and AGI agents to generate ASCII/ANSI art in background
without opening the Paint tool UI.

Usage:
    # From Chat/AGI agent
    result = await paint_ext.generate("logo for Aura CLI")
    art = result["art"]  # Use in response
"""

import asyncio
import logging
import tempfile
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class PaintBackgroundExtension:
    """Background art generation for agents."""
    
    def __init__(self, llm_client=None):
        """Initialize extension.
        
        Args:
            llm_client: LLM client for art generation
        """
        self.llm = llm_client
        self._cache: Dict[str, str] = {}
        self._temp_dir = Path(tempfile.gettempdir()) / "aura_paint_bg"
        self._temp_dir.mkdir(exist_ok=True)
    
    async def generate(
        self, 
        prompt: str, 
        width: int = 80, 
        height: int = 24,
        mode: str = "auto",
        use_cache: bool = True
    ) -> Dict[str, Any]:
        """Generate art in background.
        
        Args:
            prompt: Art description
            width: Canvas width
            height: Canvas height
            mode: Generation mode (auto/ascii/primitives/hybrid)
            use_cache: Use cached result if available
            
        Returns:
            {
                "art": "ASCII art string",
                "mode": "generation mode used",
                "cached": bool,
                "file": "path to saved file"
            }
        """
        cache_key = f"{prompt}:{width}x{height}:{mode}"
        
        if use_cache and cache_key in self._cache:
            return {
                "art": self._cache[cache_key],
                "mode": mode,
                "cached": True
            }
        
        if not self.llm:
            return {"error": "LLM client not available"}
        
        try:
            # Generate based on mode
            if mode == "auto" or mode == "ascii":
                art = await self._generate_ascii(prompt, width, height)
            elif mode == "primitives":
                art = await self._generate_primitives_text(prompt, width, height)
            elif mode == "hybrid":
                art = await self._generate_hybrid_text(prompt, width, height)
            else:
                art = await self._generate_ascii(prompt, width, height)
            
            # Cache result
            self._cache[cache_key] = art
            
            # Save to file
            file_path = self._temp_dir / f"{hash(cache_key)}.txt"
            file_path.write_text(art)
            
            return {
                "art": art,
                "mode": mode,
                "cached": False,
                "file": str(file_path)
            }
            
        except Exception as e:
            logger.error(f"Background generation failed: {e}")
            return {"error": str(e)}
    
    async def _generate_ascii(self, prompt: str, width: int, height: int) -> str:
        """Generate ASCII art."""
        art_prompt = f"""
Generate ASCII art for: {prompt}

Size: {width}x{height} characters
Use: █▓▒░ ·•○●◆◇■□▪▫
Return ONLY the art, no explanation.
Each line exactly {width} chars.
Exactly {height} lines.
"""
        
        art = await self.llm.query(art_prompt)
        
        # Ensure correct dimensions
        lines = art.split('\n')[:height]
        lines = [line[:width].ljust(width) for line in lines]
        while len(lines) < height:
            lines.append(' ' * width)
        
        return '\n'.join(lines)
    
    async def _generate_primitives_text(self, prompt: str, width: int, height: int) -> str:
        """Generate primitives and render to text."""
        import json
        
        primitives_prompt = f"""
Create drawing plan for: {prompt}
Canvas: {width}x{height}

Return JSON:
{{
    "shapes": [
        {{"type": "circle", "x": 10, "y": 10, "radius": 5, "char": "○"}},
        {{"type": "line", "x1": 0, "y1": 0, "x2": 20, "y2": 20, "char": "█"}},
        {{"type": "text", "x": 5, "y": 5, "text": "Hello"}}
    ]
}}

Return ONLY valid JSON.
"""
        
        response = await self.llm.query(primitives_prompt)
        
        # Parse and render
        response = response.strip()
        if response.startswith("```"):
            response = response.split("```")[1]
            if response.startswith("json"):
                response = response[4:]
        
        plan = json.loads(response)
        
        # Create canvas
        canvas = [[' ' for _ in range(width)] for _ in range(height)]
        
        # Draw shapes
        for shape in plan.get("shapes", []):
            self._render_shape_to_canvas(canvas, shape, width, height)
        
        return '\n'.join(''.join(row) for row in canvas)
    
    def _render_shape_to_canvas(self, canvas, shape, width, height):
        """Render shape to text canvas."""
        shape_type = shape.get("type")
        char = shape.get("char", "█")
        
        if shape_type == "circle":
            cx, cy, r = shape["x"], shape["y"], shape["radius"]
            for y in range(max(0, cy - r), min(height, cy + r + 1)):
                for x in range(max(0, cx - r), min(width, cx + r + 1)):
                    if ((x - cx) ** 2 + (y - cy) ** 2) ** 0.5 <= r:
                        canvas[y][x] = char
        
        elif shape_type == "line":
            x1, y1 = shape["x1"], shape["y1"]
            x2, y2 = shape["x2"], shape["y2"]
            
            # Bresenham
            dx = abs(x2 - x1)
            dy = abs(y2 - y1)
            sx = 1 if x1 < x2 else -1
            sy = 1 if y1 < y2 else -1
            err = dx - dy
            
            x, y = x1, y1
            while True:
                if 0 <= x < width and 0 <= y < height:
                    canvas[y][x] = char
                if x == x2 and y == y2:
                    break
                e2 = 2 * err
                if e2 > -dy:
                    err -= dy
                    x += sx
                if e2 < dx:
                    err += dx
                    y += sy
        
        elif shape_type == "text":
            x, y = shape["x"], shape["y"]
            text = shape["text"]
            for i, c in enumerate(text):
                if 0 <= x + i < width and 0 <= y < height:
                    canvas[y][x + i] = c
    
    async def _generate_hybrid_text(self, prompt: str, width: int, height: int) -> str:
        """Generate hybrid (ASCII + primitives)."""
        # For simplicity, use ASCII mode
        return await self._generate_ascii(prompt, width, height)
    
    def clear_cache(self) -> None:
        """Clear generation cache."""
        self._cache.clear()
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        return {
            "cached_items": len(self._cache),
            "temp_dir": str(self._temp_dir),
            "temp_files": len(list(self._temp_dir.glob("*.txt")))
        }


# ═══════════════════════════════════════════════════════════════════════════
# Integration with Aura CLI
# ═══════════════════════════════════════════════════════════════════════════

# Global instance
_paint_extension: Optional[PaintBackgroundExtension] = None


def get_paint_extension(llm_client=None) -> PaintBackgroundExtension:
    """Get or create paint extension instance."""
    global _paint_extension
    if _paint_extension is None:
        _paint_extension = PaintBackgroundExtension(llm_client)
    elif llm_client is not None:
        _paint_extension.llm = llm_client
    return _paint_extension


# ═══════════════════════════════════════════════════════════════════════════
# Tool Functions for AGI/Chat Agents
# ═══════════════════════════════════════════════════════════════════════════

async def generate_ascii_art(
    prompt: str,
    width: int = 80,
    height: int = 24,
    mode: str = "auto"
) -> str:
    """Generate ASCII art for use in responses.
    
    Tool function that agents can call directly.
    
    Args:
        prompt: What to draw
        width: Canvas width (default 80)
        height: Canvas height (default 24)
        mode: Generation mode (auto/ascii/primitives/hybrid)
    
    Returns:
        ASCII art as string
    
    Example:
        >>> art = await generate_ascii_art("Aura CLI logo")
        >>> print(art)
    """
    ext = get_paint_extension()
    result = await ext.generate(prompt, width, height, mode)
    
    if "error" in result:
        return f"[Error generating art: {result['error']}]"
    
    return result["art"]


async def generate_icon(name: str, size: int = 5) -> str:
    """Generate small icon.
    
    Args:
        name: Icon name (e.g., "star", "heart", "check")
        size: Icon size (default 5x5)
    
    Returns:
        Icon as ASCII art
    """
    return await generate_ascii_art(f"{name} icon", width=size, height=size, mode="ascii")


async def generate_logo(text: str, width: int = 40, height: int = 10) -> str:
    """Generate logo with text.
    
    Args:
        text: Logo text
        width: Logo width
        height: Logo height
    
    Returns:
        Logo as ASCII art
    """
    return await generate_ascii_art(f"logo with text '{text}'", width, height, mode="hybrid")


# Export for agents
__all__ = [
    "PaintBackgroundExtension",
    "get_paint_extension",
    "generate_ascii_art",
    "generate_icon",
    "generate_logo",
]
