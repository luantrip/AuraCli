"""IDE-like Features Panel for Aura TUI.

Comprehensive IDE-grade functionality panel with file browsing and code tools.

Features:
- Project file browser with tree view
- Code issues display with navigation
- Refactoring operations interface
- Quick actions and commands
- Linting/error highlighting
- Contextual help and documentation
- DirectoryTree integration

Components:
- File browser with filtering
- Issues panel with severity
- Refactoring tools
- Quick actions menu
"""

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Dict, List

from textual.app import ComposeResult
from textual.containers import Horizontal, VerticalScroll
from textual.message import Message
from textual.reactive import reactive
from textual.widgets import (
    Button,
    DataTable,
    DirectoryTree,
    Static,
    TabbedContent,
    TabPane,
)


class IssueSeverity(Enum):
    """Code issue severity."""

    ERROR = "error"
    WARNING = "warning"
    INFO = "info"
    HINT = "hint"


@dataclass
class CodeIssue:
    """A code issue (lint error, type error, etc.)."""

    file_path: str
    line: int
    column: int
    message: str
    severity: IssueSeverity
    rule: str = ""
    source: str = "linter"

    @property
    def location(self) -> str:
        """Return the current cursor location."""
        return f"{self.file_path}:{self.line}:{self.column}"


@dataclass
class RefactoringAction:
    """A refactoring action."""

    id: str
    name: str
    description: str
    category: str  # rename, extract, inline, move
    requires_selection: bool = False
    parameters: Dict[str, str] = field(default_factory=dict)


class FileTreePanel(Static):
    """
    File tree navigation panel.

    Features:
    - Directory tree view
    - Quick navigation
    - File operations
    """

    class FileSelected(Message):
        """Emitted when file is selected."""

        def __init__(self, path: str):
            """Initialize the instance."""
            super().__init__()
            self.path = path

    def __init__(self, root_path: str = ".", **kwargs):
        """Initialize the instance."""
        super().__init__(**kwargs)
        self.root_path = Path(root_path).resolve()

    def compose(self) -> ComposeResult:
        """Compose the widget layout."""
        yield Static(f"▷ {self.root_path.name}", classes="tree-header")
        yield DirectoryTree(str(self.root_path), id="file_tree", classes="file-tree")

    def on_directory_tree_file_selected(
        self, event: DirectoryTree.FileSelected
    ) -> None:
        """Handle file selection."""
        self.post_message(self.FileSelected(str(event.path)))

    def refresh_tree(self) -> None:
        """Refresh the file tree."""
        tree = self.query_one("#file_tree", DirectoryTree)
        tree.reload()


class IssuesPanel(Static):
    """
    Code issues panel (linting, errors).

    Features:
    - Issue listing by severity
    - File grouping
    - Quick navigation to issue
    - Issue filtering
    """

    class IssueSelected(Message):
        """Emitted when issue is selected."""

        def __init__(self, issue: CodeIssue):
            """Initialize the instance."""
            super().__init__()
            self.issue = issue

    def __init__(self, **kwargs):
        """Initialize the instance."""
        super().__init__(**kwargs)
        self.issues: List[CodeIssue] = []

    def compose(self) -> ComposeResult:
        """Compose the widget layout."""
        with Horizontal(classes="issues-header"):
            yield Static("⚠️ Problems", classes="pane-header")
            yield Static(
                "0 errors, 0 warnings", id="issues_summary", classes="issues-summary"
            )
        yield DataTable(id="issues_table", zebra_stripes=True, classes="issues-table")

    def on_mount(self) -> None:
        """Setup table on mount."""
        table = self.query_one("#issues_table", DataTable)
        table.add_columns("", "File", "Line", "Message", "Rule")
        table.cursor_type = "row"

    def set_issues(self, issues: List[CodeIssue]) -> None:
        """Set issues to display."""
        self.issues = issues
        self._update_table()
        self._update_summary()

    def _update_table(self) -> None:
        """Update issues table."""
        table = self.query_one("#issues_table", DataTable)
        table.clear()

        for i, issue in enumerate(self.issues):
            icon = self._get_severity_icon(issue.severity)
            file_name = Path(issue.file_path).name

            table.add_row(
                icon,
                file_name,
                str(issue.line),
                (
                    issue.message[:50] + "..."
                    if len(issue.message) > 50
                    else issue.message
                ),
                issue.rule,
                key=str(i),
            )

    def _get_severity_icon(self, severity: IssueSeverity) -> str:
        """Get severity icon."""
        icons = {
            IssueSeverity.ERROR: "✖",
            IssueSeverity.WARNING: "⚠",
            IssueSeverity.INFO: "ℹ",
            IssueSeverity.HINT: "💡",
        }
        return icons.get(severity, "•")

    def _update_summary(self) -> None:
        """Update summary."""
        errors = sum(1 for i in self.issues if i.severity == IssueSeverity.ERROR)
        warnings = sum(1 for i in self.issues if i.severity == IssueSeverity.WARNING)

        summary = self.query_one("#issues_summary", Static)
        summary.update(f"{errors} errors, {warnings} warnings")

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Handle issue selection."""
        idx = int(event.row_key.value or 0)
        if 0 <= idx < len(self.issues):
            self.post_message(self.IssueSelected(self.issues[idx]))

    def add_issue(self, issue: CodeIssue) -> None:
        """Add a single issue."""
        self.issues.append(issue)
        self._update_table()
        self._update_summary()

    def clear_issues(self) -> None:
        """Clear all issues."""
        self.issues = []
        self._update_table()
        self._update_summary()


class RefactoringPanel(Static):
    """
    Refactoring tools panel.

    Features:
    - Available refactorings list
    - Refactoring preview
    - Apply/cancel actions
    - History of refactorings
    """

    class RefactoringRequested(Message):
        """Emitted when refactoring is requested."""

        def __init__(self, action: RefactoringAction, params: Dict[str, str]):
            """Initialize the instance."""
            super().__init__()
            self.action = action
            self.params = params

    selected_refactoring = reactive("")

    def __init__(self, refactorings: List[RefactoringAction] | None = None, **kwargs):
        """Initialize the instance."""
        super().__init__(**kwargs)
        self.all_refactorings = refactorings or []
        self.refactorings = {r.id: r for r in self.all_refactorings}

    def compose(self) -> ComposeResult:
        """Compose the widget layout."""
        yield Static("⚒ Refactoring Tools", classes="refactor-header")
        yield DataTable(id="refactor_list", zebra_stripes=True, classes="refactor-list")
        yield VerticalScroll(id="refactor_preview", classes="refactor-preview")

        with Horizontal(classes="refactor-actions"):
            yield Button("▶ Apply", id="apply_btn", variant="primary", disabled=True)
            yield Button("◎ Preview", id="preview_btn", disabled=True)
            yield Button("✖ Cancel", id="cancel_btn")

    def on_mount(self) -> None:
        """Setup on mount."""
        table = self.query_one("#refactor_list", DataTable)
        table.add_columns("", "Refactoring", "Category")
        table.cursor_type = "row"

        self._load_refactorings()

    def _load_refactorings(self) -> None:
        """Load refactorings into table."""
        table = self.query_one("#refactor_list", DataTable)
        table.clear()

        for refactor in self.all_refactorings:
            icon = self._get_category_icon(refactor.category)
            table.add_row(
                icon,
                refactor.name,
                refactor.category,
                key=refactor.id,
            )

    def _get_category_icon(self, category: str) -> str:
        """Get category icon."""
        icons = {
            "rename": "✎",
            "extract": "↑",
            "inline": "📥",
            "move": "◇",
            "convert": "⟳",
            "enhance": "✨",
            "optimize": "▶",
        }
        return icons.get(category, "⚒")

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Handle refactoring selection."""
        self.selected_refactoring = event.row_key.value or ""
        self._show_refactoring_details()

        # Enable buttons
        apply_btn = self.query_one("#apply_btn", Button)
        preview_btn = self.query_one("#preview_btn", Button)
        apply_btn.disabled = False
        preview_btn.disabled = False

    def _write_log(self, message: str, log_class: str = "log-content") -> None:
        """Append a message to the log display."""
        log_container = self.query_one("#refactor_preview", VerticalScroll)
        log_entry = Static(message, classes=f"log-entry {log_class}")
        log_container.mount(log_entry)
        log_container.scroll_end()

    def _clear_log(self) -> None:
        """Clear the log display."""
        log_container = self.query_one("#refactor_preview", VerticalScroll)
        log_container.remove_children()

    def _show_refactoring_details(self) -> None:
        """Show details for the selected refactoring suggestion."""
        if not self.selected_refactoring:
            return

        refactor = self.refactorings.get(self.selected_refactoring)
        if not refactor:
            return

        self._clear_log()

        self._write_log(refactor.name, "log-label")
        self._write_log(refactor.description, "log-content")
        self._write_log("", "log-content")

        if refactor.requires_selection:
            self._write_log("⚠ Requires text selection", "log-warning")

        if refactor.parameters:
            self._write_log("", "log-content")
            self._write_log("Parameters:", "log-label")
            for param, ptype in refactor.parameters.items():
                self._write_log(f"  • {param}: {ptype}", "log-content")

        self._write_log("", "log-content")
        self._write_log(
            "Select a code element and click Apply to perform this refactoring.",
            "log-content",
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "apply_btn":
            self._apply_refactoring()
        elif event.button.id == "preview_btn":
            self._preview_refactoring()
        elif event.button.id == "cancel_btn":
            self._cancel()

    def _apply_refactoring(self) -> None:
        """Apply selected refactoring."""
        if not self.selected_refactoring:
            return

        refactor = self.refactorings.get(self.selected_refactoring)
        if not refactor:
            return

        # In a real implementation, would collect parameters and apply
        self.notify(f"Applying: {refactor.name}")
        self.post_message(self.RefactoringRequested(refactor, {}))

    def _preview_refactoring(self) -> None:
        """Preview the refactoring changes."""
        self._write_log("", "log-content")
        self._write_log("Preview:", "log-label")
        self._write_log("Changes would be shown here...", "log-content")

    def _cancel(self) -> None:
        """Cancel refactoring."""
        self.selected_refactoring = ""

        apply_btn = self.query_one("#apply_btn", Button)
        preview_btn = self.query_one("#preview_btn", Button)
        apply_btn.disabled = True
        preview_btn.disabled = True

        self._clear_log()


class IDEPanel(Static):
    """
    Combined IDE panel with file tree, issues, and refactoring.

    Provides a tabbed interface for IDE-like features.
    """

    def __init__(
        self,
        root_path: str = ".",
        refactorings: List[RefactoringAction] | None = None,
        **kwargs,
    ):
        """Initialize the instance."""
        super().__init__(**kwargs)
        self.root_path = root_path
        self.refactorings = refactorings or []

    def compose(self) -> ComposeResult:
        """Compose the widget layout."""
        with TabbedContent(id="ide_tabs"):
            with TabPane("▷ Files", id="files_tab"):
                yield FileTreePanel(root_path=self.root_path, id="file_tree_panel")

            with TabPane("⚠️ Problems", id="problems_tab"):
                yield IssuesPanel(id="issues_panel")

            with TabPane("⚒ Refactor", id="refactor_tab"):
                yield RefactoringPanel(
                    id="refactor_panel", refactorings=self.refactorings
                )

    def set_issues(self, issues: List[CodeIssue]) -> None:
        """Set issues to display."""
        panel = self.query_one("#issues_panel", IssuesPanel)
        panel.set_issues(issues)

    def add_issue(self, issue: CodeIssue) -> None:
        """Add a single issue."""
        panel = self.query_one("#issues_panel", IssuesPanel)
        panel.add_issue(issue)

    def clear_issues(self) -> None:
        """Clear all issues."""
        panel = self.query_one("#issues_panel", IssuesPanel)
        panel.clear_issues()

    def on_file_tree_panel_file_selected(
        self, event: FileTreePanel.FileSelected
    ) -> None:
        """Bubble up file selection."""
        # Can be handled by parent

    def on_issues_panel_issue_selected(self, event: IssuesPanel.IssueSelected) -> None:
        """Bubble up issue selection."""
        # Can be handled by parent

    def on_refactoring_panel_refactoring_requested(
        self, event: RefactoringPanel.RefactoringRequested
    ) -> None:
        """Bubble up refactoring request."""
        # Can be handled by parent
