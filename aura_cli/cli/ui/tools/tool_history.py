"""
Optional tool history explorer for the CLI.

This module is intentionally small. It supports `/dashboard tool_history`
without pretending to be a standalone analytics suite.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional

from rich.console import Console, Group, RenderableType
from rich.table import Table
from rich.text import Text

from aura_cli.cli.ui.constants import UIIcons, UIStyles
from aura_cli.cli.ui.layout_contract import layout_for_width


class ToolCategory(Enum):
    """Simplified tool category for history tracking."""

    GENERAL = "general"
    FILE_SYSTEM = "file_system"
    DEVELOPMENT = "development"
    SHELL = "shell"
    GIT = "git"
    DOCKER = "docker"
    TESTING = "testing"


class ExecutionStatus(Enum):
    """Execution status enum."""

    SUCCESS = "success"
    ERROR = "error"
    CANCELLED = "cancelled"


@dataclass
class ToolExecution:
    """Compact record of a single tool execution."""

    tool_name: str
    category: ToolCategory
    status: ExecutionStatus
    execution_time: float
    timestamp: datetime
    args: Dict[str, Any]
    result_preview: str
    error_message: Optional[str] = None


class ToolHistoryViewer:
    """Optional tool history explorer."""

    def __init__(self):
        self.search_query: str = ""

    def _guess_category(self, tool_name: str) -> ToolCategory:
        normalized = tool_name.lower()
        if any(token in normalized for token in ["file", "path", "dir"]):
            return ToolCategory.FILE_SYSTEM
        if any(token in normalized for token in ["shell", "bash", "command"]):
            return ToolCategory.SHELL
        if "git" in normalized:
            return ToolCategory.GIT
        if "docker" in normalized:
            return ToolCategory.DOCKER
        if "test" in normalized:
            return ToolCategory.TESTING
        if any(token in normalized for token in ["code", "refactor", "analy"]):
            return ToolCategory.DEVELOPMENT
        return ToolCategory.GENERAL

    def _load_executions(self, max_items: int) -> List[ToolExecution]:
        try:
            from aura_cli.core.stats import get_stats

            stats = get_stats()
            tools_used = (
                dict(stats.tools_used) if getattr(stats, "tools_used", None) else {}
            )
            if not tools_used:
                return []

            now = datetime.now()
            executions: List[ToolExecution] = []
            for index, (tool_name, count) in enumerate(
                list(tools_used.items())[:max_items]
            ):
                executions.append(
                    ToolExecution(
                        tool_name=tool_name,
                        category=self._guess_category(tool_name),
                        status=ExecutionStatus.SUCCESS,
                        execution_time=0.0,
                        timestamp=now - timedelta(seconds=index * 20),
                        args={},
                        result_preview=f"Usada {count} vez(es) nesta sessão",
                    )
                )
            return executions
        except Exception:
            return []

    def _render_empty_state(self, console_width: int = 80) -> RenderableType:
        body = Text()
        body.append(
            "Nenhuma execução de tool foi registrada nesta sessão.\n",
            style=UIStyles.BODY,
        )
        body.append(
            "Use o chat principal e o feedback operacional como superfícies canônicas.",
            style=UIStyles.MUTED,
        )
        header = Text(
            f"{UIIcons.TOOL} Histórico de ferramentas",
            style=UIStyles.TITLE,
        )
        return Group(header, body)

    def render(
        self,
        console: Console,
        max_items: int = 20,
        category_filter: Optional[str] = None,
    ) -> RenderableType:
        metrics = layout_for_width(console.width)
        executions = self._load_executions(max(1, max_items))
        if category_filter:
            try:
                category = ToolCategory(category_filter)
                executions = [item for item in executions if item.category == category]
            except ValueError:
                executions = []

        if self.search_query:
            query = self.search_query.lower()
            executions = [
                item for item in executions if query in item.tool_name.lower()
            ]

        if not executions:
            return self._render_empty_state(console.width)

        header = Text(
            f"{UIIcons.TOOL} Histórico de ferramentas",
            style=UIStyles.TITLE,
        )
        table = Table(
            show_header=True,
            header_style=UIStyles.SUBTITLE,
            box=None,
            expand=False,
        )
        compact = metrics.narrow
        table.add_column("Tempo", width=6 if compact else 8)
        table.add_column("Ferramenta", width=14 if compact else 26)
        table.add_column("Categoria", width=9 if compact else 15)
        table.add_column("Estado", width=12 if compact else 10)
        table.add_column("Resultado", width=13 if compact else 36)

        for execution in executions[:max_items]:
            delta = datetime.now() - execution.timestamp
            age_seconds = max(0, int(delta.total_seconds()))
            if age_seconds < 60:
                time_str = f"{age_seconds}s"
            elif age_seconds < 3600:
                time_str = f"{age_seconds // 60}min"
            else:
                time_str = f"{age_seconds // 3600}h"

            status_map = {
                ExecutionStatus.SUCCESS: (
                    UIIcons.SUCCESS,
                    "concluída",
                    UIStyles.SUCCESS,
                ),
                ExecutionStatus.ERROR: (UIIcons.ERROR, "falhou", UIStyles.ERROR),
                ExecutionStatus.CANCELLED: (
                    UIIcons.CANCEL,
                    "cancelada",
                    UIStyles.MUTED,
                ),
            }
            icon, label, style = status_map[execution.status]
            result = execution.error_message or execution.result_preview
            category_labels = {
                ToolCategory.FILE_SYSTEM: "arquivos",
                ToolCategory.DEVELOPMENT: "desenvolvimento",
                ToolCategory.SHELL: "shell",
                ToolCategory.GIT: "git",
                ToolCategory.DOCKER: "docker",
                ToolCategory.TESTING: "testes",
                ToolCategory.GENERAL: "geral",
            }
            category_name = category_labels.get(
                execution.category, execution.category.value
            )

            table.add_row(
                f"[{UIStyles.MUTED}]{time_str}[/]",
                f"[{UIStyles.PRIMARY}]{metrics.fit_inline(execution.tool_name, reserve=50)}[/]",
                f"[{UIStyles.LABEL}]{metrics.fit_inline(category_name, reserve=50)}[/]",
                f"[{style}]{icon} {label}[/]",
                f"[{UIStyles.BODY}]{metrics.fit_inline(result, reserve=50)}[/]",
            )

        summary = Text()
        summary.append(f"{UIIcons.INFO} ", style=UIStyles.INFO)
        summary.append("Itens: ", style=UIStyles.LABEL)
        summary.append(str(len(executions)), style=UIStyles.PRIMARY)

        return Group(header, table, summary)
