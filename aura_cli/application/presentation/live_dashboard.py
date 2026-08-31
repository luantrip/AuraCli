"""Neutral decisions and summaries for live agent dashboards."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import time
from typing import Any, Iterable, Protocol

_PHASE_KEYWORDS = (
    ("starting", ("iniciando", "starting")),
    ("analyzing", ("analisando", "analyzing")),
    ("executing", ("executando", "executing")),
    ("completed", ("concluído", "completed")),
    ("error", ("erro", "error")),
)
_TOOL_KEYWORDS = (
    "read_file",
    "write_file",
    "edit_file",
    "list_directory",
    "git_",
    "docker_",
    "run_shell",
    "analyze_code",
    "codebase_search",
    "glob_search",
    "tree_view",
)


class TaskState(Enum):
    """Task execution states shared by dashboard surfaces."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class DashboardTask:
    """One task tracked by a live dashboard."""

    id: str
    description: str
    state: TaskState = TaskState.PENDING
    progress: float = 0.0
    started_at: float | None = None
    completed_at: float | None = None
    result: str | None = None
    error: str | None = None


@dataclass
class DashboardState:
    """Presentation-neutral mutable state for a live dashboard."""

    mode: str = "AGI"
    status: str = "Inicializando…"
    phase: str = "setup"
    progress: float = 0.0
    tasks: list[DashboardTask] = field(default_factory=list)
    tools_used: list[str] = field(default_factory=list)
    messages: list[dict[str, Any]] = field(default_factory=list)
    start_time: float = field(default_factory=time.time)
    constitution_active: bool = False
    memory_entries: int = 0
    current_tool: str | None = None
    last_update: float = field(default_factory=time.time)

    def set_progress(self, progress: float) -> None:
        self.progress = min(1.0, max(0.0, progress))

    def add_task(self, task_id: str, description: str) -> None:
        self.tasks.append(DashboardTask(task_id, description))

    def update_task(
        self,
        task_id: str,
        *,
        state: TaskState | None = None,
        progress: float | None = None,
        result: str | None = None,
        error: str | None = None,
        timestamp: float | None = None,
    ) -> None:
        task = next((item for item in self.tasks if item.id == task_id), None)
        if task is None:
            return
        if state is not None:
            task.state = state
            if state == TaskState.RUNNING:
                task.started_at = timestamp
            elif state in (TaskState.COMPLETED, TaskState.FAILED):
                task.completed_at = timestamp
        if progress is not None:
            task.progress = min(1.0, max(0.0, progress))
        if result is not None:
            task.result = result
        if error is not None:
            task.error = error

    def add_tool(self, tool_name: str) -> None:
        if tool_name not in self.tools_used:
            self.tools_used.append(tool_name)
        self.current_tool = tool_name

    def add_message(self, message: str, msg_type: str, timestamp: float) -> None:
        self.messages.append({"text": message, "type": msg_type, "time": timestamp})
        self.messages = self.messages[-10:]


@dataclass(frozen=True)
class DashboardMessageDecision:
    """State changes inferred from one worker status message."""

    phase: str | None = None
    completed: bool = False
    tool_name: str | None = None


class DashboardTaskView(Protocol):
    state: Any


def classify_dashboard_message(message: str) -> DashboardMessageDecision:
    """Classify phase, completion and tool hints without mutating UI state."""
    normalized = message.casefold()
    phase = next(
        (
            name
            for name, keywords in _PHASE_KEYWORDS
            if any(k in normalized for k in keywords)
        ),
        None,
    )
    keyword = next((item for item in _TOOL_KEYWORDS if item in normalized), None)
    return DashboardMessageDecision(
        phase=phase,
        completed=phase == "completed",
        tool_name=keyword.replace("_", " ").title() if keyword else None,
    )


def build_dashboard_summary(state: Any, elapsed_seconds: float) -> dict[str, Any]:
    """Build a serializable dashboard summary from a structurally compatible state."""
    tasks: Iterable[DashboardTaskView] = state.tasks
    completed = sum(1 for task in tasks if task.state.value == "completed")
    failed = sum(1 for task in state.tasks if task.state.value == "failed")
    return {
        "mode": state.mode,
        "elapsed_seconds": elapsed_seconds,
        "total_tasks": len(state.tasks),
        "completed_tasks": completed,
        "failed_tasks": failed,
        "tools_used": len(state.tools_used),
        "tools_list": list(state.tools_used),
        "memory_entries": state.memory_entries,
        "constitution_active": state.constitution_active,
        "final_status": state.status,
    }
