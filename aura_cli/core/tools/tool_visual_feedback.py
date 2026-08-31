"""
Unified Visual Feedback System for Aura CLI Tools.

This module provides a centralized system for visual feedback during tool execution,
ensuring consistent UX across all 50+ tools in the Aura ecosystem.

Features:
    - Progress indicators for long-running operations
    - Success/error feedback with consistent styling
    - Real-time status updates
    - Tool execution metrics tracking
    - Integration with the Live Dashboard system

Usage:
    from aura_cli.core.tools.tool_visual_feedback import ToolFeedback, with_feedback

    @with_feedback("analyze_code")
    def analyze_code(path: str) -> str:
        ...
"""

from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import functools
import time
from typing import Any, Callable, ClassVar, Dict, List, Optional, TypeVar

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from aura_cli.core.logger import get_logger

logger = get_logger(__name__)


class ToolStatus(Enum):
    """Tool execution status."""

    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"
    CANCELLED = "cancelled"


class ToolCategory(Enum):
    """Tool category for grouping and display."""

    FILE_SYSTEM = "file_system"
    CODEBASE = "codebase"
    MEMORY = "memory"
    GIT = "git"
    DOCKER = "docker"
    SHELL = "shell"
    WEB = "web"
    SYSTEM = "system"
    ANALYSIS = "analysis"
    TASK = "task"


@dataclass
class ToolExecution:
    """Record of a tool execution."""

    tool_name: str
    category: ToolCategory
    status: ToolStatus = ToolStatus.PENDING
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None
    args: Dict[str, Any] = field(default_factory=dict)
    result_preview: Optional[str] = None
    error_message: Optional[str] = None
    metrics: Dict[str, Any] = field(default_factory=dict)

    @property
    def duration(self) -> float:
        """Get execution duration in seconds."""
        if self.end_time:
            return self.end_time - self.start_time
        return time.time() - self.start_time

    @property
    def duration_str(self) -> str:
        """Get formatted duration string."""
        d = self.duration
        if d < 1:
            return f"{d * 1000:.0f}ms"
        elif d < 60:
            return f"{d:.1f}s"
        else:
            return f"{d / 60:.1f}m"


TOOL_CATEGORIES: Dict[str, ToolCategory] = {
    "read_file": ToolCategory.FILE_SYSTEM,
    "write_file": ToolCategory.FILE_SYSTEM,
    "list_directory": ToolCategory.FILE_SYSTEM,
    "find_directory": ToolCategory.FILE_SYSTEM,
    "codebase_search": ToolCategory.CODEBASE,
    "glob_search": ToolCategory.CODEBASE,
    "view_repo_map": ToolCategory.CODEBASE,
    "view_subdirectory": ToolCategory.CODEBASE,
    "advanced_grep_search": ToolCategory.CODEBASE,
    "investigate_codebase": ToolCategory.CODEBASE,
    "investigate_codebase_deep": ToolCategory.CODEBASE,
    "get_code_insights": ToolCategory.CODEBASE,
    "ler_pagina_caderno": ToolCategory.MEMORY,
    "listar_paginas_caderno": ToolCategory.MEMORY,
    "ver_indice_caderno": ToolCategory.MEMORY,
    "info_sessao_caderno": ToolCategory.MEMORY,
    "save_constitution": ToolCategory.MEMORY,
    "git_status": ToolCategory.GIT,
    "git_diff": ToolCategory.GIT,
    "git_log": ToolCategory.GIT,
    "git_branch": ToolCategory.GIT,
    "git_commit": ToolCategory.GIT,
    "git_commit_smart": ToolCategory.GIT,
    "git_smart": ToolCategory.GIT,
    "parse_natural_git_command": ToolCategory.GIT,
    "suggest_commit_message": ToolCategory.GIT,
    "docker_ps": ToolCategory.DOCKER,
    "docker_images": ToolCategory.DOCKER,
    "docker_logs": ToolCategory.DOCKER,
    "docker_exec": ToolCategory.DOCKER,
    "docker_build": ToolCategory.DOCKER,
    "docker_compose": ToolCategory.DOCKER,
    "run_shell_command": ToolCategory.SHELL,
    "execute_shell_command": ToolCategory.SHELL,
    "web_search": ToolCategory.WEB,
    "check_service_health": ToolCategory.SYSTEM,
    "check_port": ToolCategory.SYSTEM,
    "system_resources": ToolCategory.SYSTEM,
    "process_info": ToolCategory.SYSTEM,
    "scan_filesystem_sync": ToolCategory.SYSTEM,
    "get_imagination_scanner": ToolCategory.SYSTEM,
    "edit_file": ToolCategory.ANALYSIS,
    "analyze_code": ToolCategory.ANALYSIS,
    "find_in_files": ToolCategory.ANALYSIS,
    "tree_view": ToolCategory.ANALYSIS,
    "deep_project_analysis": ToolCategory.ANALYSIS,
    "discover_patterns": ToolCategory.ANALYSIS,
    "analyze_dependencies": ToolCategory.ANALYSIS,
    "create_task_list": ToolCategory.TASK,
    "complete_task": ToolCategory.TASK,
    "view_tasks": ToolCategory.TASK,
    "add_task": ToolCategory.TASK,
    "get_next_task": ToolCategory.TASK,
}

CATEGORY_STYLES: Dict[ToolCategory, Dict[str, str]] = {
    ToolCategory.FILE_SYSTEM: {"icon": "📁", "color": "cyan"},
    ToolCategory.CODEBASE: {"icon": "🔍", "color": "blue"},
    ToolCategory.MEMORY: {"icon": "💾", "color": "magenta"},
    ToolCategory.GIT: {"icon": "📝", "color": "green"},
    ToolCategory.DOCKER: {"icon": "🐳", "color": "blue"},
    ToolCategory.SHELL: {"icon": "💻", "color": "yellow"},
    ToolCategory.WEB: {"icon": "🌐", "color": "cyan"},
    ToolCategory.SYSTEM: {"icon": "⚙️", "color": "white"},
    ToolCategory.ANALYSIS: {"icon": "📊", "color": "magenta"},
    ToolCategory.TASK: {"icon": "📋", "color": "green"},
}


class ToolFeedback:
    """
    Unified visual feedback manager for tool execution.

    Provides consistent progress indicators, status updates, and
    result formatting across all Aura CLI tools.
    """

    _instance: Optional["ToolFeedback"] = None
    _executions: ClassVar[List[ToolExecution]] = []
    _console: Console

    def __new__(cls):
        """Enforce singleton pattern."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._console = Console()
            cls._instance._executions = []
        return cls._instance

    @property
    def console(self) -> Console:
        """Return the shared Rich console instance."""
        return self._console

    def get_category(self, tool_name: str) -> ToolCategory:
        """Get category for a tool."""
        return TOOL_CATEGORIES.get(tool_name, ToolCategory.ANALYSIS)

    def get_style(self, tool_name: str) -> Dict[str, str]:
        """Get style info for a tool."""
        category = self.get_category(tool_name)
        return CATEGORY_STYLES.get(category, {"icon": "🔧", "color": "white"})

    @contextmanager
    def track_execution(self, tool_name: str, args: Dict[str, Any] | None = None):
        """
        Context manager to track tool execution.

        Usage:
            with feedback.track_execution("read_file", {"path": "main.py"}):
                # ... tool code ...
        """
        execution = ToolExecution(
            tool_name=tool_name,
            category=self.get_category(tool_name),
            args=args or {},
        )
        self._executions.append(execution)

        style = self.get_style(tool_name)
        self._show_start(tool_name, style, args)

        execution.status = ToolStatus.RUNNING

        try:
            yield execution
            execution.status = ToolStatus.SUCCESS
            execution.end_time = time.time()
            self._show_success(tool_name, style, execution)
        except Exception as e:
            execution.status = ToolStatus.ERROR
            execution.error_message = str(e)
            execution.end_time = time.time()
            self._show_error(tool_name, style, execution, e)
            raise

    def _show_start(
        self, tool_name: str, style: Dict[str, str], args: Dict[str, Any] | None = None
    ):
        """Show tool start feedback."""
        icon = style["icon"]
        color = style["color"]

        args_preview = ""
        if args:
            key_args = []
            for k, v in list(args.items())[:3]:
                if isinstance(v, str) and len(v) > 30:
                    v = v[:27] + "..."
                key_args.append(f"{k}={v!r}")
            args_preview = f"({', '.join(key_args)})"
            if len(args) > 3:
                args_preview = args_preview[:-1] + f", ...{len(args) - 3} more)"

        self._console.print(
            f"[dim]{icon}[/dim] [{color}]{tool_name}[/{color}]{args_preview}",
            highlight=False,
        )

    def _show_success(
        self, tool_name: str, style: Dict[str, str], execution: ToolExecution
    ):
        """Show success feedback."""
        color = style["color"]
        self._console.print(
            f"  [green]✓[/green] [{color}]Completed[/{color}] "
            f"[dim]({execution.duration_str})[/dim]"
        )

    def _show_error(
        self,
        tool_name: str,
        style: Dict[str, str],
        execution: ToolExecution,
        error: Exception,
    ):
        """Show error feedback."""
        self._console.print(f"  [red]✗ Error:[/red] {str(error)[:50]}")

    def show_progress(self, tool_name: str, message: str):
        """Show progress update for a running tool."""
        style = self.get_style(tool_name)
        self._console.print(f"  [dim]{style['icon']} {message}[/dim]")

    def get_execution_summary(self) -> Dict[str, Any]:
        """Get summary of all tool executions in session."""
        if not self._executions:
            return {"total": 0, "by_status": {}, "by_category": {}}

        by_status: Dict[str, int] = {}
        by_category: Dict[str, int] = {}
        total_time: float = 0

        for ex in self._executions:
            status = ex.status.value
            by_status[status] = by_status.get(status, 0) + 1
            cat = ex.category.value
            by_category[cat] = by_category.get(cat, 0) + 1
            if ex.end_time:
                total_time += ex.duration

        return {
            "total": len(self._executions),
            "by_status": by_status,
            "by_category": by_category,
            "total_time": total_time,
            "success_rate": by_status.get("success", 0) / len(self._executions) * 100
            if self._executions
            else 0,
        }

    def render_summary_panel(self) -> Panel:
        """Render a summary panel of tool executions."""
        summary = self.get_execution_summary()

        if summary["total"] == 0:
            return Panel(
                "[dim]No tool executions recorded[/dim]",
                title="🔧 Tool Summary",
                border_style="dim",
            )

        table = Table(show_header=False, box=None, padding=(0, 1))
        table.add_column("Metric")
        table.add_column("Value")

        table.add_row("Total executions", str(summary["total"]))
        table.add_row("Success rate", f"{summary['success_rate']:.1f}%")
        table.add_row("Total time", f"{summary['total_time']:.1f}s")
        if summary["by_category"]:
            table.add_row("", "")
            table.add_row("[bold]By Category[/bold]", "")
            for cat, count in sorted(
                summary["by_category"].items(), key=lambda x: -x[1]
            ):
                cat_enum = ToolCategory(cat)
                style = CATEGORY_STYLES.get(cat_enum, {})
                icon = style.get("icon", "•")
                table.add_row(f"  {icon} {cat}", str(count))

        return Panel(table, title="🔧 Tool Execution Summary", border_style="cyan")

    def clear_history(self):
        """Clear execution history."""
        self._executions = []


_feedback: Optional[ToolFeedback] = None


def get_tool_feedback() -> ToolFeedback:
    """Get the global ToolFeedback instance."""
    global _feedback
    if _feedback is None:
        _feedback = ToolFeedback()
    return _feedback


F = TypeVar("F", bound=Callable[..., Any])


def with_feedback(tool_name: str):
    """
    Decorator to add visual feedback to tool functions.

    Usage:
        @with_feedback("my_tool")
        def my_tool(arg1, arg2):
            ...
    """

    def decorator(func: F) -> F:
        """Decorator factory for plugin registration."""

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            """Async wrapper that executes the tool."""
            feedback = get_tool_feedback()
            with feedback.track_execution(tool_name, kwargs):
                return func(*args, **kwargs)

        return wrapper  # type: ignore[return-value]

    return decorator


def generate_tool_audit_report() -> str:
    """
    Generate a comprehensive audit report of all available tools.

    Returns:
        Formatted audit report as string
    """
    from aura_cli.core.service_registry import get_tools_dict

    tools = get_tools_dict()

    report_lines = [
        "=" * 70,
        "🔧 AURA CLI TOOL AUDIT REPORT",
        "=" * 70,
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"Total Tools: {len(tools)}",
        "",
        "-" * 70,
        "TOOLS BY CATEGORY",
        "-" * 70,
    ]
    by_category: Dict[ToolCategory, List[str]] = {}
    uncategorized = []

    for tool_name in tools:
        category = TOOL_CATEGORIES.get(tool_name)
        if category:
            if category not in by_category:
                by_category[category] = []
            by_category[category].append(tool_name)
        else:
            uncategorized.append(tool_name)
    for category in ToolCategory:
        if category in by_category:
            style = CATEGORY_STYLES.get(category, {})
            icon = style.get("icon", "•")
            tool_list = by_category[category]

            report_lines.append(
                f"\n{icon} {category.value.upper()} ({len(tool_list)} tools)"
            )
            for tool_name in sorted(tool_list):
                func = tools[tool_name]
                doc = func.__doc__ or ""
                first_line = doc.split("\n")[0].strip() if doc else "No description"
                report_lines.append(f"   • {tool_name}: {first_line[:50]}")
    if uncategorized:
        report_lines.append(f"\n⚠️ UNCATEGORIZED ({len(uncategorized)} tools)")
        for tool_name in sorted(uncategorized):
            report_lines.append(f"   • {tool_name}")
    report_lines.extend(
        [
            "",
            "-" * 70,
            "SUMMARY",
            "-" * 70,
            f"Total Categories: {len(by_category)}",
            f"Categorized Tools: {sum(len(t) for t in by_category.values())}",
            f"Uncategorized: {len(uncategorized)}",
            "",
            "=" * 70,
        ]
    )

    return "\n".join(report_lines)
