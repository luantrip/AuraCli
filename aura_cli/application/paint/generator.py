"""LLM-Powered Paint Agent with 3 Generation Modes.

Provides autonomous art generation using LLM with:
- Mode 1: ASCII Direct - LLM generates complete ASCII art
- Mode 2: Primitives JSON - LLM generates structured drawing commands
- Mode 3: Hybrid - Combines both approaches intelligently
"""

from enum import Enum
import json
import logging
from typing import Any, Dict, List, Optional, Protocol, cast

from rich.style import Style


class RefreshableCanvas(Protocol):
    def refresh(self) -> None: ...


class PaintHost(Protocol):
    image: Any
    canvas: RefreshableCanvas


logger = logging.getLogger(__name__)


class GenerationMode(Enum):
    """Art generation modes."""

    ASCII_DIRECT = "ascii"
    PRIMITIVES = "primitives"
    HYBRID = "hybrid"
    AUTO = "auto"  # LLM decides


class LLMPaintAgent:
    """LLM-powered autonomous paint agent."""

    def __init__(self, paint_app: PaintHost | None, llm_client=None):
        """Initialize LLM paint agent.

        Args:
            paint_app: Paint application instance
            llm_client: LLM client (Gemini/GPT/Claude)
        """
        # Headless construction is supported for prompt/mode tests; drawing methods
        # require a host and retain the historical runtime failure when absent.
        self.paint_app = cast(PaintHost, paint_app)
        self.llm = llm_client
        self.mode = GenerationMode.AUTO
        self._generation_history: List[Dict[str, Any]] = []

    async def generate_art(
        self, prompt: str, mode: Optional[GenerationMode] = None
    ) -> Dict[str, Any]:
        """Generate art using specified mode.

        Args:
            prompt: Art description
            mode: Generation mode (None = use self.mode)

        Returns:
            Generation result with metadata
        """
        mode = mode or self.mode

        if mode == GenerationMode.AUTO:
            mode = await self._decide_mode(prompt)

        if mode == GenerationMode.ASCII_DIRECT:
            return await self._generate_ascii_direct(prompt)
        elif mode == GenerationMode.PRIMITIVES:
            return await self._generate_primitives(prompt)
        elif mode == GenerationMode.HYBRID:
            return await self._generate_hybrid(prompt)

        raise ValueError(f"Unknown mode: {mode}")

    async def _decide_mode(self, prompt: str) -> GenerationMode:
        """Let LLM decide best generation mode."""
        if not self.llm:
            return GenerationMode.ASCII_DIRECT

        decision_prompt = f"""
Decide the best mode to generate this art: "{prompt}"

Modes:
- ascii: For text, logos, icons, simple art (fast)
- primitives: For geometric shapes, diagrams, UI (precise)
- hybrid: For complex scenes combining both (best quality)

Return ONLY the mode name.
"""

        try:
            response = await self.llm.query(decision_prompt)
            mode_str = response.strip().lower()

            if "ascii" in mode_str:
                return GenerationMode.ASCII_DIRECT
            elif "primitive" in mode_str:
                return GenerationMode.PRIMITIVES
            elif "hybrid" in mode_str:
                return GenerationMode.HYBRID
            else:
                return GenerationMode.ASCII_DIRECT
        except Exception as e:
            logger.warning(f"Mode decision failed: {e}, using ASCII")
            return GenerationMode.ASCII_DIRECT

    # ═══════════════════════════════════════════════════════════════════════════
    # Mode 1: ASCII Direct
    # ═══════════════════════════════════════════════════════════════════════════

    async def _generate_ascii_direct(self, prompt: str) -> Dict[str, Any]:
        """Generate complete ASCII art directly."""
        if not self.llm:
            return {"error": "LLM client not available"}

        width = self.paint_app.image.width
        height = self.paint_app.image.height

        art_prompt = f"""
Generate ASCII/ANSI art for: {prompt}

Canvas size: {width}x{height} characters
Use these characters: █▓▒░ ·•○●◆◇■□▪▫
Use colors via ANSI codes if appropriate.

Return ONLY the art, no explanation or markdown.
Each line must be exactly {width} characters (pad with spaces).
Generate exactly {height} lines.
"""

        try:
            art = await self.llm.query(art_prompt)

            # Render to canvas
            lines = art.split("\n")[:height]
            for y, line in enumerate(lines):
                line = line[:width].ljust(width)  # Ensure exact width
                for x, char in enumerate(line):
                    if 0 <= x < width and 0 <= y < height:
                        self.paint_app.image.ch[y][x] = char

            self.paint_app.canvas.refresh()

            result = {
                "mode": "ascii_direct",
                "prompt": prompt,
                "art": art,
                "success": True,
            }
            self._generation_history.append(result)
            return result

        except Exception as e:
            logger.error(f"ASCII generation failed: {e}")
            return {"error": str(e), "success": False}

    # ═══════════════════════════════════════════════════════════════════════════
    # Mode 2: Primitives JSON
    # ═══════════════════════════════════════════════════════════════════════════

    async def _generate_primitives(self, prompt: str) -> Dict[str, Any]:
        """Generate structured drawing primitives."""
        if not self.llm:
            return {"error": "LLM client not available"}

        width = self.paint_app.image.width
        height = self.paint_app.image.height

        primitives_prompt = f"""
Create a drawing plan for: {prompt}

Canvas: {width}x{height}
Return JSON with drawing primitives:

{{
    "shapes": [
        {{"type": "circle", "x": 10, "y": 10, "radius": 5, "color": "#FF0000", "filled": true}},
        {{"type": "rectangle", "x": 0, "y": 0, "width": 20, "height": 10, "color": "#00FF00"}},
        {{"type": "line", "x1": 0, "y1": 0, "x2": 20, "y2": 20, "color": "#0000FF"}},
        {{"type": "text", "x": 5, "y": 5, "text": "Hello", "color": "#FFFFFF"}},
        {{"type": "polygon", "points": [[0,0], [10,0], [5,10]], "color": "#FFFF00"}}
    ]
}}

Return ONLY valid JSON, no markdown or explanation.
"""

        try:
            response = await self.llm.query(primitives_prompt)

            # Parse JSON
            response = response.strip()
            if response.startswith("```"):
                response = response.split("```")[1]
                if response.startswith("json"):
                    response = response[4:]

            plan = json.loads(response)

            # Execute primitives
            for shape in plan.get("shapes", []):
                self._draw_primitive(shape)

            self.paint_app.canvas.refresh()

            result = {
                "mode": "primitives",
                "prompt": prompt,
                "plan": plan,
                "success": True,
            }
            self._generation_history.append(result)
            return result

        except Exception as e:
            logger.error(f"Primitives generation failed: {e}")
            return {"error": str(e), "success": False}

    def _draw_primitive(self, shape: Dict[str, Any]) -> None:
        """Draw a single primitive shape."""
        shape_type = shape.get("type")
        color = shape.get("color", "#FFFFFF")

        if shape_type == "circle":
            self._draw_circle_primitive(
                shape["x"],
                shape["y"],
                shape["radius"],
                color,
                shape.get("filled", False),
            )
        elif shape_type == "rectangle":
            self._draw_rectangle_primitive(
                shape["x"], shape["y"], shape["width"], shape["height"], color
            )
        elif shape_type == "line":
            self._draw_line_primitive(
                shape["x1"], shape["y1"], shape["x2"], shape["y2"], color
            )
        elif shape_type == "text":
            self._draw_text_primitive(shape["x"], shape["y"], shape["text"], color)
        elif shape_type == "polygon":
            self._draw_polygon_primitive(shape["points"], color)

    def _draw_circle_primitive(
        self, cx: int, cy: int, r: int, color: str, filled: bool
    ) -> None:
        """Draw circle primitive."""
        for y in range(max(0, cy - r), min(self.paint_app.image.height, cy + r + 1)):
            for x in range(max(0, cx - r), min(self.paint_app.image.width, cx + r + 1)):
                dist = ((x - cx) ** 2 + (y - cy) ** 2) ** 0.5
                if (filled and dist <= r) or (not filled and abs(dist - r) < 1):
                    self.paint_app.image.ch[y][x] = "█"
                    self.paint_app.image.st[y][x] = Style(color=color)

    def _draw_rectangle_primitive(
        self, x: int, y: int, w: int, h: int, color: str
    ) -> None:
        """Draw rectangle primitive."""
        for dy in range(h):
            for dx in range(w):
                px, py = x + dx, y + dy
                if (
                    0 <= px < self.paint_app.image.width
                    and 0 <= py < self.paint_app.image.height
                ):
                    self.paint_app.image.ch[py][px] = "█"
                    self.paint_app.image.st[py][px] = Style(color=color)

    def _draw_line_primitive(
        self, x1: int, y1: int, x2: int, y2: int, color: str
    ) -> None:
        """Draw line primitive using Bresenham."""
        dx = abs(x2 - x1)
        dy = abs(y2 - y1)
        sx = 1 if x1 < x2 else -1
        sy = 1 if y1 < y2 else -1
        err = dx - dy

        x, y = x1, y1
        while True:
            if (
                0 <= x < self.paint_app.image.width
                and 0 <= y < self.paint_app.image.height
            ):
                self.paint_app.image.ch[y][x] = "█"
                self.paint_app.image.st[y][x] = Style(color=color)

            if x == x2 and y == y2:
                break

            e2 = 2 * err
            if e2 > -dy:
                err -= dy
                x += sx
            if e2 < dx:
                err += dx
                y += sy

    def _draw_text_primitive(self, x: int, y: int, text: str, color: str) -> None:
        """Draw text primitive."""
        for i, char in enumerate(text):
            px = x + i
            if (
                0 <= px < self.paint_app.image.width
                and 0 <= y < self.paint_app.image.height
            ):
                self.paint_app.image.ch[y][px] = char
                self.paint_app.image.st[y][px] = Style(color=color)

    def _draw_polygon_primitive(self, points: List[List[int]], color: str) -> None:
        """Draw polygon primitive."""
        if len(points) < 3:
            return

        # Draw edges
        for i in range(len(points)):
            p1 = points[i]
            p2 = points[(i + 1) % len(points)]
            self._draw_line_primitive(p1[0], p1[1], p2[0], p2[1], color)

    # ═══════════════════════════════════════════════════════════════════════════
    # Mode 3: Hybrid
    # ═══════════════════════════════════════════════════════════════════════════

    async def _generate_hybrid(self, prompt: str) -> Dict[str, Any]:
        """Generate using hybrid approach (ASCII + Primitives)."""
        if not self.llm:
            return {"error": "LLM client not available"}

        width = self.paint_app.image.width
        height = self.paint_app.image.height

        hybrid_prompt = f"""
Create art for: {prompt}

Canvas: {width}x{height}

Use HYBRID approach:
1. Background/texture: ASCII art
2. Foreground/shapes: JSON primitives

Return JSON:
{{
    "background": "ASCII art here (multiline)",
    "shapes": [
        {{"type": "circle", "x": 10, "y": 10, "radius": 5, "color": "#FF0000"}}
    ]
}}

Return ONLY valid JSON.
"""

        try:
            response = await self.llm.query(hybrid_prompt)

            # Parse JSON
            response = response.strip()
            if response.startswith("```"):
                response = response.split("```")[1]
                if response.startswith("json"):
                    response = response[4:]

            plan = json.loads(response)

            # 1. Render background ASCII
            if "background" in plan:
                lines = plan["background"].split("\n")[:height]
                for y, line in enumerate(lines):
                    line = line[:width].ljust(width)
                    for x, char in enumerate(line):
                        if 0 <= x < width and 0 <= y < height:
                            self.paint_app.image.ch[y][x] = char

            # 2. Draw foreground primitives
            for shape in plan.get("shapes", []):
                self._draw_primitive(shape)

            self.paint_app.canvas.refresh()

            result = {"mode": "hybrid", "prompt": prompt, "plan": plan, "success": True}
            self._generation_history.append(result)
            return result

        except Exception as e:
            logger.error(f"Hybrid generation failed: {e}")
            return {"error": str(e), "success": False}

    # ═══════════════════════════════════════════════════════════════════════════
    # Utility Methods
    # ═══════════════════════════════════════════════════════════════════════════

    def set_mode(self, mode: GenerationMode) -> None:
        """Set default generation mode."""
        self.mode = mode

    def get_history(self) -> List[Dict[str, Any]]:
        """Get generation history."""
        return self._generation_history

    def clear_history(self) -> None:
        """Clear generation history."""
        self._generation_history.clear()

    async def refine_last(self, feedback: str) -> Dict[str, Any]:
        """Refine last generation based on feedback."""
        if not self._generation_history:
            return {"error": "No previous generation to refine"}

        last = self._generation_history[-1]
        original_prompt = last.get("prompt", "")

        refined_prompt = f"{original_prompt}\n\nRefinement: {feedback}"

        # Get mode from last generation
        last_mode_str = last.get("mode", "auto")
        mode_map = {
            "ascii_direct": GenerationMode.ASCII_DIRECT,
            "primitives": GenerationMode.PRIMITIVES,
            "hybrid": GenerationMode.HYBRID,
            "auto": GenerationMode.AUTO,
        }
        mode = mode_map.get(last_mode_str, GenerationMode.AUTO)

        return await self.generate_art(refined_prompt, mode=mode)
