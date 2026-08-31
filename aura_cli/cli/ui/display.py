"""Rich display components for development operations in Aura CLI.

Renders tool call args, file diffs, shell command output and chat bubbles.
Creates its own Console() because these functions are called from core tool
layers that have no access to UIManager — this is intentional.

For generic status messages (error/success/warning/info) use display_facade.py.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from rich.console import Group
from rich.panel import Panel
from rich.syntax import Syntax
from rich.text import Text

from aura_cli.application.presentation.safe_payloads import safe_tool_args_json
from aura_cli.cli.ui.components.file_diff import FileDiff
from aura_cli.cli.ui.components.syntax import AuraSyntax
from aura_cli.cli.ui.constants import UIIcons, UIStyles
from aura_cli.cli.ui.display_facade import get_console
from aura_cli.cli.ui.responsive import get_responsive_layout
from aura_cli.cli.ui.strings import UIStrings

console = get_console()
responsive = get_responsive_layout(console)


class ExpandablePreview:
    """Expandable preview with collapse/expand support."""

    def __init__(self, content: str, max_preview_length: int = 500):
        """Initialize the instance."""
        self.content = content
        self.max_preview_length = max_preview_length
        self.is_expanded = False

    def toggle(self):
        """Alterna entre expandido e colapsado."""
        self.is_expanded = not self.is_expanded

    def render(self, title: str = "Pré-visualização") -> Panel:
        """Render the expandable preview."""
        if self.is_expanded or len(self.content) <= self.max_preview_length:
            display_content = self.content
            expand_hint = ""
        else:
            display_content = self.content[: self.max_preview_length]
            remaining = len(self.content) - self.max_preview_length
            muted_style = UIStyles.safe_style("MUTED", "dim white")
            expand_hint = f"\n\n[{muted_style}][... +{remaining} {UIStrings.CHARACTERS} — [e] {UIStrings.EXPAND}][/{muted_style}]"

        body_style = UIStyles.safe_style("BODY", "white")
        subtitle_style = UIStyles.safe_style("SUBTITLE", "bold cyan")
        border_style = UIStyles.safe_style("BORDER_PRIMARY", "cyan")
        text = Text(display_content + expand_hint, style=body_style)
        return Panel(
            text,
            title=f"[{subtitle_style}]{title}[/{subtitle_style}]",
            border_style=border_style,
            padding=(1, 2),
        )


def display_tool_args(
    tool_name: str, args: dict, is_showing: bool = False, expandable: bool = True
) -> None:
    """
    Display tool call arguments in organized format with expandable preview.

    Args:
        tool_name: Name of the tool
        args: Tool arguments dictionary
        is_showing: Whether to show arguments
        expandable: Whether to show expandable preview for long values
    """
    if not args or not is_showing:
        return

    muted_style = UIStyles.safe_style("MUTED", "dim white")
    console.print()
    console.print(f"  [{muted_style}]{UIIcons.INFO} Arguments:[/{muted_style}]")

    for key, value in args.items():
        value_str = (
            safe_tool_args_json({key: value})
            if isinstance(value, (dict, list))
            else "[oculto]"
        )
        is_long = len(value_str) > 100

        if is_long and expandable:
            # Expandable preview with syntax highlighting if JSON
            try:
                if isinstance(value, (dict, list)):
                    json_str = safe_tool_args_json({key: value})
                    syntax = Syntax(
                        json_str, "json", theme="monokai", line_numbers=False
                    )
                    label_style = UIStyles.safe_style("LABEL", "bold")
                    border_muted_style = UIStyles.safe_style(
                        "BORDER_MUTED", "dim white"
                    )
                    preview = Panel(
                        syntax,
                        title=f"[{label_style}]{key}[/{label_style}]",
                        border_style=border_muted_style,
                        padding=(1, 2),
                    )
                    console.print(f"    {preview}")
                else:
                    preview_text = value_str[:100] + "..."
                    console.print(
                        f"    [{UIStyles.LABEL}]{key}:[/{UIStyles.LABEL}] [{UIStyles.CODE}]{preview_text}[/{UIStyles.CODE}]"
                    )
                    console.print(
                        f"      [{UIStyles.MUTED}][... {len(value_str) - 100} more characters][/{UIStyles.MUTED}]"
                    )
            except Exception:
                # Fallback to simple display
                console.print(
                    f"    [{UIStyles.LABEL}]{key}:[/{UIStyles.LABEL}] [{UIStyles.CODE}]{value_str[:100]}...[/{UIStyles.CODE}]"
                )
        else:
            console.print(
                f"    [{UIStyles.LABEL}]{key}:[/{UIStyles.LABEL}] [{UIStyles.CODE}]{value_str}[/{UIStyles.CODE}]"
            )

    console.print()


def display_file_edit(
    file_path: str,
    old_content: str,
    new_content: str,
    show_preview: bool = True,
    max_preview_lines: int = 50,
) -> None:
    """Display file edit with formatted diff using FileDiff component.

    Args:
        file_path: Path to file being edited
        old_content: Original file content
        new_content: New file content
        show_preview: Whether to show preview
        max_preview_lines: Maximum lines to show in preview
    """
    if not show_preview:
        return

    diff_component = FileDiff()
    diff_panel = diff_component.render(
        file_path=file_path,
        old_content=old_content,
        new_content=new_content,
        max_preview_lines=max_preview_lines,
        show_stats=True,
    )
    console.print()
    console.print(diff_panel)
    console.print()


def display_shell_command(
    command: str,
    output: Optional[str] = None,
    execution_time: Optional[float] = None,
    exit_code: Optional[int] = None,
    show_output: bool = True,
) -> None:
    """
    Compat wrapper for shell command rendering.

    The canonical high-level entrypoint is
    `aura_cli.cli.ui.terminal_command.display_run_terminal_command()`.
    This helper is kept for callers that still import `display.py`.
    """
    from aura_cli.cli.ui.terminal_command import display_run_terminal_command

    if exit_code is not None and exit_code != 0:
        status = "failed"
    elif execution_time is None:
        status = "running"
    else:
        status = "completed"

    display_run_terminal_command(
        command=command,
        output=output if show_output else None,
        status=status,
        execution_time=execution_time,
        exit_code=exit_code,
        show_security_warning=True,
    )


def format_code_preview(
    code: str,
    language: str = "python",
    max_lines: int = 20,
    highlight_lines: Optional[List[int]] = None,
    expandable: bool = True,
) -> Panel:
    """Format a code preview with syntax highlighting."""

    lines = code.split("\n")
    syntax_component = AuraSyntax()

    if len(lines) <= max_lines or not expandable:
        syntax = syntax_component.render(
            code, language, highlight_lines=highlight_lines
        )
        subtitle_style = UIStyles.safe_style("SUBTITLE", "bold cyan")
        border_primary_style = UIStyles.safe_style("BORDER_PRIMARY", "cyan")
        return Panel(
            syntax,
            title=f"[{subtitle_style}]Preview de código ({language})[/{subtitle_style}]",
            border_style=border_primary_style,
            padding=(1, 2),
        )

    # Truncated preview with indicator
    start_lines = lines[: max_lines // 2]
    end_lines = lines[-max_lines // 2 :]
    omitted = len(lines) - max_lines

    preview_lines = [*start_lines, f"# {UIStrings.omitted_hint(omitted)}", *end_lines]
    preview_code = "\n".join(preview_lines)

    syntax = syntax_component.render(
        preview_code, language, highlight_lines=highlight_lines
    )

    muted_style = UIStyles.safe_style("MUTED", "dim white")
    subtitle_style = UIStyles.safe_style("SUBTITLE", "bold cyan")
    border_primary_style = UIStyles.safe_style("BORDER_PRIMARY", "cyan")

    footer = Text()
    footer.append(
        f"[{muted_style}][... +{omitted} linhas — código completo: {len(lines)} linhas][/{muted_style}]",
        style=muted_style,
    )

    return Panel(
        Group(syntax, footer),
        title=f"[{subtitle_style}]Preview de código ({language}) — {len(lines)} linhas[/{subtitle_style}]",
        border_style=border_primary_style,
        padding=(1, 2),
    )


def search_in_content(
    content: str, query: str, context_lines: int = 3
) -> List[Dict[str, Any]]:
    """Search for text in content and return matches with context."""
    matches = []
    lines = content.splitlines()
    query_lower = query.lower()

    for i, line in enumerate(lines):
        if query_lower in line.lower():
            start = max(0, i - context_lines)
            end = min(len(lines), i + context_lines + 1)
            context = "\n".join(lines[start:end])
            matches.append(
                {
                    "line_number": i + 1,
                    "line": line,
                    "context": context,
                    "match_start": line.lower().find(query_lower),
                }
            )

    return matches


def display_chat_message(
    role: str,
    content: str,
    timestamp: Optional[datetime] = None,
    show_timestamp: bool = False,
) -> None:
    """Display a formatted chat message."""
    if role == "user":
        success_style = UIStyles.safe_style("SUCCESS", "green")
        prefix = f"› [{success_style} bold]Você:[/{success_style} bold]"
    else:
        title_style = UIStyles.safe_style("TITLE", "cyan")
        prefix = f"› [{title_style}]Aura:[/{title_style}]"

    if show_timestamp and timestamp:
        time_str = timestamp.strftime("%H:%M:%S")
        prefix += f" [dim]({time_str})[/dim]"

    console.print(f"{prefix} {content}")


from aura_cli.application.execution_feedback import (
    configure_file_edit_presenter,
)

configure_file_edit_presenter(
    lambda *args, **kwargs: display_file_edit(*args, **kwargs)
)
