"""Aura CLI - Pinned Todo / Task Panel Widget.

Displays an active task list pinned at the top of the interface,
matching the visual reference in docs/referencia-tui/todo-list-fixed-top.png.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import List, Optional

from rich.console import RenderableType
from rich.panel import Panel
from rich.text import Text
from textual.reactive import reactive
from textual.widget import Widget

import aura_cli.tui.constants as tui_constants


class TaskStatus(Enum):
    """Status of a task item."""

    COMPLETED = "completed"
    ACTIVE = "active"
    PENDING = "pending"


@dataclass
class TaskItem:
    """Individual task item."""

    text: str
    status: TaskStatus = TaskStatus.PENDING


class AuraTodoPanel(Widget):
    """Pinned top panel displaying current active tasks and goals."""

    DEFAULT_CSS = """
    AuraTodoPanel {
        height: auto;
        min-height: 3;
        max-height: 8;
        width: 100%;
        margin: 0 0 1 0;
        padding: 0 1;
        display: block;
    }

    AuraTodoPanel.--hidden {
        display: none;
    }
    """

    tasks: reactive[List[TaskItem]] = reactive(list, init=False)
    is_collapsed: reactive[bool] = reactive(False)

    def __init__(
        self,
        tasks: Optional[List[TaskItem]] = None,
        name: Optional[str] = None,
        id: Optional[str] = None,
        classes: Optional[str] = None,
    ) -> None:
        super().__init__(name=name, id=id, classes=classes)
        # Initialise with a fresh list — avoids shared state between instances
        self.tasks = list(tasks) if tasks else []

    def set_tasks(self, tasks: List[TaskItem]) -> None:
        """Replace the current list of tasks."""
        self.tasks = list(tasks)
        self._sync_visibility()
        self.refresh()

    def add_task(self, text: str, status: TaskStatus = TaskStatus.PENDING) -> None:
        """Add a new task to the panel."""
        new_tasks = list(self.tasks)
        new_tasks.append(TaskItem(text=text, status=status))
        self.tasks = new_tasks
        self._sync_visibility()
        self.refresh()

    def update_task_status(self, index: int, status: TaskStatus) -> None:
        """Update the status of an existing task by index."""
        if 0 <= index < len(self.tasks):
            new_tasks = list(self.tasks)
            new_tasks[index].status = status
            self.tasks = new_tasks
            self._sync_visibility()
            self.refresh()

    def clear_tasks(self) -> None:
        """Clear all tasks."""
        self.tasks = []
        self.display = False
        self.refresh()

    def on_mount(self) -> None:
        """Do not reserve vertical space until the turn has active tasks."""
        self._sync_visibility()

    def _sync_visibility(self) -> None:
        self.display = bool(self.tasks) and not self.is_collapsed

    def render(self) -> RenderableType:
        """Render the task stream with compact semantic markers."""
        if not self.tasks:
            return Text("")

        content = Text()
        status_styles = {
            TaskStatus.COMPLETED: ("green", "dim green"),
            TaskStatus.ACTIVE: ("yellow", "bold white"),
            TaskStatus.PENDING: ("grey50", "grey70"),
        }

        for i, item in enumerate(self.tasks):
            if i > 0:
                content.append("\n")

            status_key = (
                "starting" if item.status == TaskStatus.ACTIVE else item.status.value
            )
            marker = tui_constants.STATUS_ICONS.get(status_key, tui_constants.IDLE)
            marker_style, text_style = status_styles[item.status]
            content.append(f" {marker} ", style=f"bold {marker_style}")
            content.append(item.text, style=text_style)

        return Panel(
            content,
            border_style="dim",
            title=f"[bold]Tarefas · {len(self.tasks)}[/bold]",
            title_align="left",
            padding=(0, 1),
        )
