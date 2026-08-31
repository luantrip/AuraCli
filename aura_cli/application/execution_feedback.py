"""Presentation-neutral execution feedback contracts."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import time
from typing import Any, Callable, Optional


class LoadingState(Enum):
    """Lifecycle states emitted by long-running application operations."""

    IDLE = "idle"
    PREPARING = "preparing"
    EXECUTING = "executing"
    PROCESSING = "processing"
    ANALYZING = "analyzing"
    THINKING = "thinking"
    STREAMING = "streaming"
    FINALIZING = "finalizing"
    COMPLETE = "complete"
    ERROR = "error"


class LoadingCategory(Enum):
    """Portable categories for long-running operations."""

    LLM = "llm"
    TOOL = "tool"
    FILE = "file"
    AGENT = "agent"
    BACKGROUND = "background"
    SYSTEM = "system"


def resolve_file_loading(operation: str) -> str:
    """Normalize a file loading operation to a known intent."""
    normalized = operation.casefold()
    return normalized if normalized in {"read", "write", "analyze"} else "custom"


def resolve_agent_loading(action: str) -> str:
    """Normalize an agent action to thinking, planning or executing."""
    normalized = action.casefold()
    if "thinking" in normalized:
        return "thinking"
    if "planning" in normalized:
        return "planning"
    return "executing"


class NullLoadingHandle:
    """Headless loading handle implementing the adapter's operational surface."""

    def update(self, state: LoadingState, details: Optional[str] = None) -> None:
        pass

    def complete(self, result: Optional[str] = None) -> None:
        pass

    def error(self, error_msg: str) -> None:
        pass


class ShellExecutionState(Enum):
    """Presentation-neutral shell execution lifecycle."""

    PENDING = "pending"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class ShellExecutionView:
    """State exposed by the shell engine to optional presentation adapters."""

    command: str
    background: bool = False
    state: ShellExecutionState = ShellExecutionState.PENDING
    output_lines: list[str] = field(default_factory=list)
    stderr_lines: list[str] = field(default_factory=list)
    exit_code: Optional[int] = None
    execution_time: Optional[float] = None
    start_time: Optional[float] = None

    def start(self) -> None:
        self.state = ShellExecutionState.EXECUTING
        self.start_time = time.time()

    def finish(self, exit_code: int) -> None:
        self.exit_code = exit_code
        self.execution_time = time.time() - self.start_time if self.start_time else 0
        self.state = (
            ShellExecutionState.COMPLETED
            if exit_code == 0
            else ShellExecutionState.FAILED
        )

    def cancel(self) -> None:
        self.state = ShellExecutionState.CANCELLED


_llm_loading_factory: Optional[Callable[[Any, str], Any]] = None
_tool_loading_factory: Optional[Callable[[Any, str, dict[str, Any]], Any]] = None
_file_edit_presenter: Optional[Callable[..., None]] = None
_shell_presenter: Optional[Callable[[Any, ShellExecutionView], None]] = None


def configure_loading_feedback(
    *,
    llm_factory: Optional[Callable[[Any, str], Any]] = None,
    tool_factory: Optional[Callable[[Any, str, dict[str, Any]], Any]] = None,
) -> None:
    """Register loading factories supplied by a presentation adapter."""
    global _llm_loading_factory, _tool_loading_factory
    if llm_factory is not None:
        _llm_loading_factory = llm_factory
    if tool_factory is not None:
        _tool_loading_factory = tool_factory


def configure_file_edit_presenter(
    presenter: Optional[Callable[..., None]],
) -> None:
    """Register the host presenter for file diffs."""
    global _file_edit_presenter
    _file_edit_presenter = presenter


def configure_shell_presenter(
    presenter: Optional[Callable[[Any, ShellExecutionView], None]],
) -> None:
    """Register the host renderer for shell execution state."""
    global _shell_presenter
    _shell_presenter = presenter


def show_llm_feedback(console: Any, model: str) -> Any:
    """Create host feedback for an LLM call, or a headless no-op handle."""
    if _llm_loading_factory is None:
        return NullLoadingHandle()
    return _llm_loading_factory(console, model)


def show_tool_feedback(console: Any, tool_name: str, params: dict[str, Any]) -> Any:
    """Create host feedback for a tool call, or a headless no-op handle."""
    if _tool_loading_factory is None:
        return NullLoadingHandle()
    return _tool_loading_factory(console, tool_name, params)


def present_file_edit(*args: Any, **kwargs: Any) -> None:
    """Present a file diff when a host adapter has been configured."""
    if _file_edit_presenter is not None:
        _file_edit_presenter(*args, **kwargs)


def present_shell_feedback(console: Any, execution: ShellExecutionView) -> None:
    """Render shell state when a host adapter is configured."""
    if _shell_presenter is not None:
        _shell_presenter(console, execution)
