"""
Status panel - Clean, minimal status display.

Provides formatted status messages for real-time agent activity
with minimal visual noise.
"""

from collections import defaultdict
from datetime import datetime
import queue
from typing import Any, Dict, List, Optional

from rich.console import Group
from rich.text import Text

from aura_cli.cli.ui.constants import UIIcons
from aura_cli.cli.ui.theme_manager import get_theme_manager


def _extract_msg_text(msg: Any) -> Optional[str]:
    """Extract text from a status message (dict or str)."""
    if isinstance(msg, dict):
        for key in ("message", "content", "description"):
            if key in msg:
                return str(msg[key])
        data = msg.get("data")
        if isinstance(data, dict):
            for key in ("content", "message", "description"):
                if key in data:
                    return str(data[key])
        return None
    return str(msg)


def _build_status_parts(grouped: Dict[str, List[str]], theme: Any, muted: str) -> list:
    """Build Rich Text parts for the status panel."""
    parts: list = []
    header = Text()
    header.append("─── ", style=f"dim {muted}")
    header.append(
        f"{UIIcons.STATS} Atividade",
        style=f"bold {theme.get_style('primary')}",
    )
    header.append(f"  {datetime.now().strftime('%H:%M:%S')}", style=f"dim {muted}")
    parts.append(header)
    parts.append(Text())
    for msg in grouped.get("AGI", [])[:3]:
        line = Text()
        line.append(f"  {UIIcons.AGI} ", style=theme.get_style("agent_agi"))
        line.append(msg, style=theme.get_style("body"))
        parts.append(line)
    for msg in grouped.get("OPS", [])[:2]:
        line = Text()
        line.append(f"  {UIIcons.OPS} ", style=theme.get_style("agent_ops"))
        line.append(msg, style=theme.get_style("body"))
        parts.append(line)
    for msg in grouped.get("GENERIC", [])[:2]:
        line = Text()
        line.append(f"  {UIIcons.BULLET} ", style=f"dim {muted}")
        line.append(msg, style=f"dim {theme.get_style('body')}")
        parts.append(line)
    return parts


def create_status_panel(
    status_queue: queue.Queue, max_messages: int = 10
) -> Optional[Group]:
    """
    Create minimal status display from message queue.

    Args:
        status_queue: Queue with status messages
        max_messages: Maximum messages to show

    Returns:
        Group with formatted status messages or None
    """
    theme = get_theme_manager()
    muted = theme.get_color("muted")

    messages = []
    count = 0

    while not status_queue.empty() and count < max_messages:
        try:
            msg = status_queue.get_nowait()
            messages.append(msg)
            count += 1
        except queue.Empty:
            break

    if not messages:
        return None

    valid_messages = []

    for msg in messages:
        clean_msg = _extract_msg_text(msg)
        if clean_msg:
            clean_msg = clean_msg.replace("› ", "").strip()
            if clean_msg:
                valid_messages.append(clean_msg)

    if not valid_messages:
        return None

    # Group messages by type
    grouped: Dict[str, List[str]] = defaultdict(list)

    for clean_msg in valid_messages:
        if "[Aura AGI]" in clean_msg:
            grouped["AGI"].append(clean_msg.replace("[Aura AGI]", "").strip())
        elif "[Aura Ops]" in clean_msg:
            grouped["OPS"].append(clean_msg.replace("[Aura Ops]", "").strip())
        else:
            grouped["GENERIC"].append(clean_msg)

    return Group(*_build_status_parts(grouped, theme, muted))


def create_activity_indicator(
    activity: str,
    details: Optional[str] = None,
    progress: Optional[float] = None,
) -> Text:
    """
    Create minimal activity indicator.

    Args:
        activity: Activity description
        details: Optional details
        progress: Optional progress (0-1)

    Returns:
        Formatted activity text
    """
    theme = get_theme_manager()
    muted = theme.get_color("muted")

    indicator = Text()
    indicator.append(f"{UIIcons.WORKING} ", style=theme.get_style("status_working"))
    indicator.append(activity, style=theme.get_style("body"))

    if details:
        indicator.append(f"  {details}", style=f"dim {muted}")

    if progress is not None:
        percent = int(progress * 100)
        indicator.append(f"  {percent}%", style=f"dim {muted}")

    return indicator


def create_completion_indicator(
    message: str,
    success: bool = True,
    duration: Optional[float] = None,
) -> Text:
    """
    Create completion indicator.

    Args:
        message: Completion message
        success: Whether successful
        duration: Optional duration

    Returns:
        Formatted completion text
    """
    theme = get_theme_manager()
    muted = theme.get_color("muted")

    if success:
        icon = UIIcons.SUCCESS
        style = theme.get_style("success")
    else:
        icon = UIIcons.ERROR
        style = theme.get_style("error")

    indicator = Text()
    indicator.append(f"{icon} ", style=style)
    indicator.append(message, style=style)

    if duration is not None:
        time_str = f"{duration * 1000:.0f}ms" if duration < 1 else f"{duration:.1f}s"
        indicator.append(f"  {time_str}", style=f"dim {muted}")

    return indicator
