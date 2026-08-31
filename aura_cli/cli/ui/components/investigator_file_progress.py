"""AuraInvestigatorFileProgress component — file processing progress display."""

from rich.console import RenderableType
from rich.text import Text

from aura_cli.cli.ui.components.base import ComponentBase
from aura_cli.cli.ui.constants import UIIcons, UIStyles


class AuraInvestigatorFileProgress(ComponentBase):
    """Display the current file processing progress."""

    def render(
        self,
        current_file: str,
        total: int,
        processed: int,
    ) -> RenderableType:
        """Render a rich visual progress bar for file processing."""
        from rich.panel import Panel
        from rich.progress import (
            BarColumn,
            Progress,
            SpinnerColumn,
            TextColumn,
            TimeElapsedColumn,
            TimeRemainingColumn,
        )

        percentage = (processed / total * 100) if total > 0 else 0

        # Progress bar profissional
        progress = Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TextColumn("({task.completed}/{task.total})"),
            TimeElapsedColumn(),
            TimeRemainingColumn(),
        )

        task = progress.add_task(f"Processando: {current_file[:40]}…", total=total)
        progress.update(task, completed=processed)

        # Info adicional
        info_text = Text()
        info_text.append(
            f"{UIIcons.FILE} {current_file}", style=f"{UIStyles.PRIMARY} bold"
        )
        info_text.append(
            f"\nProgresso: {processed}/{total} arquivos ({percentage:.1f}%)",
            style=UIStyles.MUTED,
        )

        from rich.console import Group

        return Panel(
            Group(progress, Text("\n"), info_text),
            title=f"[{UIStyles.TITLE}]Processamento de arquivos[/{UIStyles.TITLE}]",
            border_style=UIStyles.BORDER_PRIMARY,
            padding=(1, 2),
        )
