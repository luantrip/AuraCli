"""Visual to-do list display for Aura CLI.

Renders tasks from TodoTracker as Rich tables, panels and progress bars.
Differentiates tasks by status (pending/working/done). Primary entry points:
display_todo_list() and create_todo_panel().
"""

from typing import Optional

from rich.console import Group, RenderableType
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    Progress,
    TextColumn,
)
from rich.table import Table
from rich.text import Text

from aura_cli.cli.ui.constants import UIIcons, UIStyles
from aura_cli.cli.ui.display_facade import get_console
from aura_cli.cli.ui.strings import UIStrings
from aura_cli.cli.ui.theme_manager import get_theme_manager
from aura_cli.core.logger import get_logger
from aura_cli.core.todo.todo_tracker import TodoTracker, get_todo_tracker

from .responsive import get_terminal_size

logger = get_logger(__name__)
console = get_console()


def format_todo_summary(tracker: TodoTracker) -> str:
    """Return a compact one-line task summary with icons and counts.

    Args:
        tracker: Loaded TodoTracker instance.

    Returns:
        Formatted string, e.g. "⬢ To-do Working on 3 to-do * 5 done".
    """
    stats = tracker.get_stats()

    working = stats["working"]
    done = stats["done"]
    pending = stats["pending"]

    if pending > 0:
        summary = f"{UIIcons.WORKING} To-do {UIStrings.working_on_tasks(working)}"
        if done > 0:
            summary += f" {UIIcons.BULLET} {UIStrings.tasks_completed(done)}"
    else:
        summary = f"{UIIcons.SUCCESS} To-do {UIStrings.ALL_DONE} {UIIcons.BULLET} {UIStrings.tasks_completed(done)}"

    return summary


def create_progress_bar(tracker: TodoTracker, width: int = 30) -> Progress:
    """Create a Rich Progress bar for the current task counts.

    Args:
        tracker: TodoTracker with current statistics.
        width: Bar width in characters (default 30).

    Returns:
        Renderable Rich Progress instance.
    """
    stats = tracker.get_stats()
    width = max(8, int(width))
    total = stats["total"]
    done = stats["done"]

    if total == 0:
        progress = Progress(
            TextColumn("[progress.description]{task.description}"),
            BarColumn(bar_width=width),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        )
        task = progress.add_task("Nenhuma tarefa", total=100)
        progress.update(task, completed=0)
        return progress

    progress = Progress(
        TextColumn("[progress.description]{task.description}"),
        BarColumn(bar_width=width),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TextColumn(f"({done}/{total})"),
    )

    with progress:
        task = progress.add_task("Progresso", total=total)
        progress.update(task, completed=done)

    return progress


def create_todo_panel(
    tracker: Optional[TodoTracker] = None,
    max_tasks: int = 10,
    highlight_current: bool = True,
) -> RenderableType:
    """Create a Rich panel with the task list and progress summary.

    Renders a status summary, progress bar, pending tasks (with optional
    [CURRENT] highlight) and completed tasks. Caps display at max_tasks
    with a remaining-count indicator.

    Args:
        tracker: TodoTracker instance; creates a new one if None.
        max_tasks: Maximum tasks to display (default 10).
        highlight_current: Highlight the current task with [CURRENT] (default True).

    Returns:
        Rich Panel with title "To-do List" and cyan border.
    """
    if tracker is None:
        tracker = get_todo_tracker()

    stats = tracker.get_stats()

    if stats["total"] == 0:
        text = Text()
        text.append(f"{UIIcons.WORKING} To-do", style=UIStyles.TITLE)
        text.append(" Nenhuma tarefa", style=UIStyles.MUTED)
        return Group(
            Text("Lista de tarefas", style=f"bold {UIStyles.TITLE}"),
            text,
        )

    text = Text()

    summary = format_todo_summary(tracker)
    text.append(summary, style=f"{UIStyles.PRIMARY} bold")
    text.append("\n")

    progress_bar = create_progress_bar(tracker)
    # Progress cannot be appended to Text — use Group to combine them
    text.append("\n")

    all_tasks = tracker.get_all_tasks()
    pending_tasks = [t for t in all_tasks if t.is_pending]
    done_tasks = [t for t in all_tasks if t.is_done]

    current_task = tracker.get_current_task()

    tasks_to_show = pending_tasks[:max_tasks]
    remaining_pending = len(pending_tasks) - len(tasks_to_show)

    for task in tasks_to_show:
        if highlight_current and current_task and task.id == current_task.id:
            text.append(f"{UIIcons.WORKING} ", style=UIStyles.WARNING + " bold")
            text.append(f"{UIIcons.ARROW} ", style=UIStyles.PRIMARY + " bold")
            text.append(task.text, style=UIStyles.PRIMARY + " bold")
            text.append(" · atual", style=UIStyles.MUTED)
        else:
            text.append(f"{UIIcons.THINKING} ", style=UIStyles.WARNING)
            text.append(task.text, style=UIStyles.BODY)
        text.append("\n")

    if remaining_pending > 0:
        text.append(f"… e mais {remaining_pending} tarefas pendentes\n", style="dim")

    if done_tasks and len(tasks_to_show) < max_tasks:
        remaining_slots = max_tasks - len(tasks_to_show)
        if remaining_slots > 0:
            if len(tasks_to_show) > 0:
                text.append("\n")
            text.append("Concluídas:\n", style="dim")
            for task in done_tasks[:remaining_slots]:
                text.append(f"{UIIcons.SUCCESS} ", style=UIStyles.SUCCESS)
                text.append(task.text, style=UIStyles.MUTED)
                text.append("\n")

            if len(done_tasks) > remaining_slots:
                text.append(
                    f"... e mais {len(done_tasks) - remaining_slots} concluídas\n",
                    style="dim",
                )

    return Group(
        Text("Lista de tarefas", style="bold bright_cyan"),
        text,
        progress_bar,
    )


def create_todo_compact(tracker: Optional[TodoTracker] = None) -> str:
    """Return a single-line compact to-do string for footers / status bars.

    Truncates the current task text at 40 characters.

    Args:
        tracker: TodoTracker instance; creates a new one if None.

    Returns:
        Compact string, e.g. "⬢ To-do Working on: Fix bug... * 3 done".
    """
    if tracker is None:
        tracker = get_todo_tracker()

    stats = tracker.get_stats()

    if stats["total"] == 0:
        return f"{UIIcons.WORKING} To-do Sem tarefas"

    done = stats["done"]
    pending = stats["pending"]

    if pending > 0:
        current_task = tracker.get_current_task()
        if current_task:
            task_preview = (
                current_task.text[:40] + "..."
                if len(current_task.text) > 40
                else current_task.text
            )
            return f"{UIIcons.WORKING} To-do {UIStrings.WORKING_ON}: {task_preview} {UIIcons.BULLET} {UIStrings.tasks_completed(done)}"
        else:
            return f"{UIIcons.WORKING} To-do {UIStrings.tasks_pending(pending)} {UIIcons.BULLET} {UIStrings.tasks_completed(done)}"
    else:
        return f"{UIIcons.SUCCESS} To-do {UIStrings.ALL_DONE} {UIIcons.BULLET} {UIStrings.tasks_completed(done)}"


def display_todo_list(
    tracker: Optional[TodoTracker] = None,
    max_tasks: int = 10,
    highlight_current: bool = True,
) -> None:
    """Print the formatted task panel to the console.

    Args:
        tracker: TodoTracker instance; creates a new one if None.
        max_tasks: Maximum tasks to display (default 10).
        highlight_current: Highlight the current task (default True).
    """
    panel = create_todo_panel(tracker, max_tasks, highlight_current)
    console.print(panel)


def create_todo_table(
    tracker: Optional[TodoTracker] = None, highlight_current: bool = True
) -> Table:
    """Create a Rich Table with all tasks in tabular format.

    Columns: Status (icon) and Task (text). Pending tasks in yellow,
    completed in dim green. Current task highlighted with [CURRENT].

    Args:
        tracker: TodoTracker instance; creates a new one if None.
        highlight_current: Highlight the current task (default True).

    Returns:
        Rich Table with title "To-do List" and responsive width.
    """
    if tracker is None:
        tracker = get_todo_tracker()

    theme = get_theme_manager()
    table = Table(
        title=f"[{UIStyles.TITLE}]Lista de tarefas[/{UIStyles.TITLE}]",
        show_header=True,
        header_style=UIStyles.TITLE,
        width=get_terminal_size()[0],
    )
    table.add_column("Status", style=theme.get_style("primary"), width=8)
    table.add_column("Tarefa", style=theme.get_style("body"), ratio=1)

    all_tasks = tracker.get_all_tasks()
    current_task = tracker.get_current_task()

    for task in all_tasks:
        if task.is_pending:
            status = UIIcons.THINKING
            style = UIStyles.WARNING
            if highlight_current and current_task and task.id == current_task.id:
                status = f"{UIIcons.WORKING} {UIIcons.ARROW}"
                style = UIStyles.WARNING + " bold"
                task_text = f"[{UIStyles.PRIMARY} bold]{task.text}[/{UIStyles.PRIMARY} bold] [{UIStyles.MUTED}]{UIStrings.CURRENT}[/{UIStyles.MUTED}]"
            else:
                task_text = task.text
        else:
            status = UIIcons.SUCCESS
            style = UIStyles.SUCCESS
            task_text = f"[{UIStyles.MUTED}]{task.text}[/{UIStyles.MUTED}]"

        table.add_row(f"[{style}]{status}[/{style}]", task_text)

    return table


def get_todo_status_line(
    tracker: Optional[TodoTracker] = None, compact: bool = True
) -> str:
    """Return a Rich-markup status line for footers.

    Compact mode shows counts only; expanded mode includes the current
    task preview (truncated at 25 chars) and completion percentage.

    Args:
        tracker: TodoTracker instance; creates a new one if None.
        compact: Return the shorter count-only variant (default True).

    Returns:
        Rich-markup string suitable for footer display.
    """
    if tracker is None:
        tracker = get_todo_tracker()

    stats = tracker.get_stats()

    if stats["total"] == 0:
        return f"[{UIStyles.PRIMARY}]{UIIcons.WORKING} To-do[/{UIStyles.PRIMARY}] [{UIStyles.MUTED}]Sem tarefas[/{UIStyles.MUTED}]"

    done = stats["done"]
    pending = stats["pending"]
    total = stats["total"]

    percentage = int(done / total * 100) if total > 0 else 0

    # Helper to ensure valid values
    def safe_style(style, fallback="white"):
        """Return a style string safely, never None."""
        return style if style is not None else fallback

    primary = safe_style(UIStyles.PRIMARY, "cyan")
    warning = safe_style(UIStyles.WARNING, "yellow")
    muted = safe_style(UIStyles.MUTED, "dim white")
    success = safe_style(UIStyles.SUCCESS, "green")

    if compact:
        if pending > 0:
            return f"[{primary}]{UIIcons.WORKING} To-do[/{primary}] [{warning}]{UIStrings.tasks_pending(pending)}[/{warning}] [{muted}]{UIIcons.BULLET}[/{muted}] [{success}]{UIStrings.tasks_completed(done)}[/{success}]"
        else:
            return f"[{primary}]{UIIcons.SUCCESS} To-do {UIStrings.ALL_DONE}[/{primary}] [{muted}]{UIIcons.BULLET}[/{muted}] [{success}]{done}/{total}[/{success}]"
    else:
        if pending > 0:
            current_task = tracker.get_current_task()
            if current_task:
                task_preview = (
                    current_task.text[:25] + "..."
                    if len(current_task.text) > 25
                    else current_task.text
                )
                return f"[{primary}]{UIIcons.WORKING} To-do[/{primary}] [{warning}]-> {task_preview}[/{warning}] [{muted}]{UIIcons.BULLET}[/{muted}] [{success}]{done}/{total} ({percentage}%)[/{success}]"
            else:
                return f"[{primary}]{UIIcons.WORKING} To-do[/{primary}] [{warning}]{UIStrings.tasks_pending(pending)}[/{warning}] [{muted}]{UIIcons.BULLET}[/{muted}] [{success}]{done}/{total} ({percentage}%)[/{success}]"
        else:
            return f"[{primary}]{UIIcons.SUCCESS} To-do {UIStrings.ALL_DONE}[/{primary}] [{muted}]{UIIcons.BULLET}[/{muted}] [{success}]{done}/{total} (100%)[/{success}]"


def update_todo_display(tracker: Optional[TodoTracker] = None) -> None:
    """Refresh the tracker from disk and reprint the task list.

    Args:
        tracker: TodoTracker instance; creates a new one if None.
    """
    if tracker is None:
        tracker = get_todo_tracker()

    tracker.refresh()
    display_todo_list(tracker)


def notify_task_completed(
    task_text: str, tracker: Optional[TodoTracker] = None
) -> None:
    """Display a visual celebration panel for a completed task.

    Prints a green panel with the task name followed by a progress line
    (X/Y tasks, percentage).

    Args:
        task_text: Text of the completed task.
        tracker: TodoTracker instance; creates a new one if None.
    """
    if tracker is None:
        tracker = get_todo_tracker()

    theme = get_theme_manager()
    notification = Panel(
        f"[{UIStyles.SUCCESS}]{UIIcons.SUCCESS} {UIStrings.TASK_COMPLETED}:[/{UIStyles.SUCCESS}] [{theme.get_style('body')}]{task_text}[/{theme.get_style('body')}]",
        border_style=UIStyles.BORDER_SUCCESS,
        padding=(1, 2),
        expand=False,
        width=get_terminal_size()[0],
    )
    console.print(notification)

    stats = tracker.get_stats()
    total = stats["total"]
    done = stats["done"]
    percentage = int(done / total * 100) if total > 0 else 0

    console.print(
        f"[{UIStyles.MUTED}]{UIStrings.PROGRESS}: {done}/{total} {UIStrings.TASKS} ({percentage}%)[/{UIStyles.MUTED}]\n"
    )


def create_todo_summary_panel(tracker: Optional[TodoTracker] = None) -> Panel:
    """Create a compact summary panel with aggregated statistics.

    Shows total/pending/done counts, a 40-char progress bar and the
    current task preview. Suitable for dashboards and high-level views.

    Args:
        tracker: TodoTracker instance; creates a new one if None.

    Returns:
        Rich Panel titled "Task summary".
    """
    if tracker is None:
        tracker = get_todo_tracker()

    stats = tracker.get_stats()
    total = stats["total"]
    pending = stats["pending"]
    done = stats["done"]

    theme = get_theme_manager()
    text = Text()
    text.append(f"{UIIcons.WORKING} To-do", style=UIStyles.TITLE)
    text.append("\n\n")

    text.append(f"Total: {total}  ", style=UIStyles.BODY)
    text.append(f"Pendentes: {pending}  ", style=theme.get_color("warning"))
    text.append(f"Concluídas: {done}", style=theme.get_color("success"))
    text.append("\n\n")

    progress_bar = create_progress_bar(tracker, width=40)

    current_task = tracker.get_current_task()
    if current_task:
        text.append("\n\n")
        text.append("Atual: ", style=UIStyles.MUTED)
        text.append(current_task.text, style=f"{UIStyles.PRIMARY} bold")

    return Panel(
        Group(text, progress_bar),
        title=f"[{UIStyles.TITLE}]Resumo de tarefas[/{UIStyles.TITLE}]",
        border_style=UIStyles.BORDER_PRIMARY,
        padding=(1, 2),
        expand=False,
    )
