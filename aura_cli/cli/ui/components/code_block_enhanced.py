"""
CodeBlockEnhanced - Advanced code display with interactive features.

Provides premium code display with:
- Line numbers
- Syntax highlighting
- Copy to clipboard action
- Collapsible sections
- Diff highlighting
- Language detection
"""

from dataclasses import dataclass
from typing import ClassVar, List, Optional

import rich.box
from rich.console import Group, RenderableType
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table
from rich.text import Text

from aura_cli.cli.ui.components.base import ComponentBase
from aura_cli.cli.ui.theme_manager import get_theme_manager


# Lazy import to avoid circular dependency
def _get_icon_set():
    """Return the appropriate icon set for the current terminal."""
    try:
        from aura_cli.cli.ui.core.icon_set import get_icon_set

        return get_icon_set()
    except ImportError:
        return None


@dataclass
class CodeBlockConfig:
    """Configuration for code block display."""

    line_numbers: bool = True
    word_wrap: bool = True
    max_lines: Optional[int] = None
    collapsible: bool = False
    collapsed: bool = False
    show_header: bool = True
    show_footer: bool = True
    highlight_lines: Optional[List[int]] = None


class CodeBlockEnhanced(ComponentBase):
    """
    Enhanced code block with IDE-like features.

    Features:
    - Syntax highlighting via Pygments
    - Line numbers with gutter
    - Copy action indicator
    - Collapsible sections for long code
    - Line highlighting
    - Language badge
    """

    LANGUAGE_ALIASES: ClassVar[dict] = {
        "py": "python",
        "js": "javascript",
        "ts": "typescript",
        "rb": "ruby",
        "sh": "bash",
        "yml": "yaml",
        "md": "markdown",
    }

    def __init__(
        self,
        code: str,
        language: str = "text",
        title: Optional[str] = None,
        config: Optional[CodeBlockConfig] = None,
    ):
        """Initialize the instance."""
        self.code = code
        self.language = self.LANGUAGE_ALIASES.get(language.lower(), language.lower())
        self.title = title
        self.config = config or CodeBlockConfig()

    def render(self, console_width: int = 80) -> RenderableType:
        """Render the code block."""
        theme = get_theme_manager()
        icons = _get_icon_set()

        if self.config.collapsible and self.config.collapsed:
            return self._render_collapsed(theme, icons)

        elements = []

        if self.config.show_header:
            elements.append(self._render_header(theme, icons))

        elements.append(self._render_code(theme, console_width))

        if self.config.show_footer:
            elements.append(self._render_footer(theme, icons))

        return Panel(
            Group(*elements),
            box=rich.box.SIMPLE,
            padding=(0, 0),
            style=f"on {theme.get_color('background')}",
        )

    def _render_collapsed(self, theme, icons) -> RenderableType:
        """Render collapsed state."""
        line_count = len(self.code.splitlines())

        header = Text()
        header.append(f"{icons.get('chevron_right')} ", style=theme.get_color("muted"))
        header.append(
            f"{self.language.upper()}", style=f"bold {theme.get_color('warning')}"
        )
        header.append(f" · {line_count} linhas", style="dim")

        if self.title:
            header.append(f" · {self.title}", style="dim italic")

        header.append(" (clique para expandir)", style="dim italic")

        return Panel(
            header,
            border_style=theme.get_color("muted"),
            padding=(0, 1),
        )

    def _render_header(self, theme, icons) -> RenderableType:
        """Render code block header."""
        header = Table.grid(expand=True)
        header.add_column(justify="left", ratio=1)
        header.add_column(justify="right")

        left = Text()
        left.append(f" {icons.get('code')} ", style=theme.get_color("warning"))
        left.append(
            f" {self.language.upper()} ",
            style=f"reverse bold {theme.get_color('warning')}",
        )

        if self.title:
            left.append(f" {self.title}", style="dim italic")

        right = Text()
        right.append(
            f"{icons.get('copy')} copy ", style=f"dim {theme.get_color('muted')}"
        )

        if self.config.collapsible:
            right.append(" │ ", style="dim")
            right.append(
                f"{icons.get('chevron_down')} collapse ",
                style=f"dim {theme.get_color('muted')}",
            )

        header.add_row(left, right)

        return Panel(
            header,
            box=rich.box.SIMPLE,
            padding=(0, 1),
            style=f"on {theme.get_color('surface')}",
        )

    def _render_code(self, theme, width: int) -> RenderableType:
        """Render syntax-highlighted code."""
        syntax_theme = theme.get_appearance_property("syntax_theme", "monokai")

        lines = self.code.splitlines()
        display_lines = lines

        if self.config.max_lines and len(lines) > self.config.max_lines:
            half = self.config.max_lines // 2
            display_lines = [
                *lines[:half],
                f"... ({len(lines) - self.config.max_lines} lines hidden) ...",
                *lines[-half:],
            ]
            display_code = "\n".join(display_lines)
        else:
            display_code = self.code

        syntax = Syntax(
            display_code,
            self.language,
            theme=syntax_theme,
            line_numbers=self.config.line_numbers,
            word_wrap=self.config.word_wrap,
            highlight_lines=set(self.config.highlight_lines or []),
        )

        return syntax

    def _render_footer(self, theme, icons) -> RenderableType:
        """Render code block footer."""
        lines = self.code.splitlines()
        chars = len(self.code)

        footer = Text()
        footer.append(
            f" {len(lines)} lines · {chars} chars ",
            style=f"dim {theme.get_color('muted')}",
        )

        return Panel(
            footer,
            box=rich.box.SIMPLE,
            padding=(0, 1),
            style=f"on {theme.get_color('surface')}",
        )

    @classmethod
    def from_markdown_fence(
        cls,
        content: str,
        language: str = "",
        config: Optional[CodeBlockConfig] = None,
    ) -> "CodeBlockEnhanced":
        """Create from markdown code fence."""
        return cls(
            code=content.strip(),
            language=language or "text",
            config=config,
        )

    @classmethod
    def detect_language(cls, code: str, filename: Optional[str] = None) -> str:
        """Attempt to detect code language."""
        if filename:
            ext_map = {
                ".py": "python",
                ".js": "javascript",
                ".ts": "typescript",
                ".jsx": "jsx",
                ".tsx": "tsx",
                ".rb": "ruby",
                ".go": "go",
                ".rs": "rust",
                ".java": "java",
                ".c": "c",
                ".cpp": "cpp",
                ".h": "c",
                ".hpp": "cpp",
                ".sh": "bash",
                ".bash": "bash",
                ".zsh": "zsh",
                ".json": "json",
                ".yaml": "yaml",
                ".yml": "yaml",
                ".toml": "toml",
                ".md": "markdown",
                ".sql": "sql",
                ".html": "html",
                ".css": "css",
                ".scss": "scss",
            }
            for ext, lang in ext_map.items():
                if filename.endswith(ext):
                    return lang

        indicators = {
            "python": ["def ", "import ", "class ", "if __name__"],
            "javascript": ["function ", "const ", "let ", "=>", "require("],
            "typescript": ["interface ", "type ", ": string", ": number"],
            "bash": ["#!/bin/bash", "#!/bin/sh", "echo ", "export "],
            "json": ["{", "[", '":'],
            "yaml": ["---", ": ", "- "],
            "sql": ["SELECT ", "INSERT ", "UPDATE ", "DELETE ", "CREATE "],
        }

        for lang, patterns in indicators.items():
            if any(pattern in code for pattern in patterns):
                return lang

        return "text"


def render_code(
    code: str,
    language: str = "text",
    title: Optional[str] = None,
    line_numbers: bool = True,
    max_lines: Optional[int] = None,
) -> RenderableType:
    """Convenience function to render code block."""
    config = CodeBlockConfig(
        line_numbers=line_numbers,
        max_lines=max_lines,
    )
    block = CodeBlockEnhanced(code, language, title, config)
    return block.render()
