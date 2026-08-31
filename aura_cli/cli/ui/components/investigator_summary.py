"""AuraInvestigatorSummary component — final analysis summary (Modernized Nebula)."""

from typing import Any, Dict

import rich.box as box
from rich.columns import Columns
from rich.console import Group, RenderableType
from rich.panel import Panel
from rich.text import Text

from aura_cli.cli.ui.components.base import ComponentBase
from aura_cli.cli.ui.components.lcd_display import AuraLCDDisplay
from aura_cli.cli.ui.constants import UIIcons, UIStyles


class AuraInvestigatorSummary(ComponentBase):
    """Render a codebase intelligence report in Nebula Assembly Dashboard style."""

    def render(
        self,
        analysis_results: Dict[str, Any],
    ) -> RenderableType:
        """Render the intelligence report."""
        # Data Extraction
        files_found = analysis_results.get("files_found", 0)
        files_processed = analysis_results.get("files_processed", 0)
        total_lines = analysis_results.get("total_lines", 0)
        duration = analysis_results.get("duration", 0)
        symbols = analysis_results.get("symbols", {})

        # 1. Stat Cards Profissionais (Horizontal)
        stats_panels = []
        metrics = [
            ("ARQUIVOS", str(files_found), UIIcons.FILE, UIStyles.PRIMARY),
            ("LINHAS", f"{total_lines:,}", UIIcons.STATS, UIStyles.INFO),
            (
                "CLASSES",
                str(symbols.get("classes", 0)),
                UIIcons.AGI,
                UIStyles.ACCENT,
            ),
            (
                "FUNCS",
                str(symbols.get("functions", 0)),
                UIIcons.TOOL,
                UIStyles.SUCCESS,
            ),
        ]

        for label, value, icon, color in metrics:
            content = Text(justify="center")
            content.append(f"{icon} ", style=color)
            content.append(f"{value}\n", style=f"bold {color}")
            content.append(label, style=UIStyles.MUTED)

            p = Panel(
                content,
                border_style=color,
                padding=(1, 2),
                expand=True,
                box=box.ROUNDED,
            )
            stats_panels.append(p)

        stats_row = Columns(stats_panels, expand=True)

        # 2. Insights & Trace (LCD) with rich visualisation
        insights_text = Text()
        insights_text.append(
            f"{UIIcons.SUCCESS} Analysis completed in {duration:.2f}s\n",
            style=f"{UIStyles.SUCCESS} bold",
        )
        insights_text.append(
            f"{UIIcons.WORKING} Processed {files_processed}/{files_found} files\n",
            style=UIStyles.INFO,
        )

        languages = analysis_results.get("languages", {})
        if languages:
            insights_text.append(
                f"{UIIcons.INFO} Linguagens detectadas:\n", style=UIStyles.TITLE
            )
            # Top 5 languages with percentage
            total_lang_files = sum(languages.values())
            for lang, count in sorted(
                languages.items(), key=lambda x: x[1], reverse=True
            )[:5]:
                percentage = (
                    (count / total_lang_files * 100) if total_lang_files > 0 else 0
                )
                insights_text.append(
                    f"  {UIIcons.BULLET} {lang}: {count} files ({percentage:.1f}%)\n",
                    style=UIStyles.MUTED,
                )

        # Breakdown by symbol type
        if symbols:
            insights_text.append(
                f"\n{UIIcons.STATS} Distribuição de símbolos:\n", style=UIStyles.TITLE
            )
            if symbols.get("classes", 0) > 0:
                insights_text.append(
                    f"  {UIIcons.AGI} Classes: {symbols.get('classes', 0)}\n",
                    style=UIStyles.ACCENT,
                )
            if symbols.get("functions", 0) > 0:
                insights_text.append(
                    f"  {UIIcons.TOOL} Funções: {symbols.get('functions', 0)}\n",
                    style=UIStyles.SUCCESS,
                )
            if symbols.get("variables", 0) > 0:
                insights_text.append(
                    f"  {UIIcons.INFO} Variáveis: {symbols.get('variables', 0)}\n",
                    style=UIStyles.INFO,
                )

        lcd = AuraLCDDisplay()
        trace_panel = lcd.render(
            content=insights_text,
            title="Rastreio da análise",
            line_numbers=True,
            variant="primary",
            metadata="VERIFIED",
        )

        header_text = Text()
        header_text.append(
            f" {UIIcons.SEARCH} ", style=f"bold {UIStyles.SECONDARY}"
        )
        header_text.append("Relatório de codebase", style=UIStyles.TITLE)

        return Panel(
            Group(stats_row, Text(" "), trace_panel),
            title=header_text,
            border_style=UIStyles.BORDER_SECONDARY,
            padding=(1, 2),
            box=box.ROUNDED,
        )
