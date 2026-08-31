"""Accessibility module — inclusive UI helpers for Aura CLI.

Provides WCAG 2.1 AA / Section 508 utilities: color contrast checking,
visible focus indicators, keyboard navigation helpers and alternative
text for visual elements. Optional audio feedback is also supported.
"""

from typing import Optional, Tuple

import rich
from rich.color import Color
from rich.console import Console, Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from aura_cli.cli.ui.constants import UIIcons, UIStyles
from aura_cli.cli.ui.display_facade import get_console
from aura_cli.cli.ui.layout_contract import layout_for_width
from aura_cli.cli.ui.theme_manager import get_theme_manager


class ColorContrast:
    """WCAG color contrast checker.

    Provides methods to check color contrast ratios and WCAG compliance
    for text and background color combinations.
    """

    @staticmethod
    def hex_to_rgb(hex_color: str) -> Tuple[int, int, int]:
        """Convert hex color to RGB tuple.

        Args:
            hex_color: Hex color string (e.g., "#FF0000")

        Returns:
            RGB tuple (r, g, b)
        """
        value = hex_color.strip()
        if not value.startswith("#"):
            truecolor = Color.parse(value).get_truecolor()
            return (truecolor.red, truecolor.green, truecolor.blue)

        value = value.lstrip("#")
        if len(value) != 6:
            raise ValueError(f"Expected a six-digit color, got {hex_color!r}")
        return (int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16))

    @staticmethod
    def relative_luminance(rgb: Tuple[int, int, int]) -> float:
        """Calculate relative luminance of a colour."""
        r, g, b = [x / 255.0 for x in rgb]

        def adjust(c):
            """Adjust value."""
            return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

        r, g, b = adjust(r), adjust(g), adjust(b)
        return 0.2126 * r + 0.7152 * g + 0.0722 * b

    @staticmethod
    def contrast_ratio(color1: str, color2: str) -> float:
        """Calculate contrast ratio between two colours."""
        try:
            rgb1 = ColorContrast.hex_to_rgb(color1)
            rgb2 = ColorContrast.hex_to_rgb(color2)

            l1 = ColorContrast.relative_luminance(rgb1)
            l2 = ColorContrast.relative_luminance(rgb2)

            lighter = max(l1, l2)
            darker = min(l1, l2)

            return (lighter + 0.05) / (darker + 0.05)
        except Exception:
            return 0.0

    @staticmethod
    def meets_wcag_aa(color1: str, color2: str, large_text: bool = False) -> bool:
        """Return True if contrast meets WCAG AA."""
        ratio = ColorContrast.contrast_ratio(color1, color2)
        required = 3.0 if large_text else 4.5
        return ratio >= required

    @staticmethod
    def meets_wcag_aaa(color1: str, color2: str, large_text: bool = False) -> bool:
        """Return True if contrast meets WCAG AAA."""
        ratio = ColorContrast.contrast_ratio(color1, color2)
        required = 4.5 if large_text else 7.0
        return ratio >= required


class FocusIndicator:
    """Professional focus indicator manager."""

    def __init__(self, console: Optional[Console] = None):
        """Initialize the instance."""
        self.console = console if console is not None else get_console()
        self.focused_element: str | None = None

    def show_focus(
        self, element_id: str, text: str, style: str = "bold yellow on blue"
    ):
        """Display a professional focus indicator."""
        self.focused_element = element_id

        # Criar indicador visual rico
        focused_text = Text()
        focused_text.append("► ", style="bold bright_yellow")
        focused_text.append(text, style="bold white")
        focused_text.append(" ◀", style="bold bright_yellow")

        focus_panel = Panel(
            focused_text,
            border_style="bright_yellow",
            box=rich.box.DOUBLE,
            padding=(0, 1),
        )
        self.console.print(focus_panel)

    def clear_focus(self):
        """Clear the focus indicator."""
        self.focused_element = None

    def is_focused(self, element_id: str) -> bool:
        """Return True if an element has focus."""
        return self.focused_element == element_id


class KeyboardNavigation:
    """Keyboard navigation manager."""

    def __init__(self):
        """Initialize the instance."""
        self.focusable_elements = []
        self.current_index = 0

    def register_element(self, element_id: str, callback):
        """Register a navigable element."""
        self.focusable_elements.append({"id": element_id, "callback": callback})

    def next_element(self):
        """Move focus to the next element."""
        if self.focusable_elements:
            self.current_index = (self.current_index + 1) % len(self.focusable_elements)
            return self.focusable_elements[self.current_index]
        return None

    def previous_element(self):
        """Move focus to the previous element."""
        if self.focusable_elements:
            self.current_index = (self.current_index - 1) % len(self.focusable_elements)
            return self.focusable_elements[self.current_index]
        return None

    def activate_current(self):
        """Ativa elemento atual."""
        if self.focusable_elements and 0 <= self.current_index < len(
            self.focusable_elements
        ):
            element = self.focusable_elements[self.current_index]
            if element["callback"]:
                element["callback"]()


class AlternativeText:
    """Alternative text manager."""

    @staticmethod
    def add_alt_text(visual_element: str, alt_text: str) -> str:
        """Adiciona texto alternativo a elemento visual."""
        return f"{visual_element} [{alt_text}]"

    @staticmethod
    def describe_icon(icon: str) -> str:
        """Return a text description for an icon."""
        descriptions = {
            "+": "sucesso",
            "x": "erro",
            "!": "aviso",
            "i": "informação",
            "*": "ativo",
            "o": "inativo",
            "...": "carregando",
            "[T]": "ferramenta",
            "[F]": "arquivo",
            "[D]": "diretório",
            ">": "executar",
            "?": "buscar",
            UIIcons.SUCCESS: "sucesso",
            UIIcons.ERROR: "erro",
            UIIcons.WARNING: "aviso",
            UIIcons.INFO: "informação",
            UIIcons.LOADING: "carregando",
            UIIcons.TOOL: "ferramenta",
            UIIcons.FILE: "arquivo",
            UIIcons.DIR: "diretório",
            UIIcons.RUN: "executar",
            UIIcons.SEARCH: "buscar",
            UIIcons.CANCEL: "cancelled",
        }
        return descriptions.get(icon, icon)

    @staticmethod
    def describe_color(color: str) -> str:
        """Return a text description for a colour."""
        theme = get_theme_manager()
        descriptions = {
            theme.get_color("success"): "verde (sucesso)",
            theme.get_color("error"): "vermelho (erro)",
            theme.get_color("warning"): "amarelo (aviso)",
            theme.get_color("info"): "azul (informação)",
            theme.get_color("primary"): "ciano (ação)",
        }
        return descriptions.get(color.lower(), color)


class AccessibilityChecker:
    """Verificador de acessibilidade."""

    def __init__(self):
        """Initialize the instance."""
        self.issues = []

    def check_contrast(
        self, foreground: str, background: str, text_size: str = "normal"
    ) -> bool:
        """Check colour contrast for an element."""
        large_text = text_size in ["large", "heading", "title"]

        if not ColorContrast.meets_wcag_aa(foreground, background, large_text):
            self.issues.append(
                {
                    "type": "contrast",
                    "severity": "error",
                    "message": f"Contraste insuficiente entre {foreground} e {background}",
                }
            )
            return False
        return True

    def check_focus_indicator(self, has_focus_indicator: bool) -> bool:
        """Check for visible focus indicator."""
        if not has_focus_indicator:
            self.issues.append(
                {
                    "type": "focus",
                    "severity": "warning",
                    "message": "Elemento sem indicador de foco",
                }
            )
            return False
        return True

    def check_alt_text(self, has_alt_text: bool, element_type: str) -> bool:
        """Check for alternative text."""
        if not has_alt_text and element_type in ["icon", "image", "visual"]:
            self.issues.append(
                {
                    "type": "alt_text",
                    "severity": "warning",
                    "message": f"Elemento {element_type} sem texto alternativo",
                }
            )
            return False
        return True

    def check_keyboard_navigation(self, is_keyboard_accessible: bool) -> bool:
        """Check keyboard navigation accessibility."""
        if not is_keyboard_accessible:
            self.issues.append(
                {
                    "type": "keyboard",
                    "severity": "error",
                    "message": "Elemento não acessível por teclado",
                }
            )
            return False
        return True

    def get_report(self) -> dict:
        """Return the accessibility report."""
        errors = [i for i in self.issues if i["severity"] == "error"]
        warnings = [i for i in self.issues if i["severity"] == "warning"]

        return {
            "total_issues": len(self.issues),
            "errors": len(errors),
            "warnings": len(warnings),
            "issues": self.issues,
            "passed": len(errors) == 0,
        }

    def render_report(self, console: Optional[Console] = None) -> Panel:
        """Render the accessibility report as a Rich renderable."""
        output_console = console if console is not None else get_console()
        metrics = layout_for_width(output_console.width)
        errors = [i for i in self.issues if i["severity"] == "error"]
        warnings = [i for i in self.issues if i["severity"] == "warning"]

        # Tabela de issues
        table = Table(
            title="Relatório de acessibilidade",
            show_header=True,
            header_style=UIStyles.SUBTITLE,
            border_style=UIStyles.BORDER_WARNING
            if warnings
            else UIStyles.BORDER_ERROR
            if errors
            else UIStyles.BORDER_SUCCESS,
        )
        table.add_column("Tipo", width=12)
        table.add_column("Gravidade", width=10)
        table.add_column("Mensagem", width=50)

        for issue in self.issues:
            severity_style = (
                UIStyles.ERROR if issue["severity"] == "error" else UIStyles.WARNING
            )
            table.add_row(
                issue["type"],
                f"[{severity_style}]{issue['severity']}[/]",
                issue["message"],
            )

        # Resumo
        summary_text = Text()
        if len(errors) == 0 and len(warnings) == 0:
            summary_text.append("✓ ", style=UIStyles.SUCCESS)
            summary_text.append(
                "Todas as verificações de acessibilidade passaram!",
                style=UIStyles.SUCCESS,
            )
        else:
            if errors:
                summary_text.append(
                    f"{UIIcons.ERROR} {len(errors)} erros ", style=UIStyles.ERROR
                )
            if warnings:
                summary_text.append(
                    f"{UIIcons.WARNING} {len(warnings)} avisos", style=UIStyles.WARNING
                )

        return Panel(
            Group(table, summary_text),
            title="[bold cyan]Verificação de acessibilidade[/bold cyan]",
            border_style=UIStyles.BORDER_ERROR
            if errors
            else UIStyles.BORDER_WARNING
            if warnings
            else UIStyles.BORDER_SUCCESS,
            padding=metrics.group_padding,
        )


def check_color_contrast(fg: str, bg: str) -> bool:
    """Check colour contrast between two colours."""
    return ColorContrast.meets_wcag_aa(fg, bg)


def create_accessible_text(text: str, icon: Optional[str] = None) -> str:
    """Create accessible text with ARIA-like attributes."""
    if icon:
        alt = AlternativeText.describe_icon(icon)
        return f"{icon} {text} [{alt}]"
    return text


def get_focus_style() -> str:
    """Return the focus style for a given context."""
    return "bold yellow on blue"
