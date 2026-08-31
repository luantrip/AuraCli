"""
AuraMarkdownDisplay component — Advanced Markdown renderer with LCD integration.

This component nte estende as capacapabilities of Rich Markdown rendering for:
1. Usar AuraLCDDisplay para all code blocks (Syntax Highlighting + Line Numbers + OSD).
2. Aplicar estilos do tema Nebufor headers, lists and citations.
3. Provide an IDE-Grade reading exptura "IDE-Grade".
"""

from typing import Optional, Union

from rich.console import (
    Console,
    ConsoleOptions,
    JustifyMethod,
    RenderableType,
    RenderResult,
)
from rich.markdown import CodeBlock, Markdown
from rich.style import Style

from aura_cli.cli.ui.components.lcd_display import AuraLCDDisplay
from aura_cli.cli.ui.theme_manager import get_theme_manager


class AuraCodeBlock(CodeBlock):
    """
    Custom CodeBlock renderer that uses AuraLCDDisplay.
    """

    def __rich_console__(
        self, console: Console, options: ConsoleOptions
    ) -> RenderResult:
        """Render the markdown content to a Rich console."""
        code = str(self.text).rstrip()
        lexer_name = self.lexer_name or "text"

        lcd = AuraLCDDisplay()

        variant = "primary"
        if lexer_name in ["bash", "sh", "shell"]:
            variant = "success"  # Terminal commands look 'active'
        elif lexer_name in ["json", "yaml", "toml"]:
            variant = "warning"  # Data formats

        yield lcd.render(
            content=code,
            title=lexer_name.upper(),
            format_type=lexer_name,
            line_numbers=True,
            max_height=None,  # Let code expand naturally in chat
            variant=variant,
            metadata=f"{len(code.splitlines())} lines",
        )


class AuraMarkdown(Markdown):
    """
    Custom Markdown parser/renderer for Aura CLI.
    Overrides specific elements to match the Nebula aesthetic with custom colors.
    """

    elements = Markdown.elements.copy()
    elements["fence"] = AuraCodeBlock
    elements["code_block"] = AuraCodeBlock

    def __init__(
        self,
        markup: str,
        code_theme: str = "monokai",
        justify: Optional[JustifyMethod] = None,
        style: Union[str, Style] = "none",
    ):
        """Initialize the instance."""
        get_theme_manager()
        super().__init__(
            markup,
            code_theme=code_theme,
            justify=justify or "left",
            style=style,
        )


class AuraMarkdownDisplay:
    """
    Wrapper component to easily render Aura-flavored Markdown.
    """

    def render(self, content: str) -> RenderableType:
        """
        Parses and returns a renderable AuraMarkdown object with enhanced styling.

        Pre-processes content to highlight code references, file paths, and function names.
        """
        if not content or not content.strip():
            from rich.text import Text

            return Text("")

        theme = get_theme_manager()
        syntax_theme = theme.get_appearance_property("syntax_theme", "monokai")
        processed_content = self._enhance_markdown_formatting(content)

        # Markdown will be rendered as-is - Rich Markdown handles all formats

        return AuraMarkdown(
            processed_content, code_theme=syntax_theme, justify="left", style="none"
        )

    def _process_table_line(
        self,
        line: str,
        i: int,
        lines: list,
        enhanced: list,
        prev_empty: bool,
        in_table: bool,
    ) -> tuple:
        """Handle a table line. Returns (prev_empty, in_table)."""
        if not in_table:
            in_table = True
            if i > 0 and not prev_empty:
                enhanced.append("")
        enhanced.append(line)
        if i + 1 < len(lines):
            next_line = lines[i + 1]
            if "|" not in next_line and not next_line.strip().startswith("|"):
                in_table = False
                if next_line.strip() and not next_line.startswith("#"):
                    enhanced.append("")
        return False, in_table

    def _process_line(
        self,
        line: str,
        i: int,
        lines: list,
        enhanced: list,
        prev_empty: bool,
        in_table: bool,
    ) -> tuple:
        """Process a single line. Returns (prev_empty, in_table, consumed)."""
        if "|" in line and not line.strip().startswith("```"):
            prev_empty, in_table = self._process_table_line(
                line, i, lines, enhanced, prev_empty, in_table
            )
            return prev_empty, in_table, True

        in_table = False
        if line.startswith("#"):
            if i > 0 and not prev_empty:
                enhanced.append("")
            enhanced.append(line)
            if (
                i + 1 < len(lines)
                and lines[i + 1].strip()
                and not lines[i + 1].startswith(("#", "|"))
            ):
                enhanced.append("")
            return False, in_table, True
        if self._is_list_start(line):
            if (
                i > 0
                and not prev_empty
                and not self._is_list_start(lines[i - 1])
                and "|" not in lines[i - 1]
            ):
                enhanced.append("")
            enhanced.append(line)
            return False, in_table, True
        if line.strip().startswith("```"):
            if i > 0 and not prev_empty:
                enhanced.append("")
            enhanced.append(line)
            return False, in_table, True
        if not line.strip():
            if not prev_empty:
                enhanced.append("")
            return True, in_table, True
        enhanced.append(line)
        return False, in_table, True

    def _is_list_start(self, line: str) -> bool:
        return line.strip().startswith(("-", "*", "•", "1.", "2.", "3.", "4.", "5."))

    def _enhance_markdown_formatting(self, content: str) -> str:
        """
        Enhance markdown formatting with better spacing and organization.

        - Ensures proper spacing between sections
        - Adds spacing after headers
        - Improves list formatting
        - Highlights code references and file paths
        - Preserves table formatting
        """
        if not content:
            return ""

        lines = content.split("\n")
        enhanced: list = []
        prev_line_empty = False
        in_table = False

        for i, line in enumerate(lines):
            prev_line_empty, in_table, _ = self._process_line(
                line, i, lines, enhanced, prev_line_empty, in_table
            )

        return "\n".join(enhanced)
