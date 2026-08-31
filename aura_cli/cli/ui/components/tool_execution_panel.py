"""
ToolExecutionPanel - Unified panel for grouped tool executions.

Consolidates multiple related tool calls into a single organized panel
with proper spacing, numbering, and visual hierarchy.
"""

import time
from typing import List, Optional

from rich.console import Group, RenderableType
from rich.padding import Padding
from rich.text import Text

from aura_cli.application.presentation.cli_visual import cli_label
from aura_cli.application.presentation.operational_panels import (
    ToolExecutionState,
    summarize_tool_executions,
)
from aura_cli.cli.ui.components.base import ComponentBase
from aura_cli.cli.ui.constants import UIIcons, UIStyles
from aura_cli.cli.ui.display_facade import get_console
from aura_cli.cli.ui.layout_contract import layout_for_width


class ToolExecutionPanel(ComponentBase):
    """
    Unified panel for grouped tool executions.

    Aggregates multiple tool calls into a single organized display
    with proper visual hierarchy and spacing.
    """

    def __init__(self, task_id: Optional[int] = None, task_description: str = ""):
        """Initialize the instance."""
        self.task_id = task_id
        self.task_description = task_description
        self.executions: List[ToolExecutionState] = []
        self.start_time = time.time()

    def add_tool(self, name: str, args: dict) -> ToolExecutionState:
        """Add new tool execution."""
        execution = ToolExecutionState(name=name, args=args)
        self.executions.append(execution)
        return execution

    def _format_duration(self, duration: float) -> str:
        """Format duration for display."""
        if duration < 1:
            return f"{duration * 1000:.0f}ms"
        return f"{duration:.2f}s"

    def _render_header(self) -> Text:
        """Render panel header."""
        text = Text()
        text.append(f"{UIIcons.TOOL} {cli_label('operations')}", style=UIStyles.PRIMARY)

        if self.task_id is not None:
            text.append(f" - Tarefa #{self.task_id}", style="dim")
            if self.task_description:
                desc = (
                    self.task_description[:50] + "..."
                    if len(self.task_description) > 50
                    else self.task_description
                )
                text.append(f": {desc}", style=UIStyles.BODY)

        return text

    def _render_tool_line(self, index: int, execution: ToolExecutionState) -> Text:
        """Render a tool line with semantic state."""
        status_meta = {
            "pending": (UIIcons.IDLE, "pendente", UIStyles.MUTED),
            "running": (UIIcons.RUN, "executando", UIStyles.PRIMARY),
            "success": (UIIcons.SUCCESS, "concluída", UIStyles.SUCCESS),
            "error": (UIIcons.ERROR, "falhou", UIStyles.ERROR),
            "cancelled": (UIIcons.CANCEL, "cancelada", UIStyles.WARNING),
            "canceled": (UIIcons.CANCEL, "cancelada", UIStyles.WARNING),
        }
        icon, label, style = status_meta.get(
            execution.status, (UIIcons.WORKING, execution.status, UIStyles.WARNING)
        )

        text = Text()
        text.append(f"{index}. ", style=UIStyles.MUTED)
        text.append(f"{icon} ", style=style)
        text.append(execution.name, style=UIStyles.TITLE)
        text.append(f" · {label}", style=f"dim {style}")

        if execution.duration is not None:
            text.append(f" ({self._format_duration(execution.duration)})", style="dim")

        return text

    def _render_tool_details(self, execution: ToolExecutionState) -> Optional[Text]:
        """Render tool execution details."""
        if execution.status == "pending":
            return None

        text = Text()
        text.append("   ", style="dim")

        if execution.status == "success" and execution.result:
            result_preview = (
                execution.result[:80] + "..."
                if len(execution.result) > 80
                else execution.result
            )
            text.append(f"→ {result_preview}", style=UIStyles.SUCCESS)
        elif execution.status == "error" and execution.error:
            error_preview = (
                execution.error[:80] + "..."
                if len(execution.error) > 80
                else execution.error
            )
            text.append(f"✗ {error_preview}", style=UIStyles.ERROR)
        elif execution.status == "running":
            text.append("→ Executando…", style=UIStyles.PRIMARY)
        elif execution.status in {"cancelled", "canceled"}:
            text.append("⊘ Execução cancelada", style=UIStyles.WARNING)

        return text if text.plain.strip() else None

    def _render_summary(self) -> Text:
        """Render execution summary."""
        summary = summarize_tool_executions(self.executions)
        success_count = summary["success"]
        error_count = summary["error"]
        total_duration = summary["duration"]
        cancelled_count = sum(
            execution.status in {"cancelled", "canceled"}
            for execution in self.executions
        )
        pending_count = sum(
            execution.status == "pending" for execution in self.executions
        )

        text = Text()

        if error_count > 0:
            text.append(f"{UIIcons.ERROR} ", style=UIStyles.ERROR)
            text.append(f"{error_count} com falha", style=UIStyles.ERROR)

        if success_count > 0:
            if text.plain:
                text.append(" · ", style="dim")
            text.append(f"{UIIcons.SUCCESS} ", style=UIStyles.SUCCESS)
            text.append(f"{success_count} concluída(s)", style=UIStyles.SUCCESS)

        if cancelled_count > 0:
            if text.plain:
                text.append(" · ", style="dim")
            text.append(f"{UIIcons.CANCEL} ", style=UIStyles.WARNING)
            text.append(f"{cancelled_count} cancelada(s)", style=UIStyles.WARNING)

        if pending_count > 0:
            if text.plain:
                text.append(" · ", style="dim")
            text.append(f"{pending_count} pendente(s)", style=UIStyles.MUTED)

        if total_duration > 0:
            text.append(f" · {self._format_duration(total_duration)}", style="dim")

        return text

    def render(
        self, show_summary: bool = True, console_width: int = 80
    ) -> RenderableType:
        """Renderiza tools como feed aberto com lifecycle inline."""
        metrics = layout_for_width(console_width)
        parts = []

        parts.append(self._render_header())
        if metrics.vertical_gap:
            parts.append(Text())

        for i, execution in enumerate(self.executions, 1):
            parts.append(self._render_tool_line(i, execution))

            details = self._render_tool_details(execution)
            if details:
                parts.append(details)

            if i < len(self.executions) and metrics.vertical_gap:
                parts.append(Text())

        if show_summary and self.executions:
            has_completed = any(
                e.status in ["success", "error"] for e in self.executions
            )
            if has_completed:
                if metrics.vertical_gap:
                    parts.append(Text())
                parts.append(Text("━" * min(60, metrics.content_width), style="dim"))
                parts.append(self._render_summary())

        return Padding(Group(*parts), metrics.group_padding)


_global_panel: Optional[ToolExecutionPanel] = None


def get_tool_panel() -> ToolExecutionPanel:
    """Get or create global tool execution panel."""
    global _global_panel
    if _global_panel is None:
        _global_panel = ToolExecutionPanel()
    return _global_panel


def reset_tool_panel(task_id: Optional[int] = None, task_description: str = ""):
    """Reset global panel for new task."""
    global _global_panel
    _global_panel = ToolExecutionPanel(task_id, task_description)
    return _global_panel


def display_tool_panel(panel: Optional[ToolExecutionPanel] = None):
    """Display tool execution panel."""
    console = get_console()
    if panel is None:
        panel = get_tool_panel()

    console.print(panel.render(console_width=console.width))
