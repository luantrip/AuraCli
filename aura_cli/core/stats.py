"""Session statistics tracker for Aura CLI — singleton via get_stats().

Tracks tokens (total/prompt/completion per model), files read/edited/created,
shell command history and timing, per-tool usage counters, and session state
(idle/running/thinking). All callers share one StatsTracker instance.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from aura_cli.application.execution import TurnExecution


class _SafeStatusContext:
    """Context manager that sets a status on enter and resets to idle on exit.

    Ensures ``reset_to_idle()`` is always called, even when an exception
    escapes the body — preventing the UI from being stuck in 'thinking'.

    Supports both sync (``with``) and async (``async with``) usage.
    """

    def __init__(self, stats: StatsTracker, status: str, message: str = "") -> None:
        self._stats = stats
        self._status = status
        self._message = message

    def __enter__(self) -> StatsTracker:
        self._stats.set_status(self._status, self._message)
        return self._stats

    def __exit__(self, *_: object) -> None:
        self._stats.reset_to_idle()

    async def __aenter__(self) -> StatsTracker:
        self._stats.set_status(self._status, self._message)
        return self._stats

    async def __aexit__(self, *_: object) -> None:
        self._stats.reset_to_idle()


class StatsTracker:
    """
    Statistics tracker for Aura CLI.
    Monitors tokens, files, commands and session status.
    """

    def __init__(self):
        """Initialize all counters and tracking structures to zero."""
        self.tokens_used = 0
        self.prompt_tokens = 0
        self.completion_tokens = 0
        self.tokens_by_model: Dict[str, Dict[str, int]] = defaultdict(
            lambda: {"total_tokens": 0, "prompt_tokens": 0, "completion_tokens": 0}
        )
        self._budget_warning_emitted = False

        self.files_edited = 0
        self.files_created = 0
        self.files_read = 0
        self.files_by_type = defaultdict(int)

        self.shell_commands_run = 0
        self.shell_command_total_time = 0.0
        self.shell_commands_history = []

        self.current_status = "idle"
        self.status_message = ""

        self.skip_confirmations = False

        self.notification_message: Optional[str] = None
        self.notification_expires_at: Optional[datetime] = None

        self.edit_percentage = 0.0

        self.current_model = ""

        self.session_start = datetime.now()
        self.last_activity = datetime.now()

        self.tools_used = defaultdict(int)
        self._last_tool_used = "none"

        self._files_read_list = []
        self._files_edited_list = []
        self._files_created_list = []

        self.notebook_snapshots = 0
        self.notebook_pages_read = 0
        self._active_turn_execution: Optional[TurnExecution] = None
        self.turn_tokens = 0
        self.context_tokens = 0
        self.session_tokens = 0

    def bind_turn_execution(self, turn: Optional[TurnExecution]) -> None:
        """Bind the canonical source for per-turn operational projections."""
        self._active_turn_execution = turn
        self.turn_tokens = 0

    def update_last_activity(self) -> None:
        """Record activity through the public observability contract."""
        self.last_activity = datetime.now()

    def get_turn_files(self) -> dict[str, list[str]]:
        """Project file activity from the ledger, with a legacy fallback."""
        if self._active_turn_execution is not None:
            return {
                "read": self._active_turn_execution.files_read,
                "created": self._active_turn_execution.files_created,
                "edited": self._active_turn_execution.files_edited,
            }
        return {
            "read": list(self._files_read_list),
            "created": list(self._files_created_list),
            "edited": list(self._files_edited_list),
        }

    @property
    def total_tokens(self) -> int:
        """Total tokens used this session."""
        return self.tokens_used

    def add_tokens(self, usage: Dict, model: Optional[str] = None) -> None:
        """Accumulate token usage from an LLM response.

        Args:
            usage: Dict or object with prompt_tokens, completion_tokens, total_tokens.
            model: Optional model name for per-model tracking.
        """
        if isinstance(usage, dict):
            prompt = usage.get("prompt_tokens", 0)
            completion = usage.get("completion_tokens", 0)
            total = usage.get("total_tokens", 0)
            self.prompt_tokens += prompt
            self.completion_tokens += completion
            self.tokens_used += total
            self.turn_tokens += total
            self.session_tokens += total
            if model:
                self.tokens_by_model[model]["total_tokens"] += total
                self.tokens_by_model[model]["prompt_tokens"] += prompt
                self.tokens_by_model[model]["completion_tokens"] += completion
        elif hasattr(usage, "total_tokens"):
            prompt = getattr(usage, "prompt_tokens", 0)
            completion = getattr(usage, "completion_tokens", 0)
            total = getattr(usage, "total_tokens", 0)
            self.prompt_tokens += prompt
            self.completion_tokens += completion
            self.tokens_used += total
            self.turn_tokens += total
            self.session_tokens += total
            if model:
                self.tokens_by_model[model]["total_tokens"] += total
                self.tokens_by_model[model]["prompt_tokens"] += prompt
                self.tokens_by_model[model]["completion_tokens"] += completion

        self.last_activity = datetime.now()

    def increment_files_edited(self, file_path: Optional[str] = None) -> None:
        """Increment the edited-files counter.

        Args:
            file_path: Optional file path for per-extension tracking.
        """
        self.files_edited += 1
        if file_path:
            ext = file_path.split(".")[-1] if "." in file_path else "no_ext"
            self.files_by_type[ext] += 1
            if file_path not in self._files_edited_list:
                self._files_edited_list.append(file_path)
        self.last_activity = datetime.now()

    def increment_files_created(self, file_path: Optional[str] = None) -> None:
        """Increment the created-files counter.

        Args:
            file_path: Optional file path for per-extension tracking.
        """
        self.files_created += 1
        if file_path:
            ext = file_path.split(".")[-1] if "." in file_path else "no_ext"
            self.files_by_type[ext] += 1
            if file_path not in self._files_created_list:
                self._files_created_list.append(file_path)
        self.last_activity = datetime.now()

    def increment_files_read(self, file_path: Optional[str] = None) -> None:
        """Increment the read-files counter.

        Args:
            file_path: Optional file path tracked in the read list.
        """
        self.files_read += 1
        if file_path and file_path not in self._files_read_list:
            self._files_read_list.append(file_path)
        self.last_activity = datetime.now()

    def add_shell_command(self, command: str, execution_time: float) -> None:
        """Record a shell command execution.

        Args:
            command: Command string (stored truncated to 50 chars).
            execution_time: Elapsed time in seconds.
        """
        self.shell_commands_run += 1
        self.shell_command_total_time += execution_time

        self.shell_commands_history.append(
            {
                "command": command[:50],
                "time": execution_time,
                "timestamp": datetime.now(),
            }
        )
        if len(self.shell_commands_history) > 10:
            self.shell_commands_history.pop(0)

        self.last_activity = datetime.now()

    def set_status(self, status: str, message: str = "") -> None:
        """Set the current status and optional status message.

        Args:
            status: One of 'idle', 'running', 'thinking', 'executing'.
            message: Optional status detail string.
        """
        self.current_status = status
        self.status_message = message
        self.last_activity = datetime.now()

    def reset_to_idle(self) -> None:
        """Force status back to idle regardless of current state.

        Use after any error path or early return to guarantee the UI
        is never left stuck in 'thinking' or 'executing'.
        """
        self.current_status = "idle"
        self.status_message = ""
        self.last_activity = datetime.now()

    def safe_status(self, status: str, message: str = ""):
        """Context manager that sets status on enter and resets to idle on exit.

        Guarantees reset_to_idle() is called even when exceptions propagate.

        Usage:
            async with self.stats.safe_status("thinking", "Pensando..."):
                response = await llm_call(...)
        """
        return _SafeStatusContext(self, status, message)

    def toggle_skip_confirmations(self) -> bool:
        """Toggle skip_confirmations and return the new state."""
        self.skip_confirmations = not self.skip_confirmations
        return self.skip_confirmations

    def set_skip_confirmations(self, enabled: bool) -> None:
        """Set skip_confirmations explicitly.

        Args:
            enabled: True to skip confirmation prompts.
        """
        self.skip_confirmations = enabled

    def set_edit_percentage(self, percentage: float) -> None:
        """Set the edit percentage, clamped to 0.0–100.0."""
        self.edit_percentage = max(0.0, min(100.0, percentage))

    def set_model(self, model: str) -> None:
        """Set the current active LLM model name."""
        self.current_model = model

    def set_notification(self, message: str, duration_seconds: float = 3.0) -> None:
        """Set a temporary notification for the status bar.

        Args:
            message: Rich-markup message string.
            duration_seconds: Display duration in seconds (default 3.0).
        """
        self.notification_message = message
        self.notification_expires_at = datetime.now() + timedelta(
            seconds=duration_seconds
        )

    def clear_notification(self) -> None:
        """Clear the current notification."""
        self.notification_message = None
        self.notification_expires_at = None

    def get_notification(self) -> Optional[str]:
        """Return the current notification if still valid, else None."""
        if self.notification_message and self.notification_expires_at:
            if datetime.now() < self.notification_expires_at:
                return self.notification_message
            else:
                self.clear_notification()
        return None

    def track_tool_usage(self, tool_name: str) -> None:
        """Track usage of a named tool.

        Args:
            tool_name: Tool identifier.
        """
        self.tools_used[tool_name] += 1
        self._last_tool_used = tool_name
        self.last_activity = datetime.now()

    def increment_tool_calls(self, tool_name: str) -> None:
        """Alias for track_tool_usage."""
        self.track_tool_usage(tool_name)

    def increment_notebook_snapshots(self) -> None:
        """Increment the notebook snapshot counter."""
        self.notebook_snapshots += 1
        self.last_activity = datetime.now()

    def increment_notebook_pages_read(self) -> None:
        """Increment the notebook pages-read counter."""
        self.notebook_pages_read += 1
        self.last_activity = datetime.now()

    def get_total_files_changed(self) -> int:
        """Return total files changed (edited + created)."""
        return self.files_edited + self.files_created

    def get_files_changed(self) -> bool:
        """Return True if any file operations were recorded this turn."""
        if self._active_turn_execution is not None:
            projected = self.get_turn_files()
            return any(projected.values())
        return (
            len(self._files_edited_list) > 0
            or len(self._files_created_list) > 0
            or len(self._files_read_list) > 0
        )

    def clear_file_op_lists(self) -> None:
        """Clear all file-operation tracking lists."""
        self._files_edited_list.clear()
        self._files_created_list.clear()
        self._files_read_list.clear()
        self._active_turn_execution = None

    def get_average_shell_time(self) -> float:
        """Return the average shell command execution time in seconds."""
        if self.shell_commands_run == 0:
            return 0.0
        return self.shell_command_total_time / self.shell_commands_run

    def get_session_duration(self) -> timedelta:
        """Return elapsed time since session start."""
        return datetime.now() - self.session_start

    def get_last_shell_command_time(self) -> Optional[float]:
        """Return the last shell command execution time, or None."""
        if self.shell_commands_history:
            return self.shell_commands_history[-1]["time"]
        return None

    def format_tokens(self) -> str:
        """Format token count as a human-readable string (e.g. "1.5M tokens")."""
        if self.tokens_used >= 1_000_000:
            return f"{self.tokens_used / 1_000_000:.2f}M tokens"
        elif self.tokens_used >= 1_000:
            return f"{self.tokens_used / 1_000:.2f}k tokens"
        else:
            return f"{self.tokens_used} tokens"

    def format_shell_time(self, seconds: float) -> str:
        """Format execution time as a human-readable string.

        Args:
            seconds: Time in seconds.

        Returns:
            E.g. "150ms", "2.5s", "1m 30.5s".
        """
        if seconds < 1:
            return f"{seconds * 1000:.0f}ms"
        elif seconds < 60:
            return f"{seconds:.2f}s"
        else:
            mins = int(seconds // 60)
            secs = seconds % 60
            return f"{mins}m {secs:.1f}s"

    def check_budget(self, budget: Optional[int] = None) -> Optional[str]:
        """
        Check if token usage exceeds the configured budget.

        Args:
            budget: Token budget threshold. If None, reads from config.

        Returns:
            Warning message string if budget exceeded, None otherwise.
            Only returns the warning once per threshold crossing.
        """
        if budget is None:
            try:
                from aura_cli.core.config import config_manager

                budget = config_manager.get("token_budget_warning") or 100000
            except Exception:
                budget = 100000

        if self.tokens_used >= budget and not self._budget_warning_emitted:
            self._budget_warning_emitted = True
            formatted = self.format_tokens()
            return (
                f"⚠️  Token budget warning: {formatted} used this session "
                f"(budget: {budget:,} tokens). Use /cost for details."
            )
        return None

    def get_cost_summary(self) -> Dict[str, Any]:
        """
        Returns a cost summary for the current session.

        Estimates cost based on approximate per-token rates for known models.

        Returns:
            Dictionary with total_tokens, estimated_cost, breakdown_by_model, etc.
        """
        # Approximate rates per 1M tokens (input/output blended average)
        _MODEL_RATES: Dict[str, float] = {
            "gemini/gemini-2.5-flash": 0.15,
            "gemini/gemini-2.5-pro": 1.25,
            "gpt-4o": 5.00,
            "gpt-4o-mini": 0.30,
            "anthropic/claude-sonnet-4-6": 3.00,
            "anthropic/claude-haiku-4-5-20251001": 0.80,
        }

        breakdown = {}
        total_cost = 0.0
        for model_name, usage in self.tokens_by_model.items():
            rate = _MODEL_RATES.get(model_name, 0.50)  # default $0.50/1M
            model_cost = (usage["total_tokens"] / 1_000_000) * rate
            total_cost += model_cost
            breakdown[model_name] = {
                "total_tokens": usage["total_tokens"],
                "prompt_tokens": usage["prompt_tokens"],
                "completion_tokens": usage["completion_tokens"],
                "estimated_cost_usd": round(model_cost, 4),
                "rate_per_1m": rate,
            }

        return {
            "total_tokens": self.tokens_used,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "estimated_cost_usd": round(total_cost, 4),
            "breakdown_by_model": breakdown,
            "session_duration": str(self.get_session_duration()),
        }

    def get_stats_summary(self) -> Dict:
        """Return a complete snapshot of all statistics as a dict."""
        return {
            "tokens": self.tokens_used,
            "tokens_formatted": self.format_tokens(),
            "files_edited": self.files_edited,
            "files_created": self.files_created,
            "files_total": self.get_total_files_changed(),
            "shell_commands": self.shell_commands_run,
            "shell_avg_time": self.get_average_shell_time(),
            "status": self.current_status,
            "skip_confirmations": self.skip_confirmations,
            "edit_percentage": self.edit_percentage,
            "model": self.current_model,
            "session_duration": self.get_session_duration(),
            "tools_used": dict(self.tools_used),
            "notebook_snapshots": self.notebook_snapshots,
            "notebook_pages_read": self.notebook_pages_read,
        }

    def reset(self) -> None:
        """Reset all counters while keeping the session active."""
        self.tokens_used = 0
        self.prompt_tokens = 0
        self.completion_tokens = 0
        self.tokens_by_model.clear()
        self._budget_warning_emitted = False
        self.files_edited = 0
        self.files_created = 0
        self.files_read = 0
        self.files_by_type.clear()
        self.shell_commands_run = 0
        self.shell_command_total_time = 0.0
        self.shell_commands_history.clear()
        self.current_status = "idle"
        self.status_message = ""
        self.edit_percentage = 0.0
        self.tools_used.clear()
        self.notebook_snapshots = 0
        self.notebook_pages_read = 0


def get_stats() -> StatsTracker:
    """Return the global StatsTracker instance via the DI container.

    Thread-safe — the container uses internal locks.
    """
    try:
        from aura_cli.core.di import Services, get_container

        container = get_container()
        if container.has(Services.STATS):
            return container.resolve(Services.STATS)
    except Exception:
        pass
    # Simple fallback (no globals needed — container handles thread safety)
    return StatsTracker()


def reset_stats() -> None:
    """Reset global stats (thread-safe)."""
    try:
        from aura_cli.core.di import Services, get_container

        container = get_container()
        if container.has(Services.STATS) and container.is_resolved(Services.STATS):
            container.resolve(Services.STATS).reset()
            return
    except Exception:
        pass


def get_stats_snapshot() -> Dict[str, Any]:
    """Return an immutable snapshot of current statistics for serialisation or logging."""
    stats = get_stats()
    return stats.get_stats_summary()
