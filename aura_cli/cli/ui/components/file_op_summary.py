"""
FileOperationSummary Component for Aura CLI.

This module defines `FileOperationSummary` class, a reusable UI component
that adheres to `ComponentBase` protocol. Its responsibility is to create
visual summary of file operations (read, create, edit) performed during
an interaction.

The component is "dumb" and only renders data it receives, returning
Rich-renderable object without printing directly to console.

Features:
    - Operation Summary: Visual summary of file operations
    - Categorized Display: Separate sections for read/create/edit
    - Icon Support: Icons for each operation type
    - Empty State: Returns empty Group if no operations

Usage:
    >>> from aura_cli.cli.ui.components.file_op_summary import FileOperationSummary
    >>> summary = FileOperationSummary()
    >>> rendered = summary.render(files_edited=["main.py"], files_created=["test.py"], files_read=["config.py"])
"""

import os
from typing import Any, Dict, List

from rich.columns import Columns
from rich.console import Group
from rich.text import Text

from aura_cli.cli.ui.components.base import ComponentBase
from aura_cli.cli.ui.constants import UIIcons, UIStyles


class FileOperationSummary(ComponentBase):
    """
    UI component that renders file operations summary.

    Displays categorized list of file operations with icons.

    Example:
        >>> summary = FileOperationSummary()
        >>> group = summary.render(
        ...     files_edited=["main.py", "utils.py"],
        ...     files_created=["test.py"],
        ...     files_read=["config.json"]
        ... )
    """

    def _get_file_stats(self, file_path: str) -> Dict[str, Any]:
        """Get file statistics."""
        stats = {"exists": False, "size": 0, "lines": 0}
        try:
            if os.path.exists(file_path):
                stats["exists"] = True
                stats["size"] = os.path.getsize(file_path)
                try:
                    with open(file_path, encoding="utf-8") as f:
                        stats["lines"] = len(f.readlines())
                except (OSError, UnicodeDecodeError) as _e:
                    pass  # silenced: {_e}
                except Exception as e:
                    import logging

                    logger = logging.getLogger(__name__)
                    logger.debug(f"Unexpected error reading file stats: {e}")
        except OSError as e:
            import logging

            logger = logging.getLogger(__name__)
            logger.debug(f"Error getting file stats: {e}")
        except Exception as e:
            import logging

            logger = logging.getLogger(__name__)
            logger.debug(f"Unexpected error in get_file_stats: {e}")
        return stats

    def render(
        self,
        files_edited: List[str],
        files_created: List[str],
        files_read: List[str],
        *args,
        **kwargs,
    ) -> Group:
        """
        Render file operations summary as Rich Group with professional cards.

        Args:
            files_edited: List of edited file paths
            files_created: List of created file paths
            files_read: List of read file paths

        Returns:
            Rich Group containing summary panel, or empty Group if no operations
        """
        operations = []
        if files_read:
            operations.append(
                f"{UIIcons.FILE} Lidos {len(files_read)} arquivo{'s' if len(files_read) > 1 else ''}"
            )
        if files_created:
            operations.append(
                f"{UIIcons.CREATE} Criados {len(files_created)} arquivo{'s' if len(files_created) > 1 else ''}"
            )
        if files_edited:
            operations.append(
                f"{UIIcons.EDIT} Editados {len(files_edited)} arquivo{'s' if len(files_edited) > 1 else ''}"
            )

        if not operations:
            return Group()

        total_files = len(files_read) + len(files_created) + len(files_edited)
        # Compact one-liner when many operations to avoid clutter
        COMPACT_THRESHOLD = 12
        if total_files > COMPACT_THRESHOLD:
            stats_text = Text()
            stats_text.append(f"{UIIcons.STATS} ", style=UIStyles.INFO)
            stats_text.append(
                f"Total: {total_files} operações (Lidos: {len(files_read)}, Criados: {len(files_created)}, Editados: {len(files_edited)})",
                style=UIStyles.PRIMARY,
            )
            return Group(Text(), stats_text)

        header = " ".join(operations)

        # Cards profissionais por tipo
        cards = []

        # Card de Read
        if files_read:
            read_card = self._create_operation_card(
                "Lidos", files_read, UIIcons.FILE, UIStyles.INFO
            )
            cards.append(read_card)

        # Card de Created
        if files_created:
            created_card = self._create_operation_card(
                "Criados", files_created, UIIcons.CREATE, UIStyles.SUCCESS
            )
            cards.append(created_card)

        # Card de Edited
        if files_edited:
            edited_card = self._create_operation_card(
                "Editados", files_edited, UIIcons.EDIT, UIStyles.WARNING
            )
            cards.append(edited_card)

        # Aggregated statistics
        total_files = len(files_read) + len(files_created) + len(files_edited)
        stats_text = Text()
        stats_text.append(f"{UIIcons.STATS} ", style=UIStyles.INFO)
        stats_text.append(f"Total: {total_files} operações", style=UIStyles.PRIMARY)

        body = (
            Columns(cards, equal=True, expand=True)
            if len(cards) > 1
            else (cards[0] if cards else Text())
        )

        header_text = Text(
            f"{UIIcons.FILE} {header}",
            style=f"bold {UIStyles.PRIMARY}",
        )
        return Group(header_text, body, stats_text)

    def _create_operation_card(
        self, operation_type: str, files: List[str], icon: str, style: str
    ) -> Text:
        """Create a professional text block for an operation type."""
        text = Text()
        text.append(f"{icon} {operation_type}: {len(files)}\n\n", style=style + " bold")

        for file_path in files[:5]:  # Maximum 5 per card
            stats = self._get_file_stats(file_path)
            file_name = os.path.basename(file_path)

            text.append(f"  {UIIcons.BULLET} ", style=UIStyles.MUTED)
            text.append(file_name, style=UIStyles.PRIMARY)

            if stats["exists"]:
                size_kb = stats["size"] / 1024
                text.append(f" ({size_kb:.1f} KB", style=UIStyles.MUTED)
                if stats["lines"] > 0:
                    text.append(f", {stats['lines']} linhas", style=UIStyles.MUTED)
                text.append(")", style=UIStyles.MUTED)

            text.append("\n")

        if len(files) > 5:
            text.append(f"  ... +{len(files) - 5} arquivos\n", style=UIStyles.MUTED)

        return text
