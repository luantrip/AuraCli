"""
TaskBoard - Visual Kanban-style task board for Aura CLI.

Provides interactive visual task board with columns for different task states,
progress tracking, and keyboard navigation.
"""

from typing import List, Optional

from rich.console import Group, RenderableType
from rich.progress import BarColumn, Progress, TextColumn
from rich.table import Table
from rich.text import Text

from aura_cli.application.presentation.task_board import build_task_board_columns
from aura_cli.cli.ui.components.base import ComponentBase
from aura_cli.cli.ui.constants import UIIcons, UILayout, UIStyles
from aura_cli.cli.ui.layout_contract import layout_for_width
from aura_cli.core.todo.todo_tracker import TodoTask, TodoTracker, get_todo_tracker


class TaskBoard(ComponentBase):
    """
    Visual Kanban-style task board component.

    Displays tasks in organized columns with progress tracking
    and visual indicators for task status and priority.
    """

    def __init__(self, tracker: Optional[TodoTracker] = None):
        """Initialize the instance."""
        self.tracker = tracker or get_todo_tracker()
        self.max_tasks_per_column = 5

    def _categorize_tasks(self) -> dict:
        """Categorize tasks into columns."""
        all_tasks = self.tracker.get_all_tasks()
        current_task = self.tracker.get_current_task()
        return build_task_board_columns(
            all_tasks,
            current_task=current_task,
            max_per_column=self.max_tasks_per_column,
        )

    def _create_progress_bar(self, console_width: int = 80) -> RenderableType:
        """Create visual progress bar sized for the current terminal."""
        stats = self.tracker.get_stats()
        total = stats["total"]
        done = stats["done"]

        progress = Progress(
            TextColumn(f"[{UIStyles.PRIMARY}]{UIIcons.STATS} Progresso:"),
            BarColumn(
                bar_width=min(
                    30, max(12, layout_for_width(console_width).content_width // 6)
                ),
                complete_style=UIStyles.SUCCESS,
                finished_style=UIStyles.SUCCESS,
            ),
            TextColumn("[bold]{task.percentage:>3.0f}%"),
            TextColumn(f"({done}/{total})"),
        )

        progress.add_task("progress", total=total, completed=done)

        return progress

    def _create_column(
        self, title: str, icon: str, tasks: List[TodoTask], count: int
    ) -> Table:
        """Create a single column for the board."""
        column = Table.grid(padding=(0, 1))
        column.add_column(justify="left")

        header = Text()
        header.append(f"{icon} {title}", style="bold")
        header.append(f"\n   ({count})", style="dim")
        column.add_row(header)
        column.add_row(Text("─" * 15, style="dim"))

        if not tasks:
            column.add_row(Text("(vazio)", style="dim"))
        else:
            for task in tasks[: self.max_tasks_per_column]:
                task_text = task.text[:30] + "..." if len(task.text) > 30 else task.text

                if task.is_done:
                    style = "dim green"
                    prefix = "✓"
                elif task in self._categorize_tasks()["doing"]:
                    style = "bold cyan"
                    prefix = "▶"
                else:
                    style = "white"
                    prefix = "•"

                column.add_row(Text(f"{prefix} {task_text}", style=style))

            if len(tasks) > self.max_tasks_per_column:
                remaining = len(tasks) - self.max_tasks_per_column
                column.add_row(Text(f"   +{remaining} tarefas", style="dim"))

        return column

    def _create_board_table(self, categories: dict, console_width: int = 80) -> Table:
        """Create the board, stacking columns when the terminal is compact."""
        metrics = layout_for_width(console_width)
        board = Table.grid(padding=(0, metrics.group_padding[1]))

        stats = self.tracker.get_stats()

        todo_col = self._create_column(
            "A fazer",
            UIIcons.TODO,
            categories["todo"],
            len(
                [
                    t
                    for t in self.tracker.get_all_tasks()
                    if t.is_pending and t not in categories["doing"]
                ]
            ),
        )

        doing_col = self._create_column(
            "Fazendo", "✦", categories["doing"], len(categories["doing"])
        )

        done_col = self._create_column(
            "Concluído", UIIcons.DONE, categories["done"], stats["done"]
        )

        priority_col = self._create_column(
            "Prioridade",
            UIIcons.PRIORITY_HIGH,
            categories["priority"],
            len(categories["priority"]),
        )

        columns = (todo_col, doing_col, done_col, priority_col)
        if metrics.narrow:
            board.add_column()
            for column in columns:
                board.add_row(column)
        else:
            for _ in columns:
                board.add_column()
            board.add_row(*columns)

        return board

    def _create_next_task_hint(self) -> Optional[Text]:
        """Create hint for next task."""
        current = self.tracker.get_current_task()
        if current:
            text = Text()
            text.append(f"{UIIcons.INFO} Próxima: ", style=UIStyles.PRIMARY)
            task_preview = (
                current.text[:60] + "..." if len(current.text) > 60 else current.text
            )
            text.append(task_preview, style="white")
            return text
        return None

    def render(self, console_width: int = 80) -> RenderableType:
        """Renderiza o quadro usando a densidade do terminal."""
        metrics = layout_for_width(console_width)
        self.tracker.refresh()

        categories = self._categorize_tasks()
        self.tracker.get_stats()

        parts = []

        parts.append(self._create_progress_bar(console_width))
        if metrics.vertical_gap:
            parts.append(Text())

        parts.append(self._create_board_table(categories, console_width))
        if metrics.vertical_gap:
            parts.append(Text())

        next_hint = self._create_next_task_hint()
        if next_hint:
            parts.append(next_hint)
            if metrics.vertical_gap:
                parts.append(Text())

        help_text = Text()
        help_text.append(
            "↑↓ navegar · Enter detalhes · Espaço marcar · q sair", style="dim"
        )
        parts.append(help_text)

        title_style = UIStyles.safe_style("TITLE", "cyan")
        project_name = (
            self.tracker.scope.name if self.tracker.scope.name != "." else "Projeto"
        )
        header = Text()
        header.append(f"{UIIcons.TODO} ", style=title_style)
        header.append("Quadro de tarefas", style=f"bold {title_style}")
        header.append(f" {UILayout.METADATA_SEPARATOR} {project_name}", style="dim")
        parts.insert(0, header)

        return Group(*parts)


def display_task_board(tracker: Optional[TodoTracker] = None) -> None:
    """
    Display task board in console.

    Args:
        tracker: TodoTracker instance (creates new if None)
    """
    from aura_cli.cli.ui.display_facade import get_console

    console = get_console()
    board = TaskBoard(tracker)
    console.print(board.render(console_width=console.width))
