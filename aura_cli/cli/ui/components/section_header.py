"""AuraSectionHeader - Unified section divider component.

Provides consistent section headers with optional metadata across all UI components.
Standardizes the visual pattern: ─── TITLE · METADATA

Features:
    - Consistent 3-dash prefix (─── )
    - Optional metadata separated inline, without brackets
    - Theme-aware styling
    - Minimal, professional design

Usage:
    >>> from aura_cli.cli.ui.components.section_header import AuraSectionHeader
    >>> header = AuraSectionHeader()
    >>> rendered = header.render("Output", metadata="12 lines")
"""

from typing import Optional

from rich.text import Text

from aura_cli.cli.ui.components.base import ComponentBase
from aura_cli.cli.ui.constants import UILayout, UIStyles


class AuraSectionHeader(ComponentBase):
    """Unified section header component.

    Creates consistent section dividers with optional metadata.
    Standard format: ─── TITLE · METADATA
    """

    def render(
        self,
        title: str,
        metadata: Optional[str] = None,
        style: Optional[str] = None,
    ) -> Text:
        """Render section header.

        Args:
            title: Section title
            metadata: Optional metadata displayed inline without brackets
            style: Optional style override (defaults to UIStyles.LABEL)

        Returns:
            Formatted Text object
        """
        header = Text()

        # Prefix (3 dashes)
        prefix_style = style or UIStyles.MUTED
        header.append(f"{UILayout.HORIZONTAL * 3} ", style=prefix_style)

        # Title
        title_style = style or UIStyles.LABEL
        header.append(title, style=title_style)

        # Metadata (optional)
        if metadata:
            metadata_style = style or UIStyles.MUTED
            header.append(
                f" {UILayout.METADATA_SEPARATOR} {metadata}", style=metadata_style
            )

        return header
