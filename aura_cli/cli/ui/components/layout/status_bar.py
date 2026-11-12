"""
StatusBar component for Aura CLI.

A persistent one-line footer printed before each prompt. By default it shows only
what the user needs to decide their next move:

- activity state (idle, thinking, working, executing),
- the model in use,
- how full the context window is, and the session's token total,
- to-do progress.

Cost, the last turn's duration and the git branch are *detail*: they appear only
when the ``status_bar_verbose`` setting is on. Auto-run is deliberately absent --
the prompt itself already says ``(sem confirmação)`` where the action happens.

The component is "dumb": it receives a ``StatsTracker`` and renders it, with
``rich.table`` for layout. It never invents a number: when a value is not known
yet (e.g. no request has been sent), it is omitted rather than estimated.
"""

import logging

from rich.table import Table
from rich.text import Text

from aura_cli.application.workspace.context_usage import (
    context_window_for_model,
    get_context_percentage,
)
from aura_cli.cli.ui.constants import UIIcons, UIStyles
from aura_cli.cli.ui.layout_contract import layout_for_width
from aura_cli.core.config import config_manager
from aura_cli.core.llm.model_utils import (
    format_model_display_name,
    get_provider_from_model,
)
from aura_cli.core.stats import StatsTracker

logger = logging.getLogger(__name__)


class StatusBar:
    """Um componente de UI que renderiza a barra de status."""

    # Cache TTL for git branch lookup (seconds) — avoids repeated I/O on
    # every render cycle, which matters on slow mounts (NFS, Docker volumes).
    _GIT_CACHE_TTL: float = 10.0

    def __init__(self, stats: StatsTracker, verbose: bool | None = None):
        """Initialise the status bar.

        ``verbose`` forces the detail mode on or off; ``None`` follows the
        ``status_bar_verbose`` setting, read at render time so toggling it in
        ``/settings`` applies on the next prompt without a restart.
        """
        self.stats = stats
        self._verbose_override = verbose
        self._last_turn_time = 0.0
        self._last_turn_model = ""
        self._git_branch_cache: tuple[float, str | None] = (0.0, None)  # (ts, branch)

    @property
    def verbose(self) -> bool:
        if self._verbose_override is not None:
            return self._verbose_override
        return bool(config_manager.get("status_bar_verbose"))

    def record_turn_metrics(self, exec_time: float = 0.0, model: str = "") -> None:
        """Record metrics for the current turn."""
        self._last_turn_time = max(0.0, float(exec_time))
        self._last_turn_model = model

    def render(self, todo_summary: str = "", console_width: int = 80) -> Table:
        """Render the status bar as a Rich renderable."""
        notification = self.stats.get_notification()

        if notification:
            status_table = Table.grid(expand=True, padding=(0, 1))
            status_table.add_column(justify="center", ratio=1)
            status_table.add_row(Text.from_markup(notification))
            return status_table

        metrics = layout_for_width(console_width)
        status_table = Table.grid(expand=True, padding=(0, 1))
        left_panel = self._create_left_panel(console_width=metrics.width)
        right_panel = self._create_right_panel(
            todo_summary, console_width=metrics.width
        )

        if metrics.narrow:
            status_table.add_column(justify="left")
            status_table.add_row(left_panel)
            status_table.add_row(right_panel)
        else:
            status_table.add_column(justify="left", ratio=1)
            status_table.add_column(justify="right", ratio=1)
            status_table.add_row(left_panel, right_panel)

        return status_table

    def _get_git_branch(self) -> str | None:
        """Return the current git branch with TTL caching to avoid per-render I/O."""
        import time

        ts, cached = self._git_branch_cache
        if time.monotonic() - ts < self._GIT_CACHE_TTL:
            return cached

        branch: str | None = None
        try:
            from pathlib import Path

            from aura_cli.core.git_manager import GitManager

            git_mgr = GitManager(Path.cwd())
            branch = git_mgr.get_current_branch() or None
        except Exception:
            logger.debug("Failed to read git branch for status bar", exc_info=True)
        return branch

    def _create_left_panel(self, console_width: int = 80) -> Text:
        """Create the left section of the status bar."""
        metrics = layout_for_width(console_width)
        panel_text = Text(no_wrap=not metrics.narrow)

        state = self.stats.current_status
        if state in ("running", "working"):
            panel_text.append(f"{UIIcons.WORKING} ", style=f"{UIStyles.PRIMARY} bold")
            panel_text.append("Processing", style=f"{UIStyles.PRIMARY} bold")
        elif state == "thinking":
            panel_text.append(f"{UIIcons.THINKING} ", style=f"{UIStyles.WARNING} bold")
            panel_text.append("Raciocinando", style=f"{UIStyles.WARNING} bold")
        elif state == "executing":
            panel_text.append(f"{UIIcons.TOOL} ", style=f"{UIStyles.ACCENT} bold")
            panel_text.append("Executando", style=f"{UIStyles.ACCENT} bold")
        else:
            panel_text.append(f"{UIIcons.IDLE} ", style=f"{UIStyles.SUCCESS} bold")
            panel_text.append("Ocioso", style=UIStyles.SUCCESS)

        # Mode Badge if active
        active_mode = getattr(self.stats, "active_mode", None)
        if active_mode and active_mode != "NORMAL":
            panel_text.append(f" {UIIcons.SEPARATOR} ", style=UIStyles.MUTED)
            panel_text.append(f"[{active_mode}]", style=f"{UIStyles.ACCENT} bold")

        panel_text.append(f" {UIIcons.SEPARATOR} ", style=UIStyles.MUTED)

        # Extrair nome do modelo formatado e provider
        model_full = self._last_turn_model or self.stats.current_model or "auto"
        model_display_name = metrics.fit_inline(
            format_model_display_name(model_full), reserve=32
        )

        # Map canonical providers to clean colors (no duplicated ID parsing).
        provider = get_provider_from_model(model_full)
        provider_colors: dict[str, str] = {
            "gemini": UIStyles.PRIMARY,
            "claude": UIStyles.ACCENT,
            "gpt": UIStyles.SUCCESS,
            "openrouter": UIStyles.INFO,
            "nvidia": UIStyles.INFO,
            "cerebras": UIStyles.SUCCESS,
            "groq": UIStyles.SUCCESS,
        }
        color = provider_colors.get(provider or "", UIStyles.MUTED)

        panel_text.append(model_display_name, style=f"{color} bold")

        # Git branch is detail: verbose only (also skips the cached git lookup).
        branch = self._get_git_branch() if self.verbose else None
        if branch:
            panel_text.append(f" {UIIcons.SEPARATOR} ", style=UIStyles.MUTED)
            panel_text.append(
                metrics.fit_inline(f"git:{branch}", reserve=32),
                style=f"dim {UIStyles.INFO}",
            )

        return panel_text

    def _context_usage(self) -> float | None:
        """Percent of the model's context window in use, or ``None`` if unknown.

        Uses ``stats.context_tokens`` -- the size of the history that the next
        request will actually send -- not ``total_tokens``, which is the session's
        cumulative spend (every call re-sends the whole history, so it grows far
        faster than the window fills). Before any request has measured the history
        there is no honest number, so nothing is shown.
        """
        used = getattr(self.stats, "context_tokens", 0) or 0
        if not isinstance(used, (int, float)) or used <= 0:
            return None
        model = self._last_turn_model or self.stats.current_model or ""
        return get_context_percentage(int(used), context_window_for_model(model))

    def _create_right_panel(self, todo_summary: str, console_width: int = 80) -> Text:
        """Create context, token and task metrics (cost / last turn when verbose)."""
        metrics = layout_for_width(console_width)
        panel_text = Text(no_wrap=not metrics.narrow)
        sep = f" {UIIcons.SEPARATOR} "

        percentage = self._context_usage()
        if percentage is not None:
            if percentage < 50:
                ctx_style = UIStyles.SUCCESS
            elif percentage < 90:
                ctx_style = UIStyles.WARNING
            else:
                ctx_style = UIStyles.ERROR
            panel_text.append("Contexto ", style=UIStyles.MUTED)
            panel_text.append(f"{percentage:.0f}%", style=ctx_style)
            panel_text.append(sep, style=UIStyles.MUTED)

        tokens_used = self.stats.total_tokens
        if tokens_used >= 1_000_000:
            tok_str = f"{tokens_used / 1_000_000:.1f}M tok"
        elif tokens_used >= 1_000:
            tok_str = f"{tokens_used / 1_000:.1f}k tok"
        else:
            tok_str = f"{tokens_used} tok"
        panel_text.append(tok_str, style=UIStyles.WARNING)

        if self.verbose:
            cost = getattr(self.stats, "total_cost", 0.0) or getattr(
                self.stats, "cost", 0.0
            )
            if cost > 0:
                panel_text.append(sep, style=UIStyles.MUTED)
                panel_text.append(f"${cost:.4f}", style="dim green")

            if self._last_turn_time > 0:
                panel_text.append(sep, style=UIStyles.MUTED)
                turn_time = (
                    f"{self._last_turn_time * 1000:.0f}ms"
                    if self._last_turn_time < 1
                    else f"{self._last_turn_time:.1f}s"
                )
                panel_text.append(f"last {turn_time}", style=UIStyles.MUTED)

        panel_text.append(sep, style=UIStyles.MUTED)

        try:
            from aura_cli.core.todo.todo_tracker import get_todo_tracker

            tracker = get_todo_tracker()
            stats = tracker.get_stats()
            if stats["total"] > 0:
                sm = f"{stats['done']}/{stats['total']}"
                if stats["done"] == stats["total"]:
                    panel_text.append(f"{UIIcons.SUCCESS} {sm}", style=UIStyles.SUCCESS)
                elif stats["done"] > 0:
                    panel_text.append(f"{UIIcons.WORKING} {sm}", style=UIStyles.WARNING)
                else:
                    panel_text.append(f"{UIIcons.IDLE} {sm}", style=UIStyles.PRIMARY)
            else:
                panel_text.append("—", style=UIStyles.MUTED)
        except Exception:
            if (
                "No Tasks" in todo_summary
                or "No tasks" in todo_summary
                or not todo_summary
            ):
                panel_text.append("—", style=UIStyles.MUTED)
            else:
                panel_text.append(todo_summary, style=UIStyles.SUCCESS)

        return panel_text
