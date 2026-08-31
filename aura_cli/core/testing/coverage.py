"""Code coverage analysis for Aura CLI.

Provides test coverage analysis with detailed reports.
"""

from dataclasses import dataclass, field
import subprocess
from typing import Any, Dict, Optional

from rich.console import Console
from rich.table import Table

from aura_cli.core.logger import get_logger
from aura_cli.core.stats import get_stats

logger = get_logger(__name__)
console = Console()


@dataclass
class CoverageReport:
    """Coverage report (total_lines, covered_lines, coverage_pct, etc.)."""

    total_lines: int = 0
    covered_lines: int = 0
    coverage_percent: float = 0.0
    files: Dict[str, Dict[str, Any]] = field(default_factory=dict)


class CoverageAnalyzer:
    """Code coverage analyser with pytest-cov integration."""

    def __init__(self):
        """Initialise the coverage analyser."""
        self.stats = get_stats()

        logger.info("CoverageAnalyzer initialized")

    def analyze_coverage(
        self, source_path: str = ".", test_path: Optional[str] = None
    ) -> CoverageReport:
        """Analyse code coverage and return a CoverageReport."""
        from aura_cli.core.ui import display_tool_call

        display_tool_call("analyze_coverage", {"source_path": source_path})

        if self._check_coverage():
            return self._analyze_with_coverage(source_path, test_path)
        else:
            logger.warning("coverage.py não instalado, retornando relatório vazio")
            return CoverageReport()

    def _check_coverage(self) -> bool:
        """Return True if coverage.py is available."""
        import shutil

        return shutil.which("coverage") is not None

    def _analyze_with_coverage(
        self, source_path: str, test_path: Optional[str]
    ) -> CoverageReport:
        """Analyse coverage using coverage.py."""
        cmd = ["coverage", "run", "-m", "pytest"]
        if test_path:
            cmd.append(test_path)

        try:
            subprocess.run(cmd, capture_output=True, timeout=300)

            result = subprocess.run(
                ["coverage", "report", "--format=json"],
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode == 0:
                import json

                data = json.loads(result.stdout)

                report = CoverageReport()

                totals = data.get("totals", {})
                report.total_lines = totals.get("num_statements", 0)
                report.covered_lines = totals.get("covered_lines", 0)
                report.coverage_percent = totals.get("percent_covered", 0.0)

                files = data.get("files", {})
                for file_path, file_data in files.items():
                    report.files[file_path] = {
                        "total": file_data.get("num_statements", 0),
                        "covered": file_data.get("covered_lines", 0),
                        "percent": file_data.get("percent_covered", 0.0),
                    }

                logger.info(f"Cobertura analisada: {report.coverage_percent:.1f}%")

                return report

        except Exception as e:
            logger.error(f"Error analyzing coverage: {e}", exc_info=True)

        return CoverageReport()

    def display_report(self, report: CoverageReport) -> None:
        """Display a coverage report to the console."""
        from aura_cli.core.ui_bridge import UIStyles

        table = Table(title="Coverage Report", show_header=True)
        table.add_column("Metric", style=UIStyles.PRIMARY)
        table.add_column("Value", style=UIStyles.SECONDARY)

        table.add_row("Total Lines", str(report.total_lines))
        table.add_row("Covered Lines", str(report.covered_lines))

        coverage_style = (
            UIStyles.SUCCESS if report.coverage_percent >= 80 else UIStyles.WARNING
        )
        table.add_row(
            "Coverage",
            f"[{coverage_style}]{report.coverage_percent:.1f}%[/{coverage_style}]",
        )

        console.print(table)

        if report.files:
            file_table = Table(title="Files Coverage", show_header=True)
            file_table.add_column("File", style=UIStyles.PRIMARY)
            file_table.add_column("Coverage", style=UIStyles.SECONDARY)

            sorted_files = sorted(report.files.items(), key=lambda x: x[1]["percent"])[
                :10
            ]

            for file_path, file_data in sorted_files:
                percent = file_data["percent"]
                style = (
                    UIStyles.SUCCESS
                    if percent >= 80
                    else UIStyles.WARNING
                    if percent >= 50
                    else UIStyles.ERROR
                )
                file_table.add_row(file_path[:50], f"[{style}]{percent:.1f}%[/{style}]")

            console.print(file_table)

        self.stats.track_tool_usage("coverage_analyzer")
