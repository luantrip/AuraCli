"""Enhanced Code Analysis Panel for Aura TUI.

Interactive code analysis viewer with syntax highlighting and issue navigation.
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from rich.syntax import Syntax as RichSyntax
from textual.containers import ScrollableContainer, Vertical
from textual.reactive import reactive
from textual.widgets import DataTable, Static


@dataclass
class CodeIssue:
    """Represents a code analysis issue."""

    file: str
    line: int
    column: int
    severity: str
    message: str
    rule: str = ""

    @property
    def severity_icon(self) -> str:
        """Return an icon character for the issue severity."""
        icons = {
            "error": "✖",
            "warning": "⚠",
            "info": "ℹ",
            "hint": "💡",
        }
        return icons.get(self.severity, "●")


class CodeAnalysisPanel(Vertical):
    """Widget to display code and AI-driven analysis results.

    Features:
    - Syntax-highlighted code viewer
    - DataTable for structured issue display
    - Issue severity filtering
    - Line highlighting for issues
    """

    current_file: reactive[str] = reactive("")
    issue_count: reactive[int] = reactive(0)

    def __init__(self, **kwargs):
        """Initialize the instance."""
        super().__init__(**kwargs)
        self.issues: List[CodeIssue] = []
        self.code_content: str = ""
        self.language: str = "python"

    def compose(self):
        """Compose code analysis panel structure."""
        yield Static(
            "◆ Análise de código", classes="panel-header", id="analysis_header"
        )

        with ScrollableContainer(id="code_viewer_container"):
            yield Static("", id="code_viewer")
            yield Static(
                "No code loaded. Select a file to start analysis.",
                id="code-empty-state",
                classes="empty-state",
            )

        yield Static("◆ Problemas (0)", id="issues_header", classes="panel-header")
        yield DataTable(id="issues_table", zebra_stripes=True, cursor_type="row")
        yield Static(
            "Nenhum problema encontrado.",
            id="issues-empty-state",
            classes="empty-state",
        )

        with ScrollableContainer(id="analysis_summary_container"):
            yield Static(
                "Nenhum resumo disponível ainda.",
                id="analysis_summary",
                classes="analysis-content",
            )

    def on_mount(self) -> None:
        """Initialize the issues table."""
        table = self.query_one("#issues_table", DataTable)
        table.add_columns("", "Linha", "Severidade", "Mensagem", "Regra")
        self._sync_empty_states()

    def update_code(
        self,
        code_content: str,
        language: str = "python",
        highlights: Optional[List[tuple]] = None,
        file_path: str = "",
    ) -> None:
        """Update the code viewer with new content and syntax highlighting.

        Args:
            code_content: The code to display
            language: Programming language for syntax highlighting
            highlights: List of (line_number, style) tuples for highlighting specific lines
            file_path: Path to the file being displayed
        """
        self.code_content = code_content
        self.language = language
        self.current_file = file_path

        header = self.query_one("#analysis_header", Static)
        if file_path:
            header.update(f"◆ Análise de código: {file_path}")

        # Build highlight_lines set from highlights parameter
        highlight_lines = None
        if highlights:
            highlight_lines = {line_num for line_num, _ in highlights}

        syntax_widget = self.query_one("#code_viewer", Static)
        syntax = RichSyntax(
            code_content,
            language,
            theme="monokai",
            word_wrap=True,
            highlight_lines=highlight_lines,
        )
        syntax_widget.update(syntax)
        self._sync_empty_states()

    def update_issues(self, issues: List[CodeIssue]) -> None:
        """Update the issues table with analysis results.

        Args:
            issues: List of CodeIssue objects
        """
        self.issues = issues
        self.issue_count = len(issues)

        issues_header = self.query_one("#issues_header", Static)
        issues_header.update(f"◆ Problemas ({len(issues)})")

        table = self.query_one("#issues_table", DataTable)
        table.clear()

        for issue in issues:
            table.add_row(
                issue.severity_icon,
                str(issue.line),
                self._severity_label(issue.severity).upper(),
                issue.message[:60] + "..."
                if len(issue.message) > 60
                else issue.message,
                issue.rule,
                key=f"{issue.file}:{issue.line}",
            )

        self._sync_empty_states()

    @staticmethod
    def _severity_label(severity: str) -> str:
        """Return a Portuguese presentation label without changing the value."""
        return {
            "error": "erro",
            "warning": "aviso",
            "info": "informação",
            "hint": "dica",
        }.get(severity, severity)

    def _sync_empty_states(self) -> None:
        """Keep code, issues, and summary empty-state copy coherent."""
        self.query_one("#code-empty-state", Static).display = not bool(
            self.code_content
        )
        self.query_one("#issues-empty-state", Static).display = not bool(self.issues)

    def update_analysis_results(self, results: Dict[str, Any]) -> None:
        """Update the analysis results panel with structured data.

        Args:
            results: Dictionary with "issues", "suggestions", "summary" keys
        """
        if "issues" in results and isinstance(results["issues"], list):
            code_issues = []
            for issue_data in results["issues"]:
                if isinstance(issue_data, dict):
                    code_issues.append(
                        CodeIssue(
                            file=issue_data.get("file", ""),
                            line=issue_data.get("line", 1),
                            column=issue_data.get("column", 1),
                            severity=issue_data.get("severity", "info"),
                            message=issue_data.get("message", ""),
                            rule=issue_data.get("rule", ""),
                        )
                    )
            self.update_issues(code_issues)

        if "summary" in results:
            summary = self.query_one("#analysis_summary", Static)
            summary.update(str(results["summary"]))
