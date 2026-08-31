"""AgentWorkspacePanel — collapsible inner panel for tool executions."""

import json
import time
from typing import Any, Dict, List, Optional

from rich.console import Group, RenderableType
from rich.text import Text

from aura_cli.application.execution import OperationStatus, TurnExecution
from aura_cli.application.presentation.cli_visual import cli_label, decide_cli_visual
from aura_cli.cli.ui.composition.visual_surface import surface_panel
from aura_cli.cli.ui.constants import UIIcons, UIStyles


class ToolCallEntry:
    """Represents a single tool execution entry."""

    def __init__(self, name: str, args: Dict[str, Any]):
        self.name = name
        self.args = args
        self.result: Any = None
        self.success: bool = True
        self.duration_ms: float = 0.0
        self._start = time.time()

    def finish(self, result: Any, success: bool = True):
        self.result = result
        self.success = success
        self.duration_ms = (time.time() - self._start) * 1000

    def render_line(self) -> Text:
        """Renderiza uma linha compacta para o painel."""
        t = Text()

        icon = UIIcons.SUCCESS if self.success else UIIcons.ERROR
        color = UIStyles.SUCCESS if self.success else UIStyles.ERROR
        t.append(f"{icon} ", style=color)
        t.append(self.name, style=f"bold {color}")
        t.append(f"  {self.duration_ms:.0f}ms", style=UIStyles.MUTED)

        # Preview dos args
        if self.args:
            preview_parts = []
            for k, v in list(self.args.items())[:2]:
                sv = str(v)
                if len(sv) > 40:
                    sv = sv[:37] + "..."
                preview_parts.append(f"{k}={sv!r}")
            if preview_parts:
                t.append(
                    f"  ({', '.join(preview_parts)})",
                    style=f"dim {UIStyles.INFO}",
                )

        return t

    def render_result_preview(self, max_chars: int = 200) -> Optional[Text]:
        """Render a result preview (only when relevant)."""
        if self.result is None:
            return None
        if isinstance(self.result, dict):
            content = json.dumps(self.result, ensure_ascii=False)
        else:
            content = str(self.result)
        if len(content) > max_chars:
            content = content[:max_chars] + "…"
        t = Text(f"    {content}", style="dim")
        return t


class AgentWorkspacePanel:
    """Collapsible panel grouping agent tool executions."""

    def __init__(
        self, title: str = "Agente", turn_execution: TurnExecution | None = None
    ):
        self.title = title
        self._entries: List[ToolCallEntry] = []
        self._turn_execution = turn_execution

    def add(self, entry: ToolCallEntry) -> None:
        self._entries.append(entry)

    def render(self, expanded: bool = False, console_width: int = 80) -> RenderableType:
        """Render the workspace panel."""
        parts = []

        entries = self._project_entries()
        total = len(entries)
        errors = sum(1 for e in entries if not e.success)
        total_ms = sum(e.duration_ms for e in entries)

        plan = decide_cli_visual(console_width)
        visible_entries = entries if expanded else entries[-plan.visible_operations :]
        hidden = len(entries) - len(visible_entries)
        if hidden:
            parts.append(
                Text(f"⋯ {hidden} operações anteriores", style=UIStyles.MUTED)
            )

        for entry in visible_entries:
            parts.append(entry.render_line())
            if expanded:
                preview = entry.render_result_preview()
                if preview:
                    parts.append(preview)

        # Footer with summary
        footer = Text()
        footer.append(
            f"{total} {'operação' if total == 1 else 'operações'}",
            style=UIStyles.MUTED,
        )
        if errors:
            footer.append(
                f"  {errors} erro{'s' if errors != 1 else ''}",
                style=f"dim {UIStyles.ERROR}",
            )
        footer.append(f"  {total_ms:.0f}ms total", style=UIStyles.MUTED)
        parts.append(footer)

        title_text = Text()
        title_text.append(
            f"{UIIcons.TOOL} {cli_label('operations')}",
            style=f"{UIStyles.MUTED} bold",
        )

        return surface_panel(
            Group(*parts),
            title=title_text,
            border_style=UIStyles.BORDER_MUTED,
            console_width=console_width,
        )

    @property
    def has_entries(self) -> bool:
        return bool(self._project_entries())

    def _project_entries(self) -> List[ToolCallEntry]:
        if self._turn_execution is None:
            return self._entries
        projected: List[ToolCallEntry] = []
        for operation in self._turn_execution.operations:
            entry = ToolCallEntry(operation.label, operation.arguments_sanitized)
            entry.result = operation.result_summary
            entry.success = operation.status is OperationStatus.SUCCEEDED
            entry.duration_ms = (operation.duration or 0) * 1000
            projected.append(entry)
        return projected
