"""Dynamic tool status messages for Aura CLI.

Generates contextual status messages and semantic icons for tool execution
states: generating, generated, calling, done, errored, canceled. Colors
reflect progress (yellow), success (green) or failure (red).
"""

from typing import Any, List, Literal, Optional

from rich.columns import Columns
from rich.console import Group, RenderableType
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeElapsedColumn,
)
from rich.text import Text

from aura_cli.cli.ui.constants import UIIcons, UIStyles

ToolStatus = Literal[
    "generating", "generated", "calling", "done", "errored", "canceled"
]


def get_status_intro(status: ToolStatus, is_instant: bool = False) -> str:
    """Return the introductory verb for a tool status phrase.

    Maps each status to a verb used in natural-language messages
    (e.g. "calling" → an action verb for "Aura is using…").

    Args:
        status: Current ToolStatus literal.
        is_instant: If True, treat "calling" the same as "done" (no intro verb).

    Returns:
        Intro verb string, or empty string for "done" / instant-done.
    """
    if status == "done" or (is_instant and status == "calling"):
        return ""

    status_map = {
        "generating": "vai",
        "generated": "quer",
        "calling": "está",
        "canceled": "tentou",
        "errored": "tentou",
    }

    return status_map.get(status, "")


def get_status_icon(status: ToolStatus) -> str:
    """Return the Unicode icon for a tool status.

    generating/calling → ⚡, generated → →, done → ✓,
    canceled → ⊗, errored → ✗.

    Args:
        status: Current ToolStatus literal.

    Returns:
        Unicode icon character.
    """
    status_icons = {
        "generating": UIIcons.LOADING,
        "calling": UIIcons.LOADING,
        "generated": UIIcons.ARROW,
        "done": UIIcons.SUCCESS,
        "canceled": UIIcons.CANCEL,
        "errored": UIIcons.ERROR,
    }

    return status_icons.get(status, UIIcons.TOOL)


def get_status_color(status: ToolStatus) -> str:
    """Return the Rich style string for a tool status.

    generating/calling → yellow, generated → cyan,
    done → green, canceled → yellow, errored → red.

    Args:
        status: Current ToolStatus literal.

    Returns:
        Rich style string (e.g. "yellow", "green").
    """
    status_colors = {
        "generating": UIStyles.WARNING,
        "calling": UIStyles.WARNING,
        "generated": UIStyles.PRIMARY,
        "done": UIStyles.SUCCESS,
        "canceled": UIStyles.WARNING,
        "errored": UIStyles.ERROR,
    }

    return status_colors.get(status, UIStyles.MUTED)


def get_group_action_verb(statuses: List[ToolStatus]) -> str:
    """Return an action verb describing a group of tools as a whole.

    Priority order: calling > generating > generated > done > errored/canceled.

    Args:
        statuses: List of ToolStatus values for each tool in the group.

    Returns:
        Action verb string: "Executando", "Gerando", "Pendente",
        "Executado" or "Tentado".
    """
    if not statuses:
        return "Executando"

    if "calling" in statuses:
        return "Executando"
    elif "generating" in statuses:
        return "Gerando"
    elif "generated" in statuses:
        return "Pendente"
    elif any(s == "done" for s in statuses):
        return "Executado"
    elif any(s in ("errored", "canceled") for s in statuses):
        return "Tentado"

    return "Executando"


def format_tool_status_message(
    tool_name: str,
    status: ToolStatus,
    is_instant: bool = False,
    custom_message: Optional[str] = None,
) -> str:
    """Format a contextual status message for a tool execution.

    Combines icon, intro verb and action into one string. Message varies
    by status: "Aura is using…", "Aura used…", "Aura tried to use…".

    Args:
        tool_name: Tool identifier (e.g. "read_file").
        status: Current ToolStatus literal.
        is_instant: If True, skips "is" and uses "used" immediately.
        custom_message: Optional override for the default message body.

    Returns:
        Formatted string (e.g. "⚡ Aura is using tool read_file").
    """
    intro = get_status_intro(status, is_instant)
    icon = get_status_icon(status)

    if custom_message:
        message = custom_message
    elif status == "done" or (is_instant and status == "calling"):
        message = f"usou a ferramenta {tool_name}"
    elif status in ("generating", "generated", "canceled", "errored"):
        message = f"usar a ferramenta {tool_name}"
    elif status == "calling":
        message = f"usando a ferramenta {tool_name}"
    else:
        message = f"ferramenta {tool_name}"

    if intro:
        return f"{icon} Aura {intro} {message}"
    else:
        return f"{icon} Aura {message}"


def render_tool_status_panel(
    tool_name: str,
    status: ToolStatus,
    execution_time: Optional[float] = None,
    tokens: Optional[int] = None,
    result_preview: Optional[str] = None,
) -> RenderableType:
    """Render a tool status as an open Rich surface.

    Args:
        tool_name: Tool identifier.
        status: Current execution status.
        execution_time: Elapsed time in seconds, if available.
        tokens: Token count used, if available.
        result_preview: Short preview of the result, if available.

    Returns:
        Rich Group with header, metrics and optional progress/preview.
    """

    status_icon = get_status_icon(status)
    status_color = get_status_color(status)

    # Header
    header = Text()
    header.append(f"{status_icon} ", style=status_color + " bold")
    header.append(tool_name, style=UIStyles.PRIMARY + " bold")

    # Metrics in columns
    metrics_parts = []
    if execution_time is not None:
        time_text = Text()
        time_text.append(f"{UIIcons.TIMER} ", style=UIStyles.MUTED)
        time_text.append(f"{execution_time:.2f}s", style=UIStyles.INFO)
        metrics_parts.append(time_text)

    if tokens is not None:
        token_text = Text()
        token_text.append(f"{UIIcons.STATS} ", style=UIStyles.MUTED)
        token_text.append(f"{tokens:,} tokens", style=UIStyles.INFO)
        metrics_parts.append(token_text)

    # Progress bar se estiver executando
    progress_content: list[Any] = []
    if status == "calling" or status == "generating":
        progress = Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TimeElapsedColumn(),
        )
        with progress:
            progress.add_task(f"Executando {tool_name}...", total=None)
        progress_content.append(progress)

    # Result preview
    if result_preview:
        preview_text = Text()
        preview_text.append("Resultado: ", style=UIStyles.LABEL)
        preview_text.append(
            result_preview[:100] + "..."
            if len(result_preview) > 100
            else result_preview,
            style=UIStyles.BODY,
        )
        progress_content.append(preview_text)

    content_parts: list[Any] = []
    if metrics_parts:
        content_parts.append(Columns(metrics_parts, equal=True, expand=True))
    if progress_content:
        content_parts.extend(progress_content)

    return Group(header, *content_parts)
