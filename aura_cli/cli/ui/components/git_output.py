"""
UI Components for Git Output Display.

This module provides components for rich formatting of Git operation outputs,
separating presentation logic from tools layer.

Components:
    - GitStatusOutput: Formatted git status display
    - GitDiffOutput: Formatted git diff display
    - GitLogOutput: Formatted git log display

Usage:
    >>> from aura_cli.cli.ui.components.git_output import GitStatusOutput
    >>> status = GitStatusOutput()
    >>> rendered = status.render("main", status_lines)
"""

from typing import Dict, List, Optional

import rich.box as box
from rich.console import Group, RenderableType
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table
from rich.text import Text

from aura_cli.cli.ui.components.base import ComponentBase
from aura_cli.cli.ui.constants import UIIcons, UIStyles


class GitStatusOutput(ComponentBase):
    """
    Component for displaying formatted git status.

    Example:
        >>> status = GitStatusOutput()
        >>> table = status.render("main", ["M file.py", "A new.py"])
    """

    def __init__(self):
        """Initialize GitStatusOutput component."""
        super().__init__()

    def render(
        self, branch: str, status_lines: List[str], console_width: int = 80
    ) -> RenderableType:
        """
        Render git status as formatted table.

        Args:
            branch: Current branch name
            status_lines: Status lines (git status --short format)
            console_width: Console width

        Returns:
            Rich renderable

        Example:
            >>> rendered = status.render("main", ["M main.py"])
        """
        title_style = UIStyles.safe_style("TITLE", "cyan")
        subtitle_style = UIStyles.safe_style("SUBTITLE", "bold cyan")
        border_primary_style = UIStyles.safe_style("BORDER_PRIMARY", "cyan")
        table = Table(
            title=f"[{title_style}]Git Status - Branch: {branch}[/{title_style}]",
            show_header=True,
            header_style=subtitle_style,
            border_style=border_primary_style,
            expand=False,
        )

        table.add_column("Status", style=UIStyles.PRIMARY, width=8)
        table.add_column("Arquivo", style=UIStyles.SUCCESS)

        for line in status_lines:
            if line and len(line) > 2:
                status = line[:2].strip() or "?"
                filename = line[3:].strip()

                status_style = self._get_status_style(status)
                table.add_row(Text(status, style=status_style), filename)

        if not status_lines or not any(status_lines):
            success_style = UIStyles.safe_style("SUCCESS", "green")
            return Text(
                f"{UIIcons.SUCCESS} Working tree limpo - nenhuma mudança pendente",
                style=success_style,
            )

        return table

    def _get_status_style(self, status: str) -> str:
        """Return the Rich style for a git status character."""
        status_map = {
            "M": "yellow",
            "A": "green",
            "D": "red",
            "R": "cyan",
            "C": "blue",
            "U": "magenta",
            "?": "dim",
            "!": "dim red",
        }
        return status_map.get(status.strip()[0] if status.strip() else "?", "white")


class GitDiffOutput(ComponentBase):
    """Renders git diff output as a Rich component."""

    def __init__(self):
        """Initialize the instance."""
        super().__init__()

    def render(
        self,
        diff_content: str,
        file: Optional[str] = None,
        staged: bool = False,
        console_width: int = 80,
    ) -> RenderableType:
        """
        Render a git diff with syntax highlighting.

        Args:
            diff_content: Diff content
            file: Specific file (optional)
            staged: Whether it is a staged diff
            console_width: Largura do console

        Returns:
            Renderable Rich
        """
        if not diff_content:
            info_style = UIStyles.safe_style("INFO", "blue")
            return Text(
                f"{UIIcons.INFO} Nenhuma diferença encontrada.", style=info_style
            )

        title = "Git Dif"
        if staged:
            title += " (Staged)"
        if file:
            title += f" - {file}"

        syntax = Syntax(
            diff_content, "dif", theme="monokai", line_numbers=True, word_wrap=True
        )

        # Diff statistics
        stats = self._calculate_diff_stats(diff_content)

        info_style = UIStyles.safe_style("INFO", "blue")
        body_style = UIStyles.safe_style("BODY", "white")
        title_style = UIStyles.safe_style("TITLE", "cyan")
        border_primary_style = UIStyles.safe_style("BORDER_PRIMARY", "cyan")

        stats_text = Text()
        stats_text.append(f"{UIIcons.INFO} ", style=info_style)
        stats_text.append(
            f"+{stats['added']} -{stats['removed']} ~{stats['modified']}",
            style=body_style,
        )

        return Panel(
            Group(syntax, Text(), stats_text),
            title=f"[{title_style}]{title}[/{title_style}]",
            border_style=border_primary_style,
            padding=(1, 2),
            box=box.ROUNDED,
            expand=False,
        )

    def _calculate_diff_stats(self, diff_content: str) -> Dict[str, int]:
        """Calculate diff statistics (additions, deletions)."""
        lines = diff_content.splitlines()
        added = sum(
            1 for line in lines if line.startswith("+") and not line.startswith("+++")
        )
        removed = sum(
            1 for line in lines if line.startswith("-") and not line.startswith("---")
        )
        modified = min(added, removed)  # Approximation
        return {"added": added, "removed": removed, "modified": modified}


class GitLogOutput(ComponentBase):
    """Renders git log output as a Rich component."""

    def __init__(self):
        """Initialize the instance."""
        super().__init__()

    def render(
        self,
        log_entries: List[Dict[str, str]],
        limit: int = 10,
        console_width: int = 80,
        selected_index: Optional[int] = None,
    ) -> RenderableType:
        """
        Render a formatted git log table with commit preview.

        Args:
            log_entries: List of commits [{hash, author, date, message}]
            limit: Limite de commits
            console_width: Largura do console
            selected_index: Index of the selected commit ara preview

        Returns:
            Renderable Rich
        """
        if not log_entries:
            info_style = UIStyles.safe_style("INFO", "blue")
            return Text(f"{UIIcons.INFO} Nenhum commit encontrado.", style=info_style)

        title_style = UIStyles.safe_style("TITLE", "cyan")
        subtitle_style = UIStyles.safe_style("SUBTITLE", "bold cyan")
        border_primary_style = UIStyles.safe_style("BORDER_PRIMARY", "cyan")
        table = Table(
            title=f"[{title_style}]Git Log (últimos {limit} commits)[/{title_style}]",
            show_header=True,
            header_style=subtitle_style,
            border_style=border_primary_style,
            expand=False,
        )

        table.add_column("#", width=3)
        table.add_column("Hash", style=UIStyles.WARNING, width=8)
        table.add_column("Autor", style=UIStyles.PRIMARY, width=15)
        table.add_column("Data", style="dim", width=12)
        table.add_column("Mensagem", style="white")

        primary_style = UIStyles.safe_style("PRIMARY", "cyan")
        body_style = UIStyles.safe_style("BODY", "white")
        for idx, entry in enumerate(log_entries[:limit]):
            is_selected = idx == selected_index
            marker = "►" if is_selected else " "
            row_style = f"{primary_style} bold" if is_selected else body_style

            table.add_row(
                f"[{row_style}]{marker}[/]",
                f"[{primary_style}]{entry.get('hash', '')[:7]}[/]",
                entry.get("author", "")[:15],
                entry.get("date", "")[:10],
                entry.get("message", "")[:50],
                style=row_style,
            )

        # Preview do commit selecionado
        if selected_index is not None and 0 <= selected_index < len(log_entries):
            selected = log_entries[selected_index]
            preview = self._render_commit_preview(selected)
            return Group(table, preview)

        return table

    def _render_commit_preview(self, commit: Dict[str, str]) -> Panel:
        """Renderiza preview rico de um commit."""

        content_parts = []

        # Header with hash and author
        title_style = UIStyles.safe_style("TITLE", "cyan")
        accent_style = UIStyles.safe_style("ACCENT", "magenta")
        muted_style = UIStyles.safe_style("MUTED", "dim white")
        header = Text()
        header.append(f"{UIIcons.GIT} Commit: ", style=title_style)
        header.append(commit.get("hash", "")[:7], style=f"{accent_style} bold")
        header.append(f" by {commit.get('author', 'unknown')}", style=muted_style)
        content_parts.append(header)
        content_parts.append(Text())

        # Mensagem
        label_style = UIStyles.safe_style("LABEL", "bold")
        body_style = UIStyles.safe_style("BODY", "white")
        message_text = Text()
        message_text.append("Message: ", style=label_style)
        message_text.append(commit.get("message", ""), style=body_style)
        content_parts.append(message_text)
        content_parts.append(Text())

        # Data
        date_text = Text()
        date_text.append("Date: ", style=label_style)
        date_text.append(commit.get("date", ""), style=muted_style)
        content_parts.append(date_text)

        border_accent_style = UIStyles.safe_style("BORDER_ACCENT", "magenta")
        return Panel(
            Group(*content_parts),
            title="Detalhes do commit",
            border_style=border_accent_style,
            padding=(1, 2),
            box=box.ROUNDED,
        )


class GitCommitConfirmation(ComponentBase):
    """Renders a git commit confirmation panel."""

    def __init__(self):
        """Initialize the instance."""
        super().__init__()

    def render(
        self, message: str, files: Optional[List[str]] = None, auto_run: bool = False
    ) -> RenderableType:
        """
        Render a commit confirmation panel.

        Args:
            message: Commit message
            files: Files to be committed
            auto_run: Whether in auto-run mode

        Returns:
            Renderable Rich
        """
        warning_style = UIStyles.safe_style("WARNING", "yellow")
        info_style = UIStyles.safe_style("INFO", "blue")
        content = Text()
        content.append(f"{UIIcons.WARNING} Criar commit?\n\n", style=warning_style)
        content.append("Mensagem: ", style="bold")
        content.append(f"{message}\n", style=info_style)

        if files:
            content.append("Arquivos: ", style="bold")
            content.append(f"{', '.join(files)}\n", style=UIStyles.SUCCESS)
        else:
            content.append("Arquivos: ", style="bold")
            content.append("Todos no staging area\n", style="dim")

        if auto_run:
            success_style = UIStyles.safe_style("SUCCESS", "green")
            content.append(
                f"\n{UIIcons.SUCCESS} Auto-run: Criando commit automaticamente.",
                style=success_style,
            )

        title_style = UIStyles.safe_style("TITLE", "cyan")
        border_warning_style = UIStyles.safe_style("BORDER_WARNING", "yellow")
        return Panel(
            content,
            title=f"[{title_style}]Git Commit[/{title_style}]",
            border_style=border_warning_style,
            padding=(1, 2),
            box=box.ROUNDED,
            expand=False,
        )


class GitBranchOutput(ComponentBase):
    """Renders git branch output as a Rich component."""

    def __init__(self):
        """Initialize the instance."""
        super().__init__()

    def render(
        self, branches: List[str], current_branch: str, console_width: int = 80
    ) -> RenderableType:
        """
        Render a branch list.

        Args:
            branches: List of branches
            current_branch: Current branch ual
            console_width: Largura do console

        Returns:
            Renderable Rich
        """
        content = Text()
        content.append("Branch atual: ", style="bold")
        content.append(f"{current_branch}\n\n", style=UIStyles.SUCCESS)

        subtitle_style = UIStyles.safe_style("SUBTITLE", "bold cyan")
        content.append("Branches locais:\n", style=subtitle_style)

        for branch in branches:
            if branch.startswith("*"):
                content.append(
                    f"  {UIIcons.ARROW} {branch[1:].strip()}\n", style=UIStyles.SUCCESS
                )
            elif branch.strip().startswith("remotes/"):
                content.append(f"    {branch.strip()}\n", style="dim")
            else:
                content.append(f"    {branch.strip()}\n", style="white")

        title_style = UIStyles.safe_style("TITLE", "cyan")
        border_primary_style = UIStyles.safe_style("BORDER_PRIMARY", "cyan")
        return Panel(
            content,
            title=f"[{title_style}]Git Branches[/{title_style}]",
            border_style=border_primary_style,
            padding=(1, 2),
            box=box.ROUNDED,
            expand=False,
        )
