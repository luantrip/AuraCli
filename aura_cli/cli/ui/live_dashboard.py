"""
Live Dashboard for AGI and OPS Workers.

This module provides real-time visual dashboards that display during
agent execution, showing progress, tasks, tools used, and metrics.

Features:
    - Real-time progress bars
    - Task list with status
    - Tool usage tracking
    - Memory/context indicators
    - Time elapsed display
    - Live log streaming

Usage:
    >>> from aura_cli.cli.ui.live_dashboard import LiveAgentDashboard
    >>> dashboard = LiveAgentDashboard("AGI", status_queue)
    >>> dashboard.start()
    >>> # ... agent executes ...
    >>> dashboard.stop()
"""

from queue import Empty, Queue
import threading
import time
from typing import Any, Dict, Optional

from rich.console import Console, Group, RenderableType
from rich.live import Live
from rich.padding import Padding
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeElapsedColumn,
)
from rich.table import Table
from rich.text import Text

from aura_cli.application.presentation import (
    DashboardState,
    TaskState,
    build_dashboard_summary,
    classify_dashboard_message,
)
from aura_cli.cli.ui.constants import UIIcons, UIStyles
from aura_cli.cli.ui.display_facade import get_console
from aura_cli.cli.ui.layout_contract import layout_for_width
from aura_cli.core.logger import get_logger

logger = get_logger(__name__)


def _task_state_label(state: TaskState) -> str:
    """Return the stable display label for a task state."""
    labels = {
        TaskState.PENDING: "pendente",
        TaskState.RUNNING: "em andamento",
        TaskState.COMPLETED: "concluída",
        TaskState.FAILED: "falhou",
        TaskState.SKIPPED: "ignorada",
    }
    return labels.get(state, str(state.value))


class LiveAgentDashboard:
    """
    Real-time dashboard for AGI/OPS agent execution.

    Displays a live-updating dashboard showing:
    - Overall progress
    - Current task/tool
    - Task list with states
    - Tools used
    - Time elapsed
    - Recent activity log
    """

    def __init__(
        self,
        mode: str = "AGI",
        status_queue: Optional[Queue] = None,
        console: Optional[Console] = None,
        compact: bool = False,
    ):
        """
        Initialize the live dashboard.

        Args:
            mode: "AGI" or "OPS"
            status_queue: Queue to receive status updates
            console: Rich Console instance
            compact: If True, use compact layout
        """
        self.mode = mode.upper()
        self.status_queue = status_queue or Queue()
        self.console = console if console is not None else get_console()
        self.compact = compact

        self.state = DashboardState(mode=self.mode)
        self._live: Optional[Live] = None
        self._running = False
        self._update_thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()

    def start(self) -> None:
        """Start the live dashboard."""
        self._running = True
        self.state.start_time = time.time()

        self._update_thread = threading.Thread(
            target=self._read_status_queue, daemon=True
        )
        self._update_thread.start()

    def stop(self) -> None:
        """Stop the live dashboard."""
        self._running = False
        if self._update_thread:
            self._update_thread.join(timeout=2.0)

    def update_status(self, status: str, phase: Optional[str] = None) -> None:
        """Update current status message."""
        with self._lock:
            self.state.status = status
            if phase:
                self.state.phase = phase
            self.state.last_update = time.time()

    def update_progress(self, progress: float) -> None:
        """Update overall progress (0.0 to 1.0)."""
        with self._lock:
            self.state.set_progress(progress)

    def add_task(self, task_id: str, description: str) -> None:
        """Add a new task to the dashboard."""
        with self._lock:
            self.state.add_task(task_id, description)

    def update_task(
        self,
        task_id: str,
        state: Optional[TaskState] = None,
        progress: Optional[float] = None,
        result: Optional[str] = None,
        error: Optional[str] = None,
    ) -> None:
        """Update a task's state."""
        with self._lock:
            self.state.update_task(
                task_id,
                state=state,
                progress=progress,
                result=result,
                error=error,
                timestamp=time.time(),
            )

    def add_tool(self, tool_name: str) -> None:
        """Record a tool being used."""
        with self._lock:
            self.state.add_tool(tool_name)

    def add_message(self, message: str, msg_type: str = "info") -> None:
        """Add a message to the activity log."""
        with self._lock:
            self.state.add_message(message, msg_type, time.time())

    def set_constitution_active(self, active: bool) -> None:
        """Set whether constitution is active."""
        with self._lock:
            self.state.constitution_active = active

    def set_memory_entries(self, count: int) -> None:
        """Set memory entry count."""
        with self._lock:
            self.state.memory_entries = count

    def _read_status_queue(self) -> None:
        """Background thread to read status queue updates."""
        while self._running:
            try:
                message = self.status_queue.get(timeout=min(0.1, 5.0))
                self._process_queue_message(message)
            except Empty:
                continue
            except Exception as error:
                logger.debug(f"Dashboard status message ignored: {error}")

    def _process_queue_message(self, message: str) -> None:
        """Process a message from the status queue."""
        decision = classify_dashboard_message(message)
        if decision.phase:
            self.update_status(message, decision.phase)
        if decision.completed:
            self.update_progress(1.0)
        if decision.tool_name:
            self.add_tool(decision.tool_name)
        self.add_message(message)

    def render(self, console_width: Optional[int] = None) -> RenderableType:
        """Renderiza o dashboard usando a largura real do console."""
        width = console_width if console_width is not None else self.console.width
        metrics = layout_for_width(width)
        with self._lock:
            state = self.state

        elapsed = time.time() - state.start_time

        content_parts: list[Any] = []

        header = self._render_header(state, elapsed)
        content_parts.append(header)
        if metrics.vertical_gap:
            content_parts.append(Text())

        progress_bar = self._render_progress(state, console_width=metrics.width)
        content_parts.append(progress_bar)
        if metrics.vertical_gap:
            content_parts.append(Text())

        if not self.compact and not metrics.narrow:
            if state.tasks:
                tasks_panel = self._render_tasks(state, console_width=metrics.width)
                content_parts.append(tasks_panel)
                if metrics.vertical_gap:
                    content_parts.append(Text())

            if state.tools_used:
                tools_panel = self._render_tools(state)
                content_parts.append(tools_panel)
                if metrics.vertical_gap:
                    content_parts.append(Text())

        log_panel = self._render_log(state)
        content_parts.append(log_panel)

        footer = self._render_footer(state, elapsed)
        if metrics.vertical_gap:
            content_parts.append(Text())
        content_parts.append(footer)

        mode_icon = UIIcons.AGI if state.mode == "AGI" else UIIcons.OPS
        mode_color = UIStyles.PRIMARY if state.mode == "AGI" else UIStyles.ACCENT
        header_line = Text(
            f"{mode_icon} Dashboard Aura {state.mode}",
            style=f"bold {mode_color}",
        )
        content_parts.insert(0, header_line)

        return Padding(
            Group(*content_parts),
            metrics.focus_padding if not metrics.narrow else metrics.group_padding,
        )

    def _render_header(self, state: DashboardState, elapsed: float) -> Text:
        """Render the header section."""
        header = Text()

        phase_icons = {
            "setup": UIIcons.LOADING,
            "starting": UIIcons.LOADING,
            "analyzing": UIIcons.THINKING,
            "planning": UIIcons.THINKING,
            "executing": UIIcons.WORKING,
            "completed": UIIcons.SUCCESS,
            "error": UIIcons.ERROR,
        }
        icon = phase_icons.get(state.phase, UIIcons.LOADING)

        header.append(f"{icon} ", style=UIStyles.PRIMARY)
        header.append("Estado: ", style=UIStyles.LABEL)
        header.append(f"{state.status}\n", style=UIStyles.BODY)

        if state.current_tool:
            header.append(f"{UIIcons.TOOL} ", style=UIStyles.ACCENT)
            header.append("Atual: ", style=UIStyles.LABEL)
            header.append(f"{state.current_tool}\n", style=UIStyles.INFO)

        if state.constitution_active:
            header.append("◇ ", style=UIStyles.SUCCESS)
            header.append("Constituição: ", style=UIStyles.LABEL)
            header.append("ativa\n", style=UIStyles.SUCCESS)

        return header

    def _render_progress(
        self, state: DashboardState, console_width: int = 80
    ) -> Progress:
        """Render a proportional progress bar."""
        progress = Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(
                bar_width=min(
                    40, max(12, layout_for_width(console_width).content_width // 5)
                )
            ),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeElapsedColumn(),
        )

        progress.add_task(
            f"[{UIStyles.PRIMARY}]Processando…",
            total=100,
            completed=int(state.progress * 100),
        )

        return progress

    def _render_tasks(self, state: DashboardState, console_width: int = 80) -> Table:
        """Render task list."""
        table = Table(
            show_header=True,
            header_style=UIStyles.SUBTITLE,
            border_style=UIStyles.BORDER_MUTED,
            expand=True,
            box=None,
        )

        table.add_column("", width=3)
        table.add_column("Tarefa", ratio=3)
        table.add_column("Estado", width=12)
        table.add_column("Tempo", width=8)

        state_icons = {
            TaskState.PENDING: (UIIcons.IDLE, UIStyles.MUTED),
            TaskState.RUNNING: (UIIcons.LOADING, UIStyles.INFO),
            TaskState.COMPLETED: (UIIcons.SUCCESS, UIStyles.SUCCESS),
            TaskState.FAILED: (UIIcons.ERROR, UIStyles.ERROR),
            TaskState.SKIPPED: (UIIcons.CANCEL, UIStyles.MUTED),
        }

        for task in state.tasks[-5:]:  # Show last 5 tasks
            icon, style = state_icons.get(task.state, ("?", UIStyles.MUTED))

            if task.completed_at and task.started_at:
                task_time = f"{task.completed_at - task.started_at:.1f}s"
            elif task.started_at:
                task_time = f"{time.time() - task.started_at:.1f}s"
            else:
                task_time = "—"

            table.add_row(
                f"[{style}]{icon}[/]",
                f"[{UIStyles.BODY}]{task.description[:40]}[/]",
                f"[{style}]{_task_state_label(task.state)}[/]",
                f"[{UIStyles.MUTED}]{task_time}[/]",
            )

        table.title = f"Tarefas ({len(state.tasks)})"
        return table

    def _render_tools(self, state: DashboardState) -> Group:
        """Render tools used section."""
        tools_text = Text()

        for i, tool in enumerate(state.tools_used[-8:]):  # Last 8 tools
            if i > 0:
                tools_text.append(" • ", style=UIStyles.MUTED)
            tools_text.append(f"{UIIcons.TOOL} ", style=UIStyles.ACCENT)
            tools_text.append(tool, style=UIStyles.BODY)

        return Group(
            Text(f"Operações ({len(state.tools_used)})", style=UIStyles.LABEL),
            tools_text,
        )

    def _render_log(self, state: DashboardState) -> Group:
        """Render activity log."""
        log_lines = []

        for msg in state.messages[-5:]:  # Last 5 messages
            elapsed = time.time() - msg["time"]
            time_str = (
                f"há {elapsed:.0f}s" if elapsed < 60 else f"há {elapsed / 60:.0f}min"
            )

            type_styles = {
                "info": UIStyles.INFO,
                "success": UIStyles.SUCCESS,
                "warning": UIStyles.WARNING,
                "error": UIStyles.ERROR,
            }
            style = type_styles.get(msg["type"], UIStyles.MUTED)

            line = Text()
            line.append(f"[{UIStyles.MUTED}]{time_str:<8}[/] ")

            text = msg["text"]
            if len(text) > 60:
                text = text[:57] + "..."
            line.append(f"[{style}]{text}[/]")

            log_lines.append(line)

        if not log_lines:
            log_lines.append(Text("Aguardando atividade…", style=UIStyles.MUTED))

        return Group(Text("Atividade", style=UIStyles.LABEL), *log_lines)

    def _render_footer(self, state: DashboardState, elapsed: float) -> Text:
        """Render footer with metrics."""
        footer = Text()

        minutes = int(elapsed // 60)
        seconds = int(elapsed % 60)
        time_str = f"{minutes}m {seconds}s" if minutes > 0 else f"{seconds}s"

        footer.append(f"{UIIcons.TIMER} ", style=UIStyles.WARNING)
        footer.append("Tempo: ", style=UIStyles.LABEL)
        footer.append(f"{time_str} ", style=UIStyles.BODY)

        footer.append(" │ ", style=UIStyles.MUTED)

        completed = sum(1 for t in state.tasks if t.state == TaskState.COMPLETED)
        footer.append(f"{UIIcons.SUCCESS} ", style=UIStyles.SUCCESS)
        footer.append("Tarefas: ", style=UIStyles.LABEL)
        footer.append(f"{completed}/{len(state.tasks)} ", style=UIStyles.BODY)

        footer.append(" │ ", style=UIStyles.MUTED)

        footer.append(f"{UIIcons.TOOL} ", style=UIStyles.ACCENT)
        footer.append("Ferramentas: ", style=UIStyles.LABEL)
        footer.append(f"{len(state.tools_used)} ", style=UIStyles.BODY)

        if state.memory_entries > 0:
            footer.append(" │ ", style=UIStyles.MUTED)
            footer.append("◇ ", style=UIStyles.INFO)
            footer.append("Memória: ", style=UIStyles.LABEL)
            footer.append(f"{state.memory_entries}", style=UIStyles.BODY)

        return footer

    def run_live(self, refresh_rate: float = 0.5) -> None:
        """
        Run the dashboard with live updates.

        Args:
            refresh_rate: How often to refresh (seconds)
        """
        self.start()

        try:
            with Live(
                self.render(),
                console=self.console,
                refresh_per_second=1 / refresh_rate,
                screen=False,
                transient=True,
            ) as live:
                while self._running:
                    live.update(self.render())
                    time.sleep(refresh_rate)
        finally:
            self.stop()

    def get_summary(self) -> Dict[str, Any]:
        """Get summary of dashboard state."""
        with self._lock:
            elapsed = time.time() - self.state.start_time
            return build_dashboard_summary(self.state, elapsed)


def create_mini_dashboard(
    mode: str,
    status: str,
    progress: float,
    tools_count: int,
    elapsed: float,
) -> Panel:
    """
    Create a compact mini-dashboard for inline display.

    Args:
        mode: "AGI" or "OPS"
        status: Current status message
        progress: Progress (0.0 to 1.0)
        tools_count: Number of tools used
        elapsed: Elapsed time in seconds

    Returns:
        Rich Panel with mini dashboard
    """
    mode = mode.upper()
    progress = min(1.0, max(0.0, progress))
    mode_icon = UIIcons.AGI if mode == "AGI" else UIIcons.OPS
    mode_color = UIStyles.PRIMARY if mode == "AGI" else UIStyles.ACCENT

    bar_width = 20
    filled = int(progress * bar_width)
    empty = bar_width - filled
    progress_bar = "█" * filled + "░" * empty

    content = Text()
    content.append(f"{mode_icon} ", style=mode_color)
    content.append(f"[{progress_bar}] ", style=UIStyles.INFO)
    content.append(f"{int(progress * 100)}% ", style=UIStyles.PRIMARY)
    content.append(f"│ {UIIcons.TOOL} {tools_count} ", style=UIStyles.ACCENT)
    content.append(f"│ {UIIcons.TIMER} {elapsed:.0f}s", style=UIStyles.WARNING)

    return Panel(
        content,
        title=f"[{mode_color}]{status[:40]}[/{mode_color}]",
        border_style=UIStyles.BORDER_MUTED,
        padding=(0, 1),
    )
