"""SubAgentPanel - Displays parallel task delegation feedback."""

from time import time
from typing import Dict

from rich.console import Group, RenderableType
from rich.text import Text

from aura_cli.application.presentation.cli_visual import cli_label
from aura_cli.application.presentation.operational_panels import (
    DelegatedTaskState,
    delegated_tasks_complete,
)
from aura_cli.cli.ui.components.base import ComponentBase
from aura_cli.cli.ui.constants import UIIcons, UIStyles


class SubAgentPanel(ComponentBase):
    """Renders parallel task delegation status."""

    def __init__(self, title: str = "Trabalho paralelo"):
        self.title = title
        self._tasks: Dict[str, DelegatedTaskState] = {}

    def add_task(self, task_id: str, description: str) -> None:
        self._tasks[task_id] = DelegatedTaskState(description=description)

    def update_task(self, task_id: str, tool_count: int = 0) -> None:
        if task_id in self._tasks:
            t = self._tasks[task_id]
            t.mark_running(tool_count)

    def complete_task(self, task_id: str, tool_count: int, duration: float) -> None:
        if task_id in self._tasks:
            t = self._tasks[task_id]
            t.mark_done(tool_count, duration)

    def fail_task(self, task_id: str, error: str) -> None:
        if task_id in self._tasks:
            t = self._tasks[task_id]
            t.mark_failed(error)

    def is_complete(self) -> bool:
        return delegated_tasks_complete(self._tasks.values())

    def render(self) -> RenderableType:
        lines = []
        count = len(self._tasks)
        header = Text()
        header.append(
            f"{UIIcons.AGENT} {cli_label('parallel_work')} · {count} tarefas",
            style=UIStyles.TITLE,
        )
        lines.append(header)

        for t in self._tasks.values():
            line = Text()
            if t.status == "done":
                line.append(f"  {UIIcons.SUCCESS} ", style=UIStyles.SUCCESS)
                line.append(
                    f"{t.description} ({t.tool_count} operações · {t.duration:.1f}s)"
                )
            elif t.status == "running":
                elapsed = time() - t.start_time
                line.append(f"  {UIIcons.WORKING} ", style=UIStyles.STATUS_WORKING)
                line.append(
                    f"{t.description}… ({t.tool_count} operações · {elapsed:.1f}s)"
                )
            elif t.status == "failed":
                line.append(f"  {UIIcons.ERROR} ", style=UIStyles.ERROR)
                line.append(f"{t.description} — {t.error}")
            else:
                line.append(f"  {UIIcons.IDLE} ", style=UIStyles.MUTED)
                line.append(t.description)
            lines.append(line)

        return Group(*lines)
