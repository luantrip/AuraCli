"""
Enhanced Paint Agent - AI Assistant for the Paint Tool.

This module provides an intelligent agent that can:
- Draw shapes using natural language commands
- Use the existing graphics_primitives for accurate drawing
- Maintain conversation context for iterative drawing
- Integrate with other Aura CLI tools
"""

import math
import random
import re
from typing import Any, Dict, List, Optional, Tuple

from rich.style import Style

# Import graphics primitives for accurate drawing
try:
    from . import graphics_primitives as _primitives

    bezier_curve_walk: Any = _primitives.bezier_curve_walk
    bresenham_walk: Any = _primitives.bresenham_walk
    flood_fill: Any = _primitives.flood_fill
    midpoint_ellipse: Any = _primitives.midpoint_ellipse
    polygon_walk: Any = _primitives.polygon_walk
except ImportError:
    bresenham_walk = None
    midpoint_ellipse = None
    polygon_walk = None
    bezier_curve_walk = None
    flood_fill = None


# Color name to hex mapping (expanded)
COLOR_MAP: Dict[str, str] = {
    # Basic colors
    "red": "#FF0000",
    "green": "#00FF00",
    "blue": "#0000FF",
    "yellow": "#FFFF00",
    "cyan": "#00FFFF",
    "magenta": "#FF00FF",
    "white": "#FFFFFF",
    "black": "#000000",
    # Extended colors
    "orange": "#FFA500",
    "pink": "#FFC0CB",
    "purple": "#800080",
    "brown": "#A52A2A",
    "gray": "#808080",
    "grey": "#808080",
    "lime": "#00FF00",
    "navy": "#000080",
    "teal": "#008080",
    "olive": "#808000",
    "maroon": "#800000",
    "aqua": "#00FFFF",
    "silver": "#C0C0C0",
    "gold": "#FFD700",
    "coral": "#FF7F50",
    "salmon": "#FA8072",
    "indigo": "#4B0082",
    "violet": "#EE82EE",
    "turquoise": "#40E0D0",
    "tan": "#D2B48C",
    "crimson": "#DC143C",
    "darkgreen": "#006400",
    "darkblue": "#00008B",
    "darkred": "#8B0000",
    "lightblue": "#ADD8E6",
    "lightgreen": "#90EE90",
    "lightyellow": "#FFFFE0",
}


class DrawingContext:
    """Maintains context for iterative drawing sessions."""

    def __init__(self):
        self.last_shape: Optional[str] = None
        self.last_position: Optional[Tuple[int, int]] = None
        self.last_size: Optional[int] = None
        self.last_color: Optional[str] = None
        self.objects: List[Dict[str, Any]] = []  # Track drawn objects
        self.conversation_history: List[Dict[str, str]] = []

    def add_object(self, obj_type: str, params: Dict[str, Any]) -> int:
        """Add an object to the context and return its ID."""
        obj_id = len(self.objects)
        self.objects.append({"id": obj_id, "type": obj_type, **params})
        self.last_shape = obj_type
        if "x" in params and "y" in params:
            self.last_position = (params["x"], params["y"])
        if "size" in params:
            self.last_size = params["size"]
        if "color" in params:
            self.last_color = params["color"]
        return obj_id

    def get_object(self, obj_id: int) -> Optional[Dict[str, Any]]:
        """Get an object by ID."""
        if 0 <= obj_id < len(self.objects):
            return self.objects[obj_id]
        return None

    def add_message(self, role: str, content: str):
        """Add a message to conversation history."""
        self.conversation_history.append({"role": role, "content": content})
        # Keep last 20 messages for context
        if len(self.conversation_history) > 20:
            self.conversation_history = self.conversation_history[-20:]


class PaintAgent:
    """Enhanced AI agent for the Paint tool with context awareness and advanced drawing."""

    def __init__(self, paint_app: Optional[Any] = None, llm_client=None) -> None:
        self.paint_app = paint_app
        self.context = DrawingContext()
        self.llm_agent = None

        # Initialize LLM agent if available
        if llm_client:
            try:
                from .generator import LLMPaintAgent

                self.llm_agent = LLMPaintAgent(paint_app, llm_client)
            except ImportError as _e:
                pass  # silenced

        # Command registry with patterns and handlers
        self.command_patterns: list[tuple[str, Any]] = [
            # LLM Generation Commands (NEW!)
            (
                r"(?:generate|create|draw)\s+(?:using\s+)?(?:llm|ai|auto)\s+(.+)",
                self._llm_generate_auto,
            ),
            (
                r"(?:generate|create|draw)\s+(?:using\s+)?ascii\s+(.+)",
                self._llm_generate_ascii,
            ),
            (
                r"(?:generate|create|draw)\s+(?:using\s+)?primitives\s+(.+)",
                self._llm_generate_primitives,
            ),
            (
                r"(?:generate|create|draw)\s+(?:using\s+)?hybrid\s+(.+)",
                self._llm_generate_hybrid,
            ),
            (
                r"refine\s+(?:last\s+)?(?:with\s+)?(.+)",
                self._llm_refine,
            ),
            # Shape commands
            (
                r"(?:draw|create|make)?\s*(?:a\s+)?(?P<color>\w+)?\s*square\s*(?:of\s+)?(?:size\s+)?(?P<size>\d+)?(?:\s+at\s+(?P<x>\d+)\s*,?\s*(?P<y>\d+))?",
                self._draw_square,
            ),
            (
                r"(?:draw|create|make)?\s*(?:a\s+)?(?P<color>\w+)?\s*(?:filled\s+)?rectangle\s*(?:(?P<width>\d+)\s*x\s*(?P<height>\d+))?(?:\s+at\s+(?P<x>\d+)\s*,?\s*(?P<y>\d+))?",
                self._draw_rectangle,
            ),
            (
                r"(?:draw|create|make)?\s*(?:a\s+)?(?P<color>\w+)?\s*circle\s*(?:with\s+)?(?:radius\s+)?(?P<radius>\d+)?(?:\s+at\s+(?P<x>\d+)\s*,?\s*(?P<y>\d+))?",
                self._draw_circle,
            ),
            (
                r"(?:draw|create|make)?\s*(?:a\s+)?(?P<color>\w+)?\s*(?:filled\s+)?ellipse\s*(?:(?P<rx>\d+)\s*x\s*(?P<ry>\d+))?(?:\s+at\s+(?P<x>\d+)\s*,?\s*(?P<y>\d+))?",
                self._draw_ellipse,
            ),
            (
                r"(?:draw|create|make)?\s*(?:a\s+)?(?P<color>\w+)?\s*line\s*(?:from\s+)?(?P<x1>\d+)\s*,?\s*(?P<y1>\d+)\s*(?:to\s+)?(?P<x2>\d+)\s*,?\s*(?P<y2>\d+)",
                self._draw_line,
            ),
            (
                r"(?:draw|create|make)?\s*(?:a\s+)?(?P<color>\w+)?\s*triangle\s*(?:of\s+)?(?:size\s+)?(?P<size>\d+)?(?:\s+at\s+(?P<x>\d+)\s*,?\s*(?P<y>\d+))?",
                self._draw_triangle,
            ),
            (
                r"(?:draw|create|make)?\s*(?:a\s+)?(?P<color>\w+)?\s*star\s*(?:of\s+)?(?:size\s+)?(?P<size>\d+)?(?:\s+at\s+(?P<x>\d+)\s*,?\s*(?P<y>\d+))?",
                self._draw_star,
            ),
            (
                r"(?:draw|create|make)?\s*(?:a\s+)?(?P<color>\w+)?\s*heart\s*(?:of\s+)?(?:size\s+)?(?P<size>\d+)?(?:\s+at\s+(?P<x>\d+)\s*,?\s*(?P<y>\d+))?",
                self._draw_heart,
            ),
            # Text commands
            (
                r"(?:write|type|draw)\s*(?:text\s+)?['\"](?P<text>[^'\"]+)['\"](?:\s+in\s+(?P<color>\w+))?(?:\s+at\s+(?P<x>\d+)\s*,?\s*(?P<y>\d+))?",
                self._draw_text,
            ),
            (
                r"(?:write|type|draw)\s+(?P<text>.+?)(?:\s+in\s+(?P<color>\w+))?(?:\s+at\s+(?P<x>\d+)\s*,?\s*(?P<y>\d+))?$",
                self._draw_text,
            ),
            # Fill commands
            (
                r"fill\s*(?:with\s+)?(?P<color>\w+)?(?:\s+at\s+(?P<x>\d+)\s*,?\s*(?P<y>\d+))?",
                self._fill_area,
            ),
            (
                r"bucket\s*(?P<color>\w+)?(?:\s+at\s+(?P<x>\d+)\s*,?\s*(?P<y>\d+))?",
                self._fill_area,
            ),
            # Canvas operations
            (r"clear(?:\s+(?:the\s+)?canvas)?", self._clear_canvas),
            (r"undo", self._undo),
            (r"redo", self._redo),
            # Context-aware commands
            (
                r"(?:make\s+)?(?:it\s+)?bigger(?:\s+by\s+(?P<amount>\d+))?",
                self._make_bigger,
            ),
            (
                r"(?:make\s+)?(?:it\s+)?smaller(?:\s+by\s+(?P<amount>\d+))?",
                self._make_smaller,
            ),
            (
                r"move\s+(?:it\s+)?(?P<direction>up|down|left|right)(?:\s+by\s+(?P<amount>\d+))?",
                self._move_last,
            ),
            (
                r"change\s+(?:the\s+)?color\s+(?:to\s+)?(?P<color>\w+)",
                self._change_color,
            ),
            (r"repeat(?:\s+(?P<times>\d+)\s+times)?", self._repeat_last),
            # Pattern commands
            (
                r"(?:draw|create)\s+(?:a\s+)?grid\s*(?:(?P<cols>\d+)\s*x\s*(?P<rows>\d+))?(?:\s+of\s+(?P<color>\w+))?",
                self._draw_grid,
            ),
            (
                r"(?:draw|create)\s+(?:a\s+)?border(?:\s+in\s+(?P<color>\w+))?",
                self._draw_border,
            ),
            (r"(?:draw|create)\s+(?:a\s+)?rainbow", self._draw_rainbow),
            (
                r"(?:draw|create)\s+(?:a\s+)?gradient\s*(?:from\s+)?(?P<color1>\w+)\s*(?:to\s+)?(?P<color2>\w+)?",
                self._draw_gradient,
            ),
            # ASCII art commands
            (r"(?:draw|create)\s+(?:a\s+)?house", self._draw_house),
            (r"(?:draw|create)\s+(?:a\s+)?tree", self._draw_tree),
            (r"(?:draw|create)\s+(?:a\s+)?smiley(?:\s+face)?", self._draw_smiley),
            # Help
            (r"help|commands|what can you do", self._show_help),
        ]

    @property
    def image(self):
        """Get the image document (from paint_app or headless document)."""
        if self.paint_app:
            return self.paint_app.image
        return None

    async def process_message(self, message: str) -> None:
        """Process a user message and execute the appropriate command."""
        message_lower = message.lower().strip()
        self.context.add_message("user", message)

        if not message_lower:
            await self._send_response(
                "Please provide a command. Type 'help' for available commands."
            )
            return

        # Try to match against patterns
        for pattern, handler in self.command_patterns:
            match = re.match(pattern, message_lower, re.IGNORECASE)
            if match:
                try:
                    await handler(**match.groupdict())
                    return
                except Exception as e:
                    await self._send_response(f"Error executing command: {e}")
                    return

        # No pattern matched - provide helpful response
        await self._send_response(
            f"I didn't understand '{message}'. Try commands like:\n"
            "• 'draw a red circle'\n"
            "• 'write \"Hello World\"'\n"
            "• 'clear canvas'\n"
            "Type 'help' for all commands."
        )

    async def _send_response(self, message: str) -> None:
        """Send a response message to the chat."""
        self.context.add_message("agent", message)
        if self.paint_app:
            await self.paint_app.send_message_to_chat("Agent", message, "agent")

    def _parse_color(self, color_name: Optional[str]) -> str:
        """Parse a color name to hex value."""
        if not color_name or color_name == "random":
            return random.choice(list(COLOR_MAP.values()))
        color_lower = color_name.lower()
        if color_lower in COLOR_MAP:
            return COLOR_MAP[color_lower]
        # Try to use last color from context
        if self.context.last_color:
            return self.context.last_color
        return "#FFFFFF"  # Default to white

    def _get_position(
        self, x: Optional[str], y: Optional[str], size: int = 10
    ) -> Tuple[int, int]:
        """Get position, using random if not specified."""
        if x is not None and y is not None:
            return int(x), int(y)
        # Random position that fits the shape
        image = self.image
        if not image:
            return 0, 0
        max_x = max(0, image.width - size - 1)
        max_y = max(0, image.height - size - 1)
        return random.randint(0, max_x), random.randint(0, max_y)

    def _stamp_pixel(self, x: int, y: int, color: str, char: str = "█") -> None:
        """Stamp a single pixel with the given color."""
        image = self.image
        if not image:
            return
        if 0 <= x < image.width and 0 <= y < image.height:
            image.ch[y][x] = char
            image.st[y][x] = Style(color=color, bgcolor=color)

    def _draw_line_pixels(self, x1: int, y1: int, x2: int, y2: int, color: str) -> None:
        """Draw a line using Bresenham's algorithm."""
        image = self.image
        if not image:
            return
        if bresenham_walk:
            for x, y in bresenham_walk(x1, y1, x2, y2):
                self._stamp_pixel(x, y, color)
        else:
            # Fallback implementation
            dx = abs(x2 - x1)
            dy = abs(y2 - y1)
            sx = 1 if x1 < x2 else -1
            sy = 1 if y1 < y2 else -1
            err = dx - dy
            x, y = x1, y1
            while True:
                self._stamp_pixel(x, y, color)
                if x == x2 and y == y2:
                    break
                e2 = 2 * err
                if e2 > -dy:
                    err -= dy
                    x += sx
                if e2 < dx:
                    err += dx
                    y += sy

    # ═══════════════════════════════════════════════════════════════════════════
    # LLM Generation Commands (NEW!)
    # ═══════════════════════════════════════════════════════════════════════════

    async def _llm_generate_auto(self, prompt: str | None = None, **kwargs) -> None:
        """Generate art using LLM (auto mode)."""
        if not self.llm_agent:
            await self._send_response(
                "LLM agent not available. Initialize with LLM client."
            )
            return

        from .generator import GenerationMode

        result = await self.llm_agent.generate_art(
            prompt or "", mode=GenerationMode.AUTO
        )

        if result.get("success"):
            await self._send_response(
                f"✓ Generated '{prompt}' using {result['mode']} mode"
            )
        else:
            await self._send_response(f"✗ Generation failed: {result.get('error')}")

    async def _llm_generate_ascii(self, prompt: str | None = None, **kwargs) -> None:
        """Generate art using LLM (ASCII mode)."""
        if not self.llm_agent:
            await self._send_response("LLM agent not available.")
            return

        from .generator import GenerationMode

        result = await self.llm_agent.generate_art(
            prompt or "", mode=GenerationMode.ASCII_DIRECT
        )

        if result.get("success"):
            await self._send_response(f"✓ Generated ASCII art: '{prompt}'")
        else:
            await self._send_response(f"✗ Generation failed: {result.get('error')}")

    async def _llm_generate_primitives(
        self, prompt: str | None = None, **kwargs
    ) -> None:
        """Generate art using LLM (primitives mode)."""
        if not self.llm_agent:
            await self._send_response("LLM agent not available.")
            return

        from .generator import GenerationMode

        result = await self.llm_agent.generate_art(
            prompt or "", mode=GenerationMode.PRIMITIVES
        )

        if result.get("success"):
            shapes_count = len(result.get("plan", {}).get("shapes", []))
            await self._send_response(
                f"✓ Generated {shapes_count} shapes for '{prompt}'"
            )
        else:
            await self._send_response(f"✗ Generation failed: {result.get('error')}")

    async def _llm_generate_hybrid(self, prompt: str | None = None, **kwargs) -> None:
        """Generate art using LLM (hybrid mode)."""
        if not self.llm_agent:
            await self._send_response("LLM agent not available.")
            return

        from .generator import GenerationMode

        result = await self.llm_agent.generate_art(
            prompt or "", mode=GenerationMode.HYBRID
        )

        if result.get("success"):
            await self._send_response(f"✓ Generated hybrid art: '{prompt}'")
        else:
            await self._send_response(f"✗ Generation failed: {result.get('error')}")

    async def _llm_refine(self, feedback: str | None = None, **kwargs) -> None:
        """Refine last LLM generation."""
        if not self.llm_agent:
            await self._send_response("LLM agent not available.")
            return

        result = await self.llm_agent.refine_last(feedback or "")

        if result.get("success"):
            await self._send_response(f"✓ Refined with: '{feedback}'")
        else:
            await self._send_response(f"✗ Refinement failed: {result.get('error')}")

    # ═══════════════════════════════════════════════════════════════════════════
    # Shape Drawing Commands
    # ═══════════════════════════════════════════════════════════════════════════

    async def _draw_square(
        self,
        color: Optional[str] = None,
        size: Optional[str] = None,
        x: Optional[str] = None,
        y: Optional[str] = None,
        **kwargs,
    ) -> None:
        """Draw a square."""
        s = int(size) if size else self.context.last_size or 10
        color_hex = self._parse_color(color)
        pos_x, pos_y = self._get_position(x, y, s)

        # Draw filled square
        for dy in range(s):
            for dx in range(s):
                self._stamp_pixel(pos_x + dx, pos_y + dy, color_hex)

        if self.paint_app and self.paint_app.canvas:
            self.paint_app.canvas.refresh()

        obj_id = self.context.add_object(
            "square", {"x": pos_x, "y": pos_y, "size": s, "color": color_hex}
        )

        await self._send_response(
            f"Drew a {color or 'colored'} square (size {s}) at ({pos_x}, {pos_y}) [id: {obj_id}]"
        )

    async def _draw_rectangle(
        self,
        color: Optional[str] = None,
        width: Optional[str] = None,
        height: Optional[str] = None,
        x: Optional[str] = None,
        y: Optional[str] = None,
        **kwargs,
    ) -> None:
        """Draw a rectangle."""
        w = int(width) if width else 15
        h = int(height) if height else 10
        color_hex = self._parse_color(color)
        pos_x, pos_y = self._get_position(x, y, max(w, h))

        for dy in range(h):
            for dx in range(w):
                self._stamp_pixel(pos_x + dx, pos_y + dy, color_hex)

        if self.paint_app and self.paint_app.canvas:
            self.paint_app.canvas.refresh()

        obj_id = self.context.add_object(
            "rectangle",
            {"x": pos_x, "y": pos_y, "width": w, "height": h, "color": color_hex},
        )

        await self._send_response(
            f"Drew a {color or 'colored'} rectangle ({w}x{h}) at ({pos_x}, {pos_y}) [id: {obj_id}]"
        )

    async def _draw_circle(
        self,
        color: Optional[str] = None,
        radius: Optional[str] = None,
        x: Optional[str] = None,
        y: Optional[str] = None,
        **kwargs,
    ) -> None:
        """Draw a circle using midpoint algorithm."""
        r = int(radius) if radius else 5
        color_hex = self._parse_color(color)
        cx, cy = self._get_position(x, y, r * 2)
        cx += r  # Center the circle
        cy += r

        if midpoint_ellipse:
            for px, py in midpoint_ellipse(cx, cy, r, r):
                self._stamp_pixel(px, py, color_hex)
        else:
            # Fallback: simple circle drawing
            for angle in range(360):
                rad = math.radians(angle)
                px = int(cx + r * math.cos(rad))
                py = int(cy + r * math.sin(rad))
                self._stamp_pixel(px, py, color_hex)

        if self.paint_app and self.paint_app.canvas:
            self.paint_app.canvas.refresh()

        obj_id = self.context.add_object(
            "circle", {"x": cx, "y": cy, "radius": r, "color": color_hex}
        )

        await self._send_response(
            f"Drew a {color or 'colored'} circle (radius {r}) at ({cx}, {cy}) [id: {obj_id}]"
        )

    async def _draw_ellipse(
        self,
        color: Optional[str] = None,
        rx: Optional[str] = None,
        ry: Optional[str] = None,
        x: Optional[str] = None,
        y: Optional[str] = None,
        **kwargs,
    ) -> None:
        """Draw an ellipse."""
        radius_x = int(rx) if rx else 8
        radius_y = int(ry) if ry else 5
        color_hex = self._parse_color(color)
        cx, cy = self._get_position(x, y, max(radius_x, radius_y) * 2)
        cx += radius_x
        cy += radius_y

        if midpoint_ellipse:
            for px, py in midpoint_ellipse(cx, cy, radius_x, radius_y):
                self._stamp_pixel(px, py, color_hex)

        if self.paint_app and self.paint_app.canvas:
            self.paint_app.canvas.refresh()

        obj_id = self.context.add_object(
            "ellipse",
            {"x": cx, "y": cy, "rx": radius_x, "ry": radius_y, "color": color_hex},
        )

        await self._send_response(
            f"Drew a {color or 'colored'} ellipse ({radius_x}x{radius_y}) [id: {obj_id}]"
        )

    async def _draw_line(
        self,
        color: Optional[str] = None,
        x1: Optional[str] = None,
        y1: Optional[str] = None,
        x2: Optional[str] = None,
        y2: Optional[str] = None,
        **kwargs,
    ) -> None:
        """Draw a line."""
        color_hex = self._parse_color(color)
        start_x = int(x1) if x1 else 0
        start_y = int(y1) if y1 else 0
        image = self.image
        if not image:
            return
        end_x = int(x2) if x2 else random.randint(0, image.width - 1)
        end_y = int(y2) if y2 else random.randint(0, image.height - 1)

        self._draw_line_pixels(start_x, start_y, end_x, end_y, color_hex)
        if self.paint_app and self.paint_app.canvas:
            self.paint_app.canvas.refresh()

        obj_id = self.context.add_object(
            "line",
            {
                "x1": start_x,
                "y1": start_y,
                "x2": end_x,
                "y2": end_y,
                "color": color_hex,
            },
        )

        await self._send_response(
            f"Drew a {color or 'colored'} line from ({start_x},{start_y}) to ({end_x},{end_y}) [id: {obj_id}]"
        )

    async def _draw_triangle(
        self,
        color: Optional[str] = None,
        size: Optional[str] = None,
        x: Optional[str] = None,
        y: Optional[str] = None,
        **kwargs,
    ) -> None:
        """Draw a triangle."""
        s = int(size) if size else 10
        color_hex = self._parse_color(color)
        pos_x, pos_y = self._get_position(x, y, s)

        # Draw equilateral triangle
        # Top vertex
        top_x = pos_x + s // 2
        top_y = pos_y
        # Bottom left
        bl_x = pos_x
        bl_y = pos_y + s
        # Bottom right
        br_x = pos_x + s
        br_y = pos_y + s

        self._draw_line_pixels(top_x, top_y, bl_x, bl_y, color_hex)
        self._draw_line_pixels(top_x, top_y, br_x, br_y, color_hex)
        self._draw_line_pixels(bl_x, bl_y, br_x, br_y, color_hex)

        if self.paint_app and self.paint_app.canvas:
            self.paint_app.canvas.refresh()

        obj_id = self.context.add_object(
            "triangle", {"x": pos_x, "y": pos_y, "size": s, "color": color_hex}
        )

        await self._send_response(
            f"Drew a {color or 'colored'} triangle (size {s}) [id: {obj_id}]"
        )

    async def _draw_star(
        self,
        color: Optional[str] = None,
        size: Optional[str] = None,
        x: Optional[str] = None,
        y: Optional[str] = None,
        **kwargs,
    ) -> None:
        """Draw a 5-pointed star."""
        s = int(size) if size else 10
        color_hex = self._parse_color(color)
        pos_x, pos_y = self._get_position(x, y, s)
        cx, cy = pos_x + s // 2, pos_y + s // 2

        # Calculate star points
        outer_r = s // 2
        inner_r = s // 4
        points = []
        for i in range(10):
            angle = math.pi / 2 + i * math.pi / 5
            r = outer_r if i % 2 == 0 else inner_r
            px = int(cx + r * math.cos(angle))
            py = int(cy - r * math.sin(angle))
            points.append((px, py))

        # Draw lines between points
        for i in range(len(points)):
            x1, y1 = points[i]
            x2, y2 = points[(i + 1) % len(points)]
            self._draw_line_pixels(x1, y1, x2, y2, color_hex)

        if self.paint_app and self.paint_app.canvas:
            self.paint_app.canvas.refresh()

        obj_id = self.context.add_object(
            "star", {"x": pos_x, "y": pos_y, "size": s, "color": color_hex}
        )

        await self._send_response(
            f"Drew a {color or 'colored'} star (size {s}) [id: {obj_id}]"
        )

    async def _draw_heart(
        self,
        color: Optional[str] = None,
        size: Optional[str] = None,
        x: Optional[str] = None,
        y: Optional[str] = None,
        **kwargs,
    ) -> None:
        """Draw a heart shape."""
        s = int(size) if size else 10
        color_hex = self._parse_color(color) if color else "#FF0000"
        pos_x, pos_y = self._get_position(x, y, s)

        # Heart shape using parametric equations
        for t in range(360):
            rad = math.radians(t)
            hx = 16 * (math.sin(rad) ** 3)
            hy = (
                13 * math.cos(rad)
                - 5 * math.cos(2 * rad)
                - 2 * math.cos(3 * rad)
                - math.cos(4 * rad)
            )
            px = int(pos_x + s // 2 + hx * s / 32)
            py = int(pos_y + s // 2 - hy * s / 32)
            self._stamp_pixel(px, py, color_hex)

        if self.paint_app and self.paint_app.canvas:
            self.paint_app.canvas.refresh()

        obj_id = self.context.add_object(
            "heart", {"x": pos_x, "y": pos_y, "size": s, "color": color_hex}
        )

        await self._send_response(
            f"Drew a {color or 'red'} heart (size {s}) [id: {obj_id}]"
        )

    # ═══════════════════════════════════════════════════════════════════════════
    # Text Commands
    # ═══════════════════════════════════════════════════════════════════════════

    async def _draw_text(
        self,
        text: Optional[str] = None,
        color: Optional[str] = None,
        x: Optional[str] = None,
        y: Optional[str] = None,
        **kwargs,
    ) -> None:
        """Draw text on the canvas."""
        if not text:
            await self._send_response("Please provide text to draw.")
            return

        color_hex = self._parse_color(color)
        image = self.image
        if not image:
            return
        pos_x = int(x) if x else random.randint(0, max(0, image.width - len(text) - 1))
        pos_y = int(y) if y else random.randint(0, image.height - 1)

        for i, char in enumerate(text):
            if pos_x + i < image.width:
                image.ch[pos_y][pos_x + i] = char
                image.st[pos_y][pos_x + i] = Style(color=color_hex)

        if self.paint_app and self.paint_app.canvas:
            self.paint_app.canvas.refresh()

        obj_id = self.context.add_object(
            "text", {"x": pos_x, "y": pos_y, "text": text, "color": color_hex}
        )

        await self._send_response(
            f"Drew '{text}' in {color or 'white'} at ({pos_x}, {pos_y}) [id: {obj_id}]"
        )

    # ═══════════════════════════════════════════════════════════════════════════
    # Fill Commands
    # ═══════════════════════════════════════════════════════════════════════════

    async def _fill_area(
        self,
        color: Optional[str] = None,
        x: Optional[str] = None,
        y: Optional[str] = None,
        **kwargs,
    ) -> None:
        """Fill an area with color using flood fill."""
        color_hex = self._parse_color(color)
        image = self.image
        if not image:
            return
        fill_x = int(x) if x else image.width // 2
        fill_y = int(y) if y else image.height // 2

        if flood_fill:
            flood_fill(image, fill_x, fill_y, "█", color_hex, color_hex)
            if self.paint_app and self.paint_app.canvas:
                self.paint_app.canvas.refresh()
            await self._send_response(
                f"Filled area at ({fill_x}, {fill_y}) with {color or 'color'}"
            )
        else:
            await self._send_response("Preenchimento não disponível")

    # ═══════════════════════════════════════════════════════════════════════════
    # Canvas Operations
    # ═══════════════════════════════════════════════════════════════════════════

    async def _clear_canvas(self, **kwargs) -> None:
        """Clear the canvas."""
        image = self.image
        if image:
            image.clear()
        if self.paint_app and self.paint_app.canvas:
            self.paint_app.canvas.refresh()
        self.context.objects.clear()
        await self._send_response("Canvas cleared.")

    async def _undo(self, **kwargs) -> None:
        """Undo the last action."""
        paint_app = self.paint_app
        if paint_app is not None and hasattr(paint_app, "undo"):
            paint_app.undo()
            await self._send_response("Undone last action.")
        else:
            await self._send_response("Undo not available.")

    async def _redo(self, **kwargs) -> None:
        """Redo the last undone action."""
        paint_app = self.paint_app
        if paint_app is not None and hasattr(paint_app, "redo"):
            paint_app.redo()
            await self._send_response("Redone last action.")
        else:
            await self._send_response("Redo not available.")

    # ═══════════════════════════════════════════════════════════════════════════
    # Context-Aware Commands
    # ═══════════════════════════════════════════════════════════════════════════

    async def _make_bigger(self, amount: Optional[str] = None, **kwargs) -> None:
        """Make the last shape bigger."""
        if not self.context.objects:
            await self._send_response("No previous shape to resize.")
            return

        delta = int(amount) if amount else 2
        last_obj = self.context.objects[-1]

        # Redraw with larger size
        if last_obj["type"] in ["square", "circle", "triangle", "star", "heart"]:
            new_size = last_obj.get("size", 10) + delta
            await getattr(self, f"_draw_{last_obj['type']}")(
                color=last_obj.get("color"),
                size=str(new_size),
                x=str(last_obj.get("x", 0)),
                y=str(last_obj.get("y", 0)),
            )
        else:
            await self._send_response(f"Cannot resize {last_obj['type']}")

    async def _make_smaller(self, amount: Optional[str] = None, **kwargs) -> None:
        """Make the last shape smaller."""
        if not self.context.objects:
            await self._send_response("No previous shape to resize.")
            return

        delta = int(amount) if amount else 2
        last_obj = self.context.objects[-1]

        if last_obj["type"] in ["square", "circle", "triangle", "star", "heart"]:
            new_size = max(2, last_obj.get("size", 10) - delta)
            await getattr(self, f"_draw_{last_obj['type']}")(
                color=last_obj.get("color"),
                size=str(new_size),
                x=str(last_obj.get("x", 0)),
                y=str(last_obj.get("y", 0)),
            )
        else:
            await self._send_response(f"Cannot resize {last_obj['type']}")

    async def _move_last(
        self, direction: str, amount: Optional[str] = None, **kwargs
    ) -> None:
        """Move the last shape in a direction."""
        await self._send_response(
            f"Move command noted (would move {direction} by {amount or 5}). Full implementation pending."
        )

    async def _change_color(self, color: str, **kwargs) -> None:
        """Change the color of the last shape."""
        await self._send_response(
            f"Would change color to {color}. Full implementation pending."
        )

    async def _repeat_last(self, times: Optional[str] = None, **kwargs) -> None:
        """Repeat the last command."""
        if not self.context.objects:
            await self._send_response("No previous command to repeat.")
            return

        n = int(times) if times else 1
        last_obj = self.context.objects[-1]

        for _ in range(n):
            if last_obj["type"] in ["square", "circle", "triangle", "star", "heart"]:
                await getattr(self, f"_draw_{last_obj['type']}")(
                    color=last_obj.get("color"), size=str(last_obj.get("size", 10))
                )

        await self._send_response(f"Repeated {last_obj['type']} {n} time(s)")

    # ═══════════════════════════════════════════════════════════════════════════
    # Pattern Commands
    # ═══════════════════════════════════════════════════════════════════════════

    async def _draw_grid(
        self,
        cols: Optional[str] = None,
        rows: Optional[str] = None,
        color: Optional[str] = None,
        **kwargs,
    ) -> None:
        """Draw a grid pattern."""
        num_cols = int(cols) if cols else 10
        num_rows = int(rows) if rows else 10
        color_hex = self._parse_color(color)

        image = self.image
        if not image:
            return
        cell_w = image.width // num_cols
        cell_h = image.height // num_rows

        # Draw vertical lines
        for i in range(num_cols + 1):
            x = i * cell_w
            self._draw_line_pixels(x, 0, x, image.height - 1, color_hex)

        # Draw horizontal lines
        for i in range(num_rows + 1):
            y = i * cell_h
            self._draw_line_pixels(0, y, image.width - 1, y, color_hex)

        if self.paint_app and self.paint_app.canvas:
            self.paint_app.canvas.refresh()
        await self._send_response(
            f"Drew a {num_cols}x{num_rows} grid in {color or 'white'}"
        )

    async def _draw_border(self, color: Optional[str] = None, **kwargs) -> None:
        """Draw a border around the canvas."""
        color_hex = self._parse_color(color)
        image = self.image
        if not image:
            return
        w = image.width
        h = image.height

        self._draw_line_pixels(0, 0, w - 1, 0, color_hex)
        self._draw_line_pixels(0, h - 1, w - 1, h - 1, color_hex)
        self._draw_line_pixels(0, 0, 0, h - 1, color_hex)
        self._draw_line_pixels(w - 1, 0, w - 1, h - 1, color_hex)

        if self.paint_app and self.paint_app.canvas:
            self.paint_app.canvas.refresh()
        await self._send_response(f"Drew a {color or 'white'} border")

    async def _draw_rainbow(self, **kwargs) -> None:
        """Draw a rainbow."""
        image = self.image
        if image is None:
            await self._send_response("Canvas not available.")
            return
        colors = [
            "#FF0000",
            "#FF7F00",
            "#FFFF00",
            "#00FF00",
            "#0000FF",
            "#4B0082",
            "#9400D3",
        ]
        h = image.height
        stripe_height = h // len(colors)

        for i, color in enumerate(colors):
            y_start = i * stripe_height
            y_end = (i + 1) * stripe_height
            for y in range(y_start, min(y_end, h)):
                for x in range(image.width):
                    self._stamp_pixel(x, y, color)

        if self.paint_app and self.paint_app.canvas:
            self.paint_app.canvas.refresh()
        await self._send_response("Drew a rainbow! 🌈")

    async def _draw_gradient(
        self, color1: Optional[str] = None, color2: Optional[str] = None, **kwargs
    ) -> None:
        """Draw a gradient between two colors."""
        image = self.image
        if image is None:
            await self._send_response("Canvas not available.")
            return
        c1 = self._parse_color(color1) if color1 else "#000000"
        c2 = self._parse_color(color2) if color2 else "#FFFFFF"

        # Simple horizontal gradient
        w = image.width
        for x in range(w):
            ratio = x / w
            # Interpolate colors
            r1, g1, b1 = int(c1[1:3], 16), int(c1[3:5], 16), int(c1[5:7], 16)
            r2, g2, b2 = int(c2[1:3], 16), int(c2[3:5], 16), int(c2[5:7], 16)
            r = int(r1 + (r2 - r1) * ratio)
            g = int(g1 + (g2 - g1) * ratio)
            b = int(b1 + (b2 - b1) * ratio)
            color = f"#{r:02x}{g:02x}{b:02x}"

            for y in range(image.height):
                self._stamp_pixel(x, y, color)

        if self.paint_app and self.paint_app.canvas:
            self.paint_app.canvas.refresh()
        await self._send_response(
            f"Drew a gradient from {color1 or 'black'} to {color2 or 'white'}"
        )

    # ═══════════════════════════════════════════════════════════════════════════
    # ASCII Art Presets
    # ═══════════════════════════════════════════════════════════════════════════

    async def _draw_house(self, **kwargs) -> None:
        """Draw a simple house."""
        image = self.image
        if not image:
            return
        cx = image.width // 2
        cy = image.height // 2

        # Roof (triangle)
        await self._draw_triangle(
            color="brown", size="15", x=str(cx - 7), y=str(cy - 15)
        )
        # Body (square)
        await self._draw_square(color="orange", size="15", x=str(cx - 7), y=str(cy))
        # Door (rectangle)
        for dy in range(8):
            for dx in range(4):
                self._stamp_pixel(cx - 2 + dx, cy + 7 + dy, "#654321")

        if self.paint_app and self.paint_app.canvas:
            self.paint_app.canvas.refresh()
        await self._send_response("Drew a house! 🏠")

    async def _draw_tree(self, **kwargs) -> None:
        """Draw a simple tree."""
        image = self.image
        if not image:
            return
        cx = image.width // 2
        cy = image.height // 2

        # Trunk (rectangle)
        for dy in range(10):
            for dx in range(4):
                self._stamp_pixel(cx - 2 + dx, cy + 5 + dy, "#8B4513")

        # Leaves (triangle)
        await self._draw_triangle(
            color="green", size="15", x=str(cx - 7), y=str(cy - 10)
        )

        if self.paint_app and self.paint_app.canvas:
            self.paint_app.canvas.refresh()
        await self._send_response("Drew a tree! 🌲")

    async def _draw_smiley(self, **kwargs) -> None:
        """Draw a smiley face."""
        image = self.image
        if not image:
            return
        cx = image.width // 2
        cy = image.height // 2

        # Face circle
        await self._draw_circle(
            color="yellow", radius="10", x=str(cx - 10), y=str(cy - 10)
        )

        # Eyes
        self._stamp_pixel(cx - 4, cy - 3, "#000000")
        self._stamp_pixel(cx + 4, cy - 3, "#000000")

        # Smile
        for i in range(-4, 5):
            y_offset = abs(i) // 2
            self._stamp_pixel(cx + i, cy + 3 + y_offset, "#000000")

        if self.paint_app and self.paint_app.canvas:
            self.paint_app.canvas.refresh()
        await self._send_response("Drew a smiley face! 😊")

    # ═══════════════════════════════════════════════════════════════════════════
    # Help
    # ═══════════════════════════════════════════════════════════════════════════

    async def _show_help(self, **kwargs) -> None:
        """Show available commands."""
        help_text = """
🎨 **Paint Agent Commands**

**🤖 LLM Generation (NEW!):**
• `generate llm [prompt]` - Auto-select best mode
• `generate ascii [prompt]` - ASCII art mode
• `generate primitives [prompt]` - Geometric shapes mode
• `generate hybrid [prompt]` - Combined mode
• `refine [feedback]` - Refine last generation

**Shapes:**
• `draw [color] square [size]` - Draw a square
• `draw [color] circle [radius]` - Draw a circle
• `draw [color] triangle [size]` - Draw a triangle
• `draw [color] star [size]` - Draw a star
• `draw [color] heart [size]` - Draw a heart
• `draw [color] line x1,y1 to x2,y2` - Draw a line

**Text:**
• `write "text" [in color]` - Write text

**Patterns:**
• `draw grid [cols x rows]` - Draw a grid
• `draw border [color]` - Draw a border
• `draw rainbow` - Draw a rainbow
• `draw gradient [color1] to [color2]` - Draw a gradient

**Presets:**
• `draw house` - Draw a house
• `draw tree` - Draw a tree
• `draw smiley` - Draw a smiley face

**Canvas:**
• `clear` - Clear the canvas
• `undo` / `redo` - Undo/redo actions
• `fill [color]` - Flood fill

**Modifiers:**
• Add `at X,Y` to specify position
• Colors: red, blue, green, yellow, etc.

**Examples:**
• `generate llm Aura CLI logo`
• `generate ascii cute cat`
• `generate primitives geometric pattern`
• `refine make it more colorful`
"""
        await self._send_response(help_text)
