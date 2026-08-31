"""
AuraPanel - Clean, minimal panel component.

Provides a simple container with subtle styling options.
Supports borderless and bordered variants for different contexts.
"""

from typing import Any, Optional

import rich.box as box
from rich.console import Group, RenderableType
from rich.padding import Padding
from rich.panel import Panel
from rich.text import Text

from aura_cli.cli.ui.components.base import ComponentBase
from aura_cli.cli.ui.components.section_header import AuraSectionHeader
from aura_cli.cli.ui.layout_contract import layout_for_width
from aura_cli.cli.ui.theme_manager import get_theme_manager


class AuraPanel(ComponentBase):
    """
    Clean panel component with multiple style variants.

    Variants:
    - default: Subtle rounded border for isolated/critical content
    - open: No border, inline title and compact padding
    - minimal: No border, just padding
    - accent: Left accent line only
    - bordered: Full border with title support
    """

    def render(
        self,
        content: RenderableType,
        *,
        title: Optional[str] = None,
        variant: str = "default",
        status: Optional[str] = None,
        console_width: int = 80,
    ) -> RenderableType:
        """
        Render content in a styled container.

        Args:
            content: Content to display
            title: Optional title
            variant: Style variant (default, open, minimal, accent, bordered)
            status: Status for accent color (success, warning, error)

        Returns:
            Styled panel or group
        """
        theme = get_theme_manager()
        metrics = layout_for_width(console_width)

        accent_map = {
            "success": "border_success",
            "warning": "border_warning",
            "error": "border_error",
            "primary": "border_primary",
            None: "border_primary",
        }
        accent_style = theme.get_style(accent_map.get(status, "border_primary"))
        muted = theme.get_color("muted")

        if variant == "minimal":
            return Padding(content, metrics.chat_padding)

        elif variant == "open":
            open_parts: list[Any] = []
            if title:
                header = AuraSectionHeader().render(title)
                open_parts.append(header)
                open_parts.append(Text())
            open_parts.append(Padding(content, metrics.chat_padding))
            return Group(*open_parts)

        elif variant == "accent":
            parts: list[Any] = []

            if title:
                header = Text()
                header.append("│ ", style=accent_style)
                header.append(title, style=f"bold {accent_style}")
                parts.append(header)
                parts.append(Text())

            if isinstance(content, str):
                for line in content.split("\n"):
                    line_text = Text()
                    line_text.append("│ ", style=f"dim {accent_style}")
                    line_text.append(line, style=theme.get_style("body"))
                    parts.append(line_text)
            else:
                parts.append(Padding(content, (0, 0, 0, 2)))

            return Group(*parts)

        elif variant == "bordered":
            border_type_name = theme.get_appearance_property(
                "panel_border_type", "round"
            ).upper()
            border_box = getattr(box, border_type_name, box.ROUNDED)

            return Panel(
                content,
                title=f"[bold {accent_style}]{title}[/]" if title else None,
                border_style=f"dim {muted}",
                padding=metrics.focus_padding,
                box=border_box,
                expand=False,
            )

        else:
            return Panel(
                content,
                title=f"[bold {accent_style}]{title}[/]" if title else None,
                border_style=f"dim {muted}",
                padding=metrics.focus_padding,
                box=box.ROUNDED,
                expand=False,
                width=None,  # Let content determine width naturally
            )


class AuraSection(ComponentBase):
    """Section with header line, no border."""

    def render(
        self,
        content: RenderableType,
        title: str,
        icon: Optional[str] = None,
        console_width: int = 80,
    ) -> RenderableType:
        """
        Render section with header.

        Args:
            content: Section content
            title: Section title
            icon: Optional icon prefix

        Returns:
            Formatted section
        """
        theme = get_theme_manager()
        muted = theme.get_color("muted")
        metrics = layout_for_width(console_width)

        parts: list[Any] = []

        section_header = AuraSectionHeader()
        header_title = f"{icon} {title}" if icon else title
        header = section_header.render(header_title)
        header.append(" ", style=f"dim {muted}")

        parts.append(header)
        parts.append(Text())
        parts.append(Padding(content, metrics.chat_padding))

        return Group(*parts)


class AuraCard(ComponentBase):
    """Open card with a subtle title and no enclosing border."""

    def render(
        self,
        content: RenderableType,
        title: Optional[str] = None,
        console_width: int = 80,
    ) -> RenderableType:
        """
        Render card with subtle background.

        Args:
            content: Card content
            title: Optional title

        Returns:
            Formatted card
        """
        theme = get_theme_manager()
        metrics = layout_for_width(console_width)

        parts: list[Any] = []

        if title:
            header = Text()
            header.append(title, style=f"bold {theme.get_style('primary')}")
            parts.append(header)
            parts.append(Text())

        parts.append(content)

        content_group = Group(*parts)
        # Keep the surface tone without drawing a closed window around routine data.
        return Padding(content_group, metrics.focus_padding)
