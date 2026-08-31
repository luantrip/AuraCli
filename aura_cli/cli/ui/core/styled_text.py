"""
StyledTextEngine - Advanced text styling with caching and aliases.

Provides efficient parsed text caching, style aliases, and macro support
for the Aura CLI.
"""

from dataclasses import dataclass
from typing import (
    Callable,
    Dict,
    Optional,
    Tuple,
)

from rich.text import Text

from aura_cli.cli.ui.theme_manager import get_theme_manager


@dataclass
class StyleAlias:
    """Defines a style alias mapping."""

    name: str
    style: str
    unsetter: Optional[str] = None


class StyledTextEngine:
    """
    Engine for parsing and rendering styled text with caching.

    Features:
    - LRU caching for parsed styles
    - Custom style aliases (semantic names)
    - Macro support for dynamic content
    - Theme integration
    """

    def __init__(self):
        """Initialize the styled text processor with default aliases and macros."""
        self._aliases: Dict[str, str] = {}
        self._macros: Dict[str, Callable[..., str]] = {}
        self._cache: Dict[str, str] = {}
        self._setup_default_aliases()
        self._setup_default_macros()

    def _setup_default_aliases(self) -> None:
        """Setup default semantic aliases."""
        theme = get_theme_manager()

        self._aliases.update(
            {
                "user": f"bold {theme.get_color('primary')}",
                "agent": f"bold {theme.get_color('accent')}",
                "system": f"dim {theme.get_color('muted')}",
                "error": f"bold {theme.get_color('error')}",
                "success": f"bold {theme.get_color('success')}",
                "warning": f"{theme.get_color('warning')}",
                "code": f"{theme.get_color('code')} on #1a1b26",
                "highlight": f"bold {theme.get_color('highlight')}",
                "link": f"underline {theme.get_color('accent')}",
                "timestamp": f"dim italic {theme.get_color('muted')}",
                "sender": f"bold {theme.get_color('secondary')}",
                "thinking": f"italic {theme.get_color('muted')}",
                "tool": f"bold {theme.get_color('warning')}",
                "file": f"{theme.get_color('success')}",
                "path": f"underline {theme.get_color('accent')}",
                "key": f"bold {theme.get_color('primary')}",
                "value": f"{theme.get_color('body')}",
                "badge": "reverse bold",
                "glow": f"bold {theme.get_color('accent')}",
            }
        )

    def _setup_default_macros(self) -> None:
        """Setup default macros for dynamic content."""
        import time

        self._macros.update(
            {
                "!time": lambda: time.strftime("%H:%M:%S"),
                "!date": lambda: time.strftime("%Y-%m-%d"),
                "!dots": lambda n="3": "." * int(n),
                "!pad": lambda text, width="10": text.ljust(int(width)),
                "!truncate": lambda text, max_len="20": (
                    text[: int(max_len) - 3] + "..."
                    if len(text) > int(max_len)
                    else text
                ),
                "!if": lambda condition, true_val, false_val="": (
                    true_val if condition else false_val
                ),
            }
        )

    def alias(self, name: str, style: str) -> None:
        """Create a style alias."""
        self._aliases[name] = style
        self.clear_cache()

    def define_macro(self, name: str, func: Callable[..., str]) -> None:
        """Define a macro function."""
        if not name.startswith("!"):
            name = f"!{name}"
        self._macros[name] = func

    def resolve_alias(self, name: str) -> str:
        """Resolve an alias to its style string."""
        return self._aliases.get(name, name)

    def clear_cache(self) -> None:
        """Clear the parsed text cache."""
        self._cache.clear()

    def parse(self, markup: str) -> str:
        """
        Parse markup text and resolve aliases.

        Supports Rich markup syntax with alias expansion:
        - [user]text[/user] -> [bold #7aa2f7]text[/bold #7aa2f7]
        - [!time] -> current time
        """
        cached = self._cache.get(markup)
        if cached is not None:
            return cached

        result = markup

        for alias_name, style in self._aliases.items():
            result = result.replace(f"[{alias_name}]", f"[{style}]")
            result = result.replace(f"[/{alias_name}]", f"[/{style}]")

        for macro_name, func in self._macros.items():
            if macro_name in result:
                try:
                    value = func()
                    result = result.replace(f"[{macro_name}]", value)
                except Exception as _e:
                    pass  # silenced: {_e}

        if len(self._cache) >= 512:
            self._cache.pop(next(iter(self._cache)))
        self._cache[markup] = result
        return result

    def render(self, markup: str) -> Text:
        """
        Render markup to Rich Text object.

        Args:
            markup: Text with markup and aliases

        Returns:
            Rich Text object ready for rendering
        """
        parsed = self.parse(markup)
        return Text.from_markup(parsed)

    def styled(self, text: str, *styles: str) -> Text:
        """
        Apply styles to text.

        Args:
            text: Plain text
            styles: Style names (aliases or Rich styles)

        Returns:
            Styled Rich Text object
        """
        resolved_styles = [self.resolve_alias(s) for s in styles]
        combined_style = " ".join(resolved_styles)

        result = Text(text)
        result.stylize(combined_style)
        return result

    def gradient(
        self,
        text: str,
        start_color: str,
        end_color: str,
    ) -> Text:
        """
        Apply gradient effect to text.

        Args:
            text: Text to apply gradient to
            start_color: Starting hex color
            end_color: Ending hex color

        Returns:
            Text with gradient effect
        """
        result = Text()
        length = len(text)

        if length == 0:
            return result

        start_r, start_g, start_b = self._hex_to_rgb(start_color)
        end_r, end_g, end_b = self._hex_to_rgb(end_color)

        for i, char in enumerate(text):
            ratio = i / max(length - 1, 1)
            r = int(start_r + (end_r - start_r) * ratio)
            g = int(start_g + (end_g - start_g) * ratio)
            b = int(start_b + (end_b - start_b) * ratio)
            color = f"#{r:02x}{g:02x}{b:02x}"
            result.append(char, style=color)

        return result

    def glow(self, text: str, color: Optional[str] = None) -> Text:
        """
        Apply glow effect to text (bold + bright color).

        Args:
            text: Text to apply glow to
            color: Optional color override

        Returns:
            Text with glow effect
        """
        theme = get_theme_manager()
        glow_color = color or theme.get_color("accent")
        return self.styled(text, f"bold {glow_color}")

    def badge(self, text: str, variant: str = "primary") -> Text:
        """
        Create a badge/tag style text.

        Args:
            text: Badge text
            variant: Color variant (primary, success, error, warning)

        Returns:
            Badge-styled Text
        """
        theme = get_theme_manager()
        color = theme.get_color(variant)
        result = Text()
        result.append(f" {text} ", style=f"reverse bold {color}")
        return result

    @staticmethod
    def _hex_to_rgb(hex_color: str) -> Tuple[int, int, int]:
        """Convert hex color to RGB tuple."""
        hex_color = hex_color.lstrip("#")
        return (
            int(hex_color[0:2], 16),
            int(hex_color[2:4], 16),
            int(hex_color[4:6], 16),
        )


_engine: Optional[StyledTextEngine] = None


def get_styled_text_engine() -> StyledTextEngine:
    """Get global StyledTextEngine instance."""
    global _engine
    if _engine is None:
        _engine = StyledTextEngine()
    return _engine
