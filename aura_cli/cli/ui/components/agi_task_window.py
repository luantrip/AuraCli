"""
AgiTaskWindow Component - Hybrid AGI/OPS Task Dashboard.

This component implements adaptive visualization that switches between:
1. AGI Mode (Architect): Focus on reasoning and chat
2. OPS Mode (Engineer): Focus on tool execution and technical logs

Features:
    - Mode Switching: Automatic AGI/OPS mode detection
    - Reasoning Display: AGI reasoning and planning
    - Tool Execution: OPS tool execution logs
    - LCD Display: Status display with metrics
    - Log Entries: Timestamped log entries with levels

Usage:
    >>> from aura_cli.cli.ui.components.agi_task_window import AgiTaskWindow
    >>> window = AgiTaskWindow()
    >>> window.render()
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

import rich.box as box
from rich.columns import Columns
from rich.console import Group, RenderableType
from rich.padding import Padding
from rich.panel import Panel
from rich.progress import (
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeElapsedColumn,
)
from rich.text import Text
from rich.tree import Tree

from aura_cli.cli.ui.components.base import ComponentBase
from aura_cli.cli.ui.components.lcd_display import AuraLCDDisplay
from aura_cli.cli.ui.constants import UIIcons, UIStyles
from aura_cli.cli.ui.strings import UIStrings
from aura_cli.cli.ui.theme_manager import get_theme_manager


def _format_supervisor_label(supervisor_state: str) -> str:
    """Format a supervisor agent label string."""
    labels = {
        "delegated": "DELEGADO",
        "in_progress": "EM ANDAMENTO",
        "completed": "CONCLUÍDO",
        "cancelled": "CANCELADO",
        "awaiting_human": "AGUARDANDO DECISÃO",
        "returned_to_chat": "DEVOLVIDO AO CHAT",
    }
    state = str(supervisor_state or "delegated")
    return labels.get(state, state.replace("_", " ").upper())


class LogEntry:
    """
    Log entry in AGI task window.

    Attributes:
        timestamp: Entry timestamp
        message: Log message
        level: Log level (info, success, warning, error, tool)
        details: Additional details dictionary
    """

    def __init__(
        self,
        timestamp: float,
        message: str,
        level: str = "info",
        details: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize log entry.

        Args:
            timestamp: Entry timestamp
            message: Log message
            level: Log level (default: "info")
            details: Additional details (default: {})
        """
        self.timestamp = timestamp
        self.message = message
        self.level = level
        self.details = details or {}

    def format(self, theme) -> Text:
        """
        Format log entry for plain text display (OPS Mode).

        Args:
            theme: Theme manager instance

        Returns:
            Formatted Rich Text

        Example:
            >>> entry = LogEntry(time.time(), "Task completed", "success")
            >>> text = entry.format(theme)
        """
        time_str = datetime.fromtimestamp(self.timestamp).strftime("%H:%M:%S")

        color_map = {
            "info": theme.get_color("body"),
            "success": theme.get_color("success"),
            "warning": theme.get_color("warning"),
            "error": theme.get_color("error"),
            "tool": theme.get_color("primary"),
        }
        icon_map = {
            "info": "▪",
            "success": "✔",
            "warning": "▲",
            "error": "✖",
            "tool": "⚒",
        }
        color = color_map.get(self.level, theme.get_color("muted"))
        icon = icon_map.get(self.level, "▪")

        text = Text()
        text.append(f"{icon} ", style=color)
        text.append(f"[{time_str}] ", style=f"dim {theme.get_color('muted')}")
        text.append(f"{self.message}", style=color)
        return text

    def format_tree(self, theme) -> Text:
        """Format tasks as a tree view."""
        time_str = datetime.fromtimestamp(self.timestamp).strftime("%H:%M")

        color = theme.get_color("body")
        if self.level == "error":
            color = theme.get_color("error")
        if self.level == "success":
            color = theme.get_color("success")

        text = Text()
        text.append(f"{self.message}", style=color)
        text.append(f" ({time_str})", style=f"dim {theme.get_color('muted')}")
        return text


class ToolExecution:
    """Represents a tool execution event in the AGI task window."""

    def __init__(
        self,
        tool_name: str,
        args: Dict[str, Any],
        status: str = "executing",
    ):
        """Initialize the instance."""
        self.tool_name = tool_name
        self.args = args
        self.status = status
        self.result: Optional[Any] = None
        self.error: Optional[str] = None
        self.execution_time: Optional[float] = None
        self.start_time = datetime.now().timestamp()

    def complete(self, success: bool, result: Any = None, error: Optional[str] = None):
        """Mark tool execution as complete."""
        self.status = "completed" if success else "failed"
        self.result = result
        self.error = error
        self.execution_time = datetime.now().timestamp() - self.start_time

    def format_compact(self, theme) -> Text:
        """Format tasks in compact single-line style."""
        text = Text()
        if self.status == "executing":
            text.append(
                f"{UIIcons.WORKING} {self.tool_name}",
                style=f"bold {theme.get_color('primary')}",
            )
        elif self.status == "completed":
            text.append(
                f"{UIIcons.SUCCESS} {self.tool_name}",
                style=f"dim {theme.get_color('success')}",
            )
        else:
            text.append(
                f"{UIIcons.ERROR} {self.tool_name}",
                style=f"bold {theme.get_color('error')}",
            )
        return text


class AgiTaskWindow(ComponentBase):
    """Rich component displaying the AGI task execution window."""

    def __init__(
        self,
        task_id: str,
        description: str,
        objective: str,
        parent_task_id: Optional[str] = None,
    ):
        """Initialize the instance."""
        self.task_id = task_id
        self.description = description
        self.objective = objective
        self.parent_task_id = parent_task_id
        self.status = "starting"
        self.logs: List[LogEntry] = []
        self.tool_executions: List[ToolExecution] = []
        self.children_tasks: List[str] = []
        self.start_time = datetime.now().timestamp()
        self.end_time: Optional[float] = None
        self.result: Optional[str] = None
        self.error: Optional[str] = None
        self.supervisor_state: str = "delegated"
        self.fallback_reason: Optional[str] = None

        self._cached_mode: Optional[str] = None
        self._cached_mode_log_count: int = 0
        self._cached_mode_tool_count: int = 0

    def set_supervisor_state(
        self, supervisor_state: str, fallback_reason: Optional[str] = None
    ) -> None:
        """Update the supervision-layer state shown in the task window."""
        self.supervisor_state = supervisor_state
        if fallback_reason:
            self.fallback_reason = fallback_reason

    def update_status(
        self,
        status: str,
        message: Optional[str] = None,
        *,
        supervisor_state: Optional[str] = None,
        fallback_reason: Optional[str] = None,
    ):
        """Update status."""
        self.status = status
        if supervisor_state:
            self.set_supervisor_state(supervisor_state, fallback_reason)
        elif status not in {"returned_to_chat", "awaiting_human"}:
            self.supervisor_state = "in_progress"
        if message:
            self.add_log_entry(message, level="info")

    def add_log_entry(
        self,
        message: str,
        level: str = "info",
        details: Optional[Dict[str, Any]] = None,
    ):
        """Add log entry."""
        entry = LogEntry(
            timestamp=datetime.now().timestamp(),
            message=message,
            level=level,
            details=details,
        )
        self.logs.append(entry)

    def add_tool_execution(self, tool_name: str, args: Dict[str, Any]) -> ToolExecution:
        """Add tool execution."""
        execution = ToolExecution(tool_name, args)
        self.tool_executions.append(execution)
        self.add_log_entry(f"Executando {tool_name}…", level="tool")
        return execution

    def complete_tool_execution(
        self,
        tool_name: str,
        success: bool,
        result: Any = None,
        error: Optional[str] = None,
    ):
        """Complete tool execution."""
        for execution in reversed(self.tool_executions):
            if execution.tool_name == tool_name and execution.status == "executing":
                execution.complete(success, result, error)
                level = "success" if success else "error"
                msg = f"{tool_name} concluída" if success else f"{tool_name} falhou"
                self.add_log_entry(msg, level=level)
                break

    def complete(
        self,
        success: bool,
        result: Optional[str] = None,
        error: Optional[str] = None,
        *,
        supervisor_state: Optional[str] = None,
        fallback_reason: Optional[str] = None,
    ):
        """Mark task as complete with result."""
        self.status = "completed" if success else "failed"
        if success:
            self.supervisor_state = "completed"
            self.fallback_reason = None
        else:
            self.set_supervisor_state(
                supervisor_state or "returned_to_chat", fallback_reason
            )
        self.end_time = datetime.now().timestamp()
        self.result = result
        self.error = error
        level = "success" if success else "error"
        msg = UIStrings.TASK_COMPLETED if success else f"Falha: {error or 'erro desconhecido'}"
        self.add_log_entry(msg, level=level)

    def cancel(self, reason: Optional[str] = None) -> None:
        """Mark the task as cancelled while preserving a terminal projection."""
        self.status = "cancelled"
        self.supervisor_state = "returned_to_chat"
        self.end_time = datetime.now().timestamp()
        self.error = reason
        message = "Operação cancelada"
        if reason:
            message = f"{message}: {reason}"
        self.add_log_entry(message, level="warning")

    def add_child_task(self, child_task_id: str):
        """Add child task."""
        self.children_tasks.append(child_task_id)

    def is_active(self) -> bool:
        """Return True if the task is still running (not completed or failed)."""
        return self.status not in {"completed", "failed", "cancelled"}

    def is_complete(self) -> bool:
        """Return True if the task has reached a terminal state."""
        return self.status in {"completed", "failed", "cancelled"}

    def _render_supervisor_summary(self, theme) -> Optional[Panel]:
        """Render a concise supervisor summary when state is non-normal."""
        if (
            self.supervisor_state in {"delegated", "in_progress", "completed"}
            and not self.fallback_reason
        ):
            return None

        summary = Text()
        summary.append("Estado da supervisão: ", style="dim")
        summary.append(
            _format_supervisor_label(self.supervisor_state),
            style=UIStyles.WARNING
            if self.supervisor_state != "completed"
            else UIStyles.SUCCESS,
        )
        if self.fallback_reason:
            summary.append("\nPlano alternativo: ", style="dim")
            summary.append(self.fallback_reason, style=UIStyles.WARNING)

        return Panel(
            summary,
            border_style=theme.get_color("warning"),
            title="[bold yellow]Supervisão[/bold yellow]",
            padding=(1, 2),
            box=box.ROUNDED,
        )

    def _detect_mode(self) -> str:
        """Detect the appropriate display mode for the terminal."""
        # Return cached result if state hasn't changed
        current_log_count = len(self.logs)
        current_tool_count = len(self.tool_executions)
        if (
            self._cached_mode is not None
            and self._cached_mode_log_count == current_log_count
            and self._cached_mode_tool_count == current_tool_count
        ):
            return self._cached_mode

        ops_score: float = 0
        agi_score: float = 0

        executing_tools = sum(
            1 for t in self.tool_executions if t.status == "executing"
        )
        ops_score += executing_tools * 5

        recent_tools = sum(
            1
            for t in self.tool_executions
            if t.status == "completed" and t.execution_time and t.execution_time < 60
        )
        ops_score += recent_tools * 2

        keywords_ops = [
            "run",
            "exec",
            "install",
            "build",
            "deploy",
            "git",
            "file",
            "write",
            "read",
            "execute",
            "command",
            "shell",
            "terminal",
            "docker",
            "container",
            "server",
            "api",
            "database",
            "migrate",
        ]
        keywords_agi = [
            "analyze",
            "plan",
            "design",
            "architect",
            "reason",
            "think",
            "strategy",
            "decide",
            "evaluate",
            "consider",
            "review",
            "assess",
        ]

        desc_lower = self.description.lower()
        obj_lower = self.objective.lower()
        combined_text = f"{desc_lower} {obj_lower}"

        ops_keyword_count = sum(1 for k in keywords_ops if k in combined_text)
        agi_keyword_count = sum(1 for k in keywords_agi if k in combined_text)

        ops_score += ops_keyword_count * 1.5
        agi_score += agi_keyword_count * 1.5

        tool_logs = sum(1 for log in self.logs if log.level == "tool")
        ops_score += tool_logs * 0.5

        thinking_logs = sum(
            1
            for log in self.logs
            if any(
                word in log.message.lower()
                for word in ["thinking", "considering", "analyzing", "planning"]
            )
        )
        agi_score += thinking_logs * 0.5

        if self.parent_task_id:
            ops_score += 1

        result = "ops" if ops_score > agi_score else "agi"

        # Cache result with current state fingerprint
        self._cached_mode = result
        self._cached_mode_log_count = current_log_count
        self._cached_mode_tool_count = current_tool_count

        return result

    def render(
        self,
        max_logs: int = 10,
        show_tools: bool = True,
        compact: bool = False,
    ) -> RenderableType:
        """Render component.

        Args:
            max_logs: Maximum number of logs to display
            show_tools: Whether to show tool execution panels
            compact: Reserved for compact view (not yet implemented)
        """
        _ = compact

        mode = self._detect_mode()

        if mode == "ops":
            return self._render_ops_view(max_logs, show_tools=show_tools)
        else:
            return self._render_agi_view(max_logs, show_tools=show_tools)

    def _render_ops_view(self, max_logs: int, show_tools: bool = True) -> Panel:
        """Render the OPS mode (Engineer) view with rich terminal output."""

        theme = get_theme_manager()
        primary_color = theme.get_color("primary")  # Electric Blue/Cyan

        header = Text()
        header.append(f" {UIIcons.OPS} ", style=f"bold {primary_color}")
        header.append("CONSOLE OPS", style="bold white")
        header.append(f" │ {self.task_id[:6]}", style="dim")
        header.append(" │ ", style="dim")
        header.append(
            f"SUP:{_format_supervisor_label(self.supervisor_state)}",
            style=f"bold {primary_color}"
            if self.supervisor_state == "completed"
            else "bold yellow",
        )

        active_tools = [t for t in self.tool_executions if t.status == "executing"]
        completed_tools = [t for t in self.tool_executions if t.status == "completed"]

        tools_parts = []

        if show_tools and active_tools:
            progress_group = Group()
            for tool in active_tools:
                progress = Progress(
                    SpinnerColumn(),
                    TextColumn(f"[bold cyan]{tool.tool_name}[/]"),
                    TimeElapsedColumn(),
                )
                progress.add_task("")
                progress_group.renderables.append(progress)

            tools_parts.append(
                Panel(
                    progress_group,
                    border_style=primary_color,
                    title="[bold cyan]Processos em execução[/bold cyan]",
                    padding=(1, 2),
                    box=box.ROUNDED,
                )
            )

        if show_tools and completed_tools:
            completed_group = Group()
            for tool in completed_tools[-5:]:  # Last 5
                tool_text = Text()
                tool_text.append(f"{UIIcons.SUCCESS} ", style=UIStyles.SUCCESS)
                tool_text.append(f"{tool.tool_name}", style=UIStyles.SUCCESS + " bold")
                if tool.execution_time:
                    tool_text.append(f" ({tool.execution_time:.2f}s)", style="dim")

                if (
                    tool.result
                    and isinstance(tool.result, str)
                    and len(tool.result) < 200
                ):
                    tool_text.append(f"\n  → {tool.result[:100]}...", style="dim")

                completed_group.renderables.append(tool_text)

            if completed_group.renderables:
                tools_parts.append(
                    Panel(
                        completed_group,
                        border_style=UIStyles.BORDER_SUCCESS,
                        title="[bold green]Concluído[/bold green]",
                        padding=(1, 2),
                        box=box.ROUNDED,
                    )
                )

        log_text = Text()
        for log in self.logs[-max_logs:]:
            log_text.append(log.format(theme))
            log_text.append("\n")

        lcd = AuraLCDDisplay().render(
            content=log_text,
            title="Saída padrão/erro",
            line_numbers=True,
            max_height=max_logs,
            variant="primary",
        )

        metrics_text = Text()
        if self.end_time and self.start_time:
            total_time = self.end_time - self.start_time
            metrics_text.append(
                f"○ Tempo total: {total_time:.2f}s", style=UIStyles.INFO
            )
        if self.tool_executions:
            success_rate = len(completed_tools) / len(self.tool_executions) * 100
            metrics_text.append(
                f" | Sucesso: {success_rate:.0f}%", style=UIStyles.SUCCESS
            )
            metrics_text.append(
                f" | Ferramentas: {len(self.tool_executions)}", style=UIStyles.PRIMARY
            )

        content_list: List[Any] = []
        supervisor_summary = self._render_supervisor_summary(theme)
        if supervisor_summary:
            content_list.append(supervisor_summary)
        if tools_parts:
            if len(tools_parts) == 1:
                content_list.append(tools_parts[0])
            else:
                content_list.append(Columns(tools_parts, equal=False, expand=True))
        content_list.append(lcd)
        if metrics_text.plain:
            content_list.append(metrics_text)

        return Panel(
            Group(*content_list),
            title=header,
            border_style=primary_color,
            padding=(1, 2),
            box=box.ROUNDED,
        )

    def _render_agi_view(self, max_logs: int, show_tools: bool = True) -> Panel:
        """Render the AGI mode (Architect) view with hierarchical structure."""

        theme = get_theme_manager()
        secondary_color = theme.get_color("secondary")  # Plasma Violet

        header = Text()
        header.append(f" {UIIcons.AGI} ", style=f"bold {secondary_color}")
        header.append("Fluxo cognitivo", style="bold white")
        header.append(f" │ {self.status.upper()}", style=f"dim {secondary_color}")
        header.append(" │ ", style="dim")
        header.append(
            f"SUP:{_format_supervisor_label(self.supervisor_state)}",
            style=f"bold {secondary_color}"
            if self.supervisor_state == "completed"
            else "bold yellow",
        )

        obj_panel = Panel(
            Text(
                f"{UIIcons.CHAT} {self.objective}",
                style=f"italic {theme.get_color('body')}",
            ),
            border_style=secondary_color,
            padding=(1, 2),
            box=box.ROUNDED,
        )

        tree = Tree(
            f"[bold {secondary_color}]Cadeia de raciocínio[/bold {secondary_color}]",
            guide_style=secondary_color,
        )

        recent_logs = self.logs[-max_logs:]
        current_context: Optional[str] = None
        context_node: Optional[Any] = None

        for log in recent_logs:
            if log.level == "tool":
                if current_context != "tools":
                    current_context = "tools"
                    context_node = tree.add(
                        f"[{UIStyles.PRIMARY}]{UIIcons.TOOL} Execução da ferramenta[/]"
                    )
                if context_node is not None:
                    context_node.add(log.format_tree(theme))
            elif log.level in ["success", "error"]:
                if current_context != "results":
                    current_context = "results"
                    context_node = tree.add(
                        f"[{UIStyles.SUCCESS if log.level == 'success' else UIStyles.ERROR}]Resultados[/]"
                    )
                if context_node is not None:
                    context_node.add(log.format_tree(theme))
            else:
                if current_context != "reasoning":
                    current_context = "reasoning"
                    context_node = tree.add(f"[{UIStyles.INFO}]Passos de raciocínio[/]")
                if context_node is not None:
                    context_node.add(log.format_tree(theme))

        metrics_panel = self._render_agi_metrics() if show_tools else None

        parts: List[Any] = [obj_panel]
        supervisor_summary = self._render_supervisor_summary(theme)
        if supervisor_summary:
            parts.append(supervisor_summary)
        parts.append(Padding(tree, (1, 0, 0, 1)))
        parts.append(metrics_panel if metrics_panel else Text())

        content_group = Group(*parts)

        return Panel(
            content_group,
            title=header,
            border_style=secondary_color,
            padding=(1, 1),
            box=box.ROUNDED,
        )

    def _render_agi_metrics(self) -> Optional[Panel]:
        """Render the reasoning metrics panel."""

        theme = get_theme_manager()

        total_logs = len(self.logs)
        tool_calls = sum(1 for log in self.logs if log.level == "tool")
        success_rate = (
            sum(1 for log in self.logs if log.level == "success") / total_logs * 100
            if total_logs > 0
            else 0
        )

        metrics_cards = []

        metrics_data = [
            ("Registros", str(total_logs), UIIcons.INFO),
            ("Ferramentas", str(tool_calls), UIIcons.TOOL),
            ("Sucesso", f"{success_rate:.0f}%", UIIcons.SUCCESS),
        ]

        for label, value, icon in metrics_data:
            card_text = Text(justify="center")
            card_text.append(f"{icon} ", style=theme.get_color("primary"))
            card_text.append(f"{value}\n", style="bold " + theme.get_color("primary"))
            card_text.append(label, style="dim")

            card = Panel(
                card_text,
                border_style=theme.get_color("muted"),
                padding=(1, 1),
            )
            metrics_cards.append(card)

        if metrics_cards:
            return Panel(
                Columns(metrics_cards, equal=True, expand=True),
                border_style=theme.get_color("muted"),
                padding=(1, 1),
            )
        return None
