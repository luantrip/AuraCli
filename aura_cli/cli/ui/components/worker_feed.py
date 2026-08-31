"""
WorkerActivityFeed - Modern real-time feedback for background agents.

Provides a live-updating, minimal activity feed for AGI/Ops/Tester workers
inspired by GitHub Actions logs and Vercel deploy output.

Layout:
    ─── ◈ AGI · running · 12s
      ⟳ Analysing strutura do projeto...
      ✔ read_file(src/main.py) 18ms
      ✔ codebase_search(def main) 230ms
      ⟳ Planning refactoring...

    ─── ✦ Ops · git · completo · 3s
      ✔ git status
      ✔ git add -A
      ✔ git commit -m "feat: add auth"
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from rich.console import Group, RenderableType
from rich.text import Text

from aura_cli.cli.ui.constants import UIIcons
from aura_cli.cli.ui.layout_contract import layout_for_width
from aura_cli.cli.ui.strings import UIStrings
from aura_cli.cli.ui.theme_manager import get_theme_manager


class WorkerStep:
    """A single step in a worker's execution."""

    __slots__ = ("description", "duration_ms", "status", "timestamp")

    def __init__(
        self, description: str, status: str = "running", duration_ms: float = 0
    ):
        self.description = description
        self.status = status  # running | success | error | skipped
        self.duration_ms = duration_ms
        self.timestamp = datetime.now()

    def render(self, theme) -> Text:
        """Render single step line."""
        line = Text()
        if self.status == "success":
            icon = UIIcons.SUCCESS
            style = theme.get_style("status_success")
        elif self.status == "error":
            icon = UIIcons.ERROR
            style = theme.get_style("status_error")
        elif self.status == "skipped":
            icon = "○"
            style = theme.get_color("muted")
        else:
            icon = UIIcons.WORKING
            style = theme.get_style("status_working")

        line.append(f"    {icon} ", style=style)
        line.append(self.description, style=theme.get_style("body"))

        if self.duration_ms > 0 and self.status != "running":
            if self.duration_ms < 1000:
                time_str = f"{self.duration_ms:.0f}ms"
            else:
                time_str = f"{self.duration_ms / 1000:.1f}s"
            line.append(f" {time_str}", style=f"dim {theme.get_color('muted')}")

        return line


class WorkerActivityFeed:
    """
    Modern activity feed for a single background worker.

    Shows a compact header + scrolling steps, trimming old entries.
    """

    def __init__(
        self,
        agent_type: str,
        mode: str = "",
        max_visible_steps: int = 6,
    ):
        """Initialize feed.

        Args:
            agent_type: 'agi', 'ops', or 'tester'
            mode: Optional sub-mode (e.g., 'git', 'docker')
            max_visible_steps: Max steps to display (tail)
        """
        self.agent_type = agent_type.lower()
        self.mode = mode
        self.max_visible_steps = max_visible_steps
        self.steps: List[WorkerStep] = []
        self.status = "running"  # running | complete | error | cancelled
        self.start_time = datetime.now()
        self.current_phase = ""

    def add_step(
        self, description: str, status: str = "running", duration_ms: float = 0
    ):
        """Add execution step."""
        self.steps.append(WorkerStep(description, status, duration_ms))

    def set_phase(self, phase: str):
        """Set current phase description."""
        self.current_phase = phase

    def complete(self, success: bool = True):
        """Mark worker as complete."""
        self.status = "complete" if success else "error"

    def cancel(self) -> None:
        """Mark worker as cancelled without presenting it as an error."""
        self.status = "cancelled"

    def render(self, console_width: int = 80) -> RenderableType:
        """Renderiza o feed completo usando a densidade do terminal."""
        metrics = layout_for_width(console_width)
        theme = get_theme_manager()
        muted = theme.get_color("muted")
        parts: List[Any] = []

        # Header line: ─── ICON AGENT · mode · status · elapsed
        parts.append(self._render_header(theme, muted))

        # Current phase indicator
        if self.current_phase and self.status == "running":
            phase_line = Text()
            phase_line.append(
                f"    {UIIcons.WORKING} ", style=theme.get_style("status_working")
            )
            phase_line.append(
                self.current_phase, style=f"italic {theme.get_style('body')}"
            )
            parts.append(phase_line)

        # Steps (tail only)
        visible_limit = max(
            1,
            min(
                self.max_visible_steps, 4 if metrics.narrow else self.max_visible_steps
            ),
        )
        visible = self.steps[-visible_limit:]
        if len(self.steps) > visible_limit:
            hidden = len(self.steps) - visible_limit
            skip_line = Text()
            skip_line.append(f"    ⋯ {hidden} etapas anteriores", style=f"dim {muted}")
            parts.append(skip_line)

        for step in visible:
            parts.append(step.render(theme))

        return Group(*parts)

    def _render_header(self, theme, muted: str) -> Text:
        """Render feed header."""
        header = Text()
        header.append("─── ", style=f"dim {muted}")

        # Agent icon + name
        icon, style = self._get_agent_style(theme)
        header.append(f"{icon} ", style=style)
        header.append(self.agent_type.upper(), style=f"bold {style}")

        # Mode
        if self.mode:
            header.append(f" · {self.mode}", style=f"dim {muted}")

        # Status
        if self.status == "complete":
            header.append(" · ", style=f"dim {muted}")
            header.append("completo", style=theme.get_style("status_success"))
        elif self.status == "error":
            header.append(" · ", style=f"dim {muted}")
            header.append("erro", style=theme.get_style("status_error"))
        elif self.status == "cancelled":
            header.append(" · ", style=f"dim {muted}")
            header.append(UIStrings.CANCELLED, style=theme.get_style("status_warning"))
        else:
            header.append(" · ", style=f"dim {muted}")
            header.append("em execução", style=theme.get_style("status_working"))

        # Elapsed time
        elapsed = (datetime.now() - self.start_time).total_seconds()
        time_str = f"{elapsed:.0f}s" if elapsed < 60 else f"{elapsed / 60:.1f}min"
        header.append(f" · {time_str}", style=f"dim {muted}")

        return header

    def _get_agent_style(self, theme) -> tuple:
        """Get icon and style for agent type."""
        configs = {
            "agi": (UIIcons.AGI, theme.get_style("agent_agi")),
            "ops": (UIIcons.OPS, theme.get_style("agent_ops")),
            "tester": (UIIcons.AGENT, theme.get_style("status_warning")),
        }
        return configs.get(self.agent_type, (UIIcons.AGENT, theme.get_style("primary")))


def parse_status_messages(messages: List[Any]) -> List[WorkerActivityFeed]:
    """
    Parse raw status queue messages into WorkerActivityFeed instances.

    Groups messages by agent type and builds feeds.
    """
    feeds: Dict[str, WorkerActivityFeed] = {}

    for msg in messages:
        text = _extract_text(msg)
        if not text:
            continue

        if "[Aura AGI]" in text:
            key = "agi"
            clean = text.replace("[Aura AGI]", "").strip()
        elif "[Aura Ops]" in text:
            key = "ops"
            clean = text.replace("[Aura Ops]", "").strip()
        elif "[TesterWorker]" in text or "[Tester]" in text:
            key = "tester"
            clean = text.replace("[TesterWorker]", "").replace("[Tester]", "").strip()
        else:
            continue

        clean = clean.lstrip("› ").strip()

        if key not in feeds:
            mode = ""
            if isinstance(msg, dict):
                mode = msg.get("data", {}).get("mode", "")
            feeds[key] = WorkerActivityFeed(agent_type=key, mode=mode)

        feed = feeds[key]

        # Determine step status from message content.
        # Priority: use the structured "status" field from dict messages first
        # (robust), then fall back to text heuristics so that icon changes in
        # UIIcons never silently mis-classify a step.
        step_status: Optional[str] = None
        if isinstance(msg, dict):
            data = msg.get("data", {})
            step_status = data.get("status") if isinstance(data, dict) else None

        if step_status in ("success", "complete", "done"):
            feed.add_step(clean.lstrip("⬢⟳✔✖▲ℹ⚒🤔⚙ "), status="success")
        elif step_status in ("error", "failed", "fail"):
            feed.add_step(clean.lstrip("⬢⟳✔✖▲ℹ⚒🤔⚙ "), status="error")
        elif step_status in ("running", "thinking", "planning"):
            feed.set_phase(clean.lstrip("⬢⟳✔✖▲ℹ⚒🤔⚙ "))
        else:
            # Text-based heuristics — use both icon values AND stable keywords
            # so the detection survives icon set changes.
            _SUCCESS_MARKERS = {UIIcons.SUCCESS, "✔", "✓", "☑"}
            _ERROR_MARKERS = {UIIcons.ERROR, "✖", "❌", "✗"}
            _PHASE_KEYWORDS = {
                "Planejando", "Analisando", "Executando", "Iniciando",
                "Pensando", "Planning", "Analyzing",
            }
            _PHASE_ICONS = {UIIcons.THINKING, UIIcons.WORKING, "⟳", "🤔"}

            clean_no_icons = clean.lstrip("⬢⟳✔✖▲ℹ⚒🤔⚙ ")

            if any(m in clean for m in _SUCCESS_MARKERS):
                feed.add_step(clean_no_icons, status="success")
            elif any(m in clean for m in _ERROR_MARKERS):
                feed.add_step(clean_no_icons, status="error")
            elif any(m in clean for m in _PHASE_ICONS) or any(
                kw in clean for kw in _PHASE_KEYWORDS
            ):
                feed.set_phase(clean_no_icons)
            else:
                feed.add_step(clean_no_icons, status="success")

    return list(feeds.values())


def _extract_text(msg: Any) -> Optional[str]:
    """Extract text content from a message."""
    if isinstance(msg, str):
        return msg
    if isinstance(msg, dict):
        for key in ("content", "message", "description"):
            if key in msg:
                return str(msg[key])
        data = msg.get("data", {})
        if isinstance(data, dict):
            for key in ("content", "message"):
                if key in data:
                    return str(data[key])
    return None


def render_worker_feeds(
    feeds: List["WorkerActivityFeed"], console_width: int = 80
) -> Group:
    """Render multiple feeds without adding external spacing."""
    return Group(*(feed.render(console_width=console_width) for feed in feeds))
