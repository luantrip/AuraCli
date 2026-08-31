"""
ShellCommandBox - Interactive shell command execution box.

Provides unified visual experience for shell command execution with
real-time feedback and post-execution interactivity.
"""

from enum import Enum
import shlex
import subprocess
import time
from typing import Any, List, Optional

from rich.console import Console, Group, RenderableType
from rich.live import Live
from rich.padding import Padding
from rich.syntax import Syntax
from rich.text import Text

from aura_cli.application.execution_feedback import (
    ShellExecutionView,
    configure_shell_presenter,
)
from aura_cli.cli.ui.components.base import ComponentBase
from aura_cli.cli.ui.components.section_header import AuraSectionHeader
from aura_cli.cli.ui.constants import UIIcons, UIStyles
from aura_cli.cli.ui.layout_contract import layout_for_width


class BoxState(Enum):
    """Enumeration of shell command box states."""

    PENDING = "pending"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ShellCommandBox(ComponentBase):
    """
    Interactive box for shell command execution.

    Manages command lifecycle from confirmation to completion with
    unified visual presentation and real-time output streaming.
    """

    def __init__(self, command: str, background: bool = False):
        """Initialize the instance."""
        self.command = command
        self.background = background
        self.state = BoxState.PENDING
        self.output_lines: List[str] = []
        self.stderr_lines: List[str] = []
        self.exit_code: Optional[int] = None
        self.execution_time: Optional[float] = None
        self.start_time: Optional[float] = None
        self.is_expanded = False

    def _get_header(self) -> str:
        """Get box header based on current state."""
        icons = {
            BoxState.PENDING: UIIcons.WARNING,
            BoxState.EXECUTING: UIIcons.RUN,
            BoxState.COMPLETED: UIIcons.SUCCESS,
            BoxState.FAILED: UIIcons.ERROR,
            BoxState.CANCELLED: UIIcons.CANCEL,
        }

        labels = {
            BoxState.PENDING: "Comando shell",
            BoxState.EXECUTING: "Comando shell (Executando)",
            BoxState.COMPLETED: "Comando shell (Concluído)",
            BoxState.FAILED: "Comando shell (Falhou)",
            BoxState.CANCELLED: "Comando shell (Cancelado)",
        }

        icon = icons.get(self.state, UIIcons.INFO)
        label = labels.get(self.state, "Comando shell")

        return f"{icon} {label}"

    def _get_border_style(self) -> str:
        """Get border style based on current state."""
        styles = {
            BoxState.PENDING: UIStyles.safe_style("WARNING", "yellow"),
            BoxState.EXECUTING: UIStyles.safe_style("INFO", "cyan"),
            BoxState.COMPLETED: UIStyles.safe_style("SUCCESS", "green"),
            BoxState.FAILED: UIStyles.safe_style("ERROR", "red"),
            BoxState.CANCELLED: UIStyles.safe_style("MUTED", "dim white"),
        }
        return styles.get(self.state, "white")

    def _render_command(self) -> Text:
        """Render command line."""
        text = Text()
        text.append("$ ", style=UIStyles.PRIMARY)
        text.append(self.command, style=UIStyles.TITLE)
        return text

    def _render_output(self, max_lines: int = 30) -> RenderableType:
        """Render output section."""
        if not self.output_lines and not self.stderr_lines:
            muted_style = UIStyles.safe_style("MUTED", "dim white")
            return Text("(waiting for output…)", style=muted_style)

        all_lines = self.output_lines + self.stderr_lines

        if not self.is_expanded and len(all_lines) > max_lines:
            display_lines = all_lines[:max_lines]
            truncated = True
        else:
            display_lines = all_lines
            truncated = False

        parts: list[Any] = []

        section_header = AuraSectionHeader()
        if self.state == BoxState.EXECUTING:
            header = section_header.render("Saída ao vivo", style=UIStyles.PRIMARY)
        else:
            header = section_header.render("Saída")
        parts.append(header)
        parts.append(Text())

        output_text = "\n".join(display_lines)
        if output_text.strip():
            syntax = Syntax(
                output_text,
                "bash",
                theme="monokai",
                line_numbers=False,
                word_wrap=True,
            )
            parts.append(syntax)

        if truncated:
            remaining = len(all_lines) - max_lines
            muted_style = UIStyles.safe_style("MUTED", "dim white")
            parts.append(Text())
            parts.append(
                Text(f"  ⋯ {remaining} linhas  [e] expandir", style=muted_style)
            )

        return Group(*parts)

    def _render_footer(self) -> Optional[Text]:
        """Render footer with status info."""
        if self.state not in [
            BoxState.COMPLETED,
            BoxState.FAILED,
            BoxState.CANCELLED,
        ]:
            return None

        text = Text()

        if self.state == BoxState.COMPLETED:
            text.append(
                f"{UIIcons.SUCCESS} Saída {self.exit_code}", style=UIStyles.SUCCESS
            )
        elif self.state == BoxState.CANCELLED:
            text.append(f"{UIIcons.CANCEL} Execução cancelada", style=UIStyles.WARNING)
        else:
            text.append(f"{UIIcons.ERROR} Saída {self.exit_code}", style=UIStyles.ERROR)

        if self.execution_time is not None:
            text.append(f" | {self.execution_time:.2f}s", style=UIStyles.MUTED)

        return text

    def _render_progress(self) -> Text:
        """Render execution progress."""
        if self.state != BoxState.EXECUTING or self.start_time is None:
            return Text()

        elapsed = time.time() - self.start_time

        text = Text()
        text.append(f"{UIIcons.LOADING} Executando… ", style=UIStyles.PRIMARY)
        text.append(f"({elapsed:.1f}s)", style=UIStyles.MUTED)

        return text

    def render(self, console_width: int = 80) -> RenderableType:
        """Render the shell as an open surface with inline state."""
        metrics = layout_for_width(console_width)
        parts: list[Any] = []
        title_style = UIStyles.safe_style("TITLE", "cyan")
        parts.append(Text(self._get_header(), style=f"bold {title_style}"))
        parts.append(self._render_command())
        if metrics.vertical_gap:
            parts.append(Text())

        if self.state == BoxState.EXECUTING:
            parts.append(self._render_progress())
            if metrics.vertical_gap:
                parts.append(Text())

        parts.append(self._render_output(max_lines=metrics.result_preview_lines))

        footer = self._render_footer()
        if footer:
            if metrics.vertical_gap:
                parts.append(Text())
            parts.append(
                Text("─" * min(60, metrics.content_width), style=UIStyles.MUTED)
            )
            parts.append(footer)

        return Padding(Group(*parts), metrics.focus_padding)

    def execute_with_live_output(self, console: Console) -> str:
        """
        Execute command with live output streaming.

        Returns:
            Command output as string
        """
        self.state = BoxState.EXECUTING
        self.start_time = time.time()

        try:
            command_args = shlex.split(self.command)
            if not command_args:
                self.state = BoxState.FAILED
                self.exit_code = -1
                return "Erro: comando vazio após parsing"

            process = subprocess.Popen(
                command_args,
                shell=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
            )

            with Live(
                self.render(console_width=console.width),
                console=console,
                refresh_per_second=4,
            ) as live:
                while True:
                    output = process.stdout.readline() if process.stdout else ""
                    if output:
                        self.output_lines.append(output.rstrip())
                        live.update(self.render(console_width=console.width))

                    if process.poll() is not None:
                        break

                remaining_output = process.stdout.read() if process.stdout else ""
                if remaining_output:
                    for line in remaining_output.splitlines():
                        self.output_lines.append(line.rstrip())

                stderr_output = process.stderr.read() if process.stderr else ""
                if stderr_output:
                    for line in stderr_output.splitlines():
                        self.stderr_lines.append(line.rstrip())

                live.update(self.render(console_width=console.width))

            self.exit_code = process.returncode
            self.execution_time = time.time() - self.start_time

            if self.exit_code == 0:
                self.state = BoxState.COMPLETED
            else:
                self.state = BoxState.FAILED

            console.print(self.render(console_width=console.width))

            output = "\n".join(self.output_lines)
            if self.stderr_lines:
                output += "\n" + "\n".join(self.stderr_lines)

            return output if output else "Command executed with no output."

        except subprocess.TimeoutExpired:
            self.state = BoxState.FAILED
            self.exit_code = -1
            self.execution_time = time.time() - self.start_time
            console.print(self.render(console_width=console.width))
            return "Timeout: comando excedeu o tempo limite"

        except Exception as e:
            self.state = BoxState.FAILED
            self.exit_code = -1
            self.execution_time = (
                time.time() - self.start_time if self.start_time else None
            )
            console.print(self.render(console_width=console.width))
            return f"Error executing command: {e!s}"

    def execute_simple(self, console: Console, timeout: float = 300) -> str:
        """
        Execute command without live output (for fast commands).

        Returns:
            Command output as string
        """
        self.state = BoxState.EXECUTING
        self.start_time = time.time()

        try:
            command_args = shlex.split(self.command)
            if not command_args:
                self.state = BoxState.FAILED
                self.exit_code = -1
                return "Erro: comando vazio após parsing"

            result = subprocess.run(
                command_args,
                shell=False,
                capture_output=True,
                text=True,
                timeout=timeout,
            )

            self.exit_code = result.returncode
            self.execution_time = time.time() - self.start_time

            if result.stdout:
                self.output_lines = result.stdout.splitlines()

            if result.stderr:
                self.stderr_lines = result.stderr.splitlines()

            if self.exit_code == 0:
                self.state = BoxState.COMPLETED
            else:
                self.state = BoxState.FAILED

            console.print(self.render(console_width=console.width))

            output = result.stdout if result.stdout else ""
            if result.stderr:
                output += "\n" + result.stderr

            return output if output else "Command executed with no output."

        except subprocess.TimeoutExpired:
            self.state = BoxState.FAILED
            self.exit_code = -1
            self.execution_time = timeout
            console.print(self.render(console_width=console.width))
            return "Timeout: comando excedeu o tempo limite"

        except Exception as e:
            self.state = BoxState.FAILED
            self.exit_code = -1
            self.execution_time = (
                time.time() - self.start_time if self.start_time else None
            )
            console.print(self.render(console_width=console.width))
            return f"Error executing command: {e!s}"

    def cancel(self):
        """Mark box as cancelled."""
        self.state = BoxState.CANCELLED

    def expand(self):
        """Expand output to show all lines."""
        self.is_expanded = True


def present_shell_execution(console: Console, execution: ShellExecutionView) -> None:
    """Render the neutral execution snapshot with the existing Rich component."""
    box = ShellCommandBox(execution.command, execution.background)
    box.state = BoxState(execution.state.value)
    box.output_lines = list(execution.output_lines)
    box.stderr_lines = list(execution.stderr_lines)
    box.exit_code = execution.exit_code
    box.execution_time = execution.execution_time
    box.start_time = execution.start_time
    console.print(box.render(console_width=console.width))


def register_shell_presenter() -> None:
    """Register this Rich adapter with the presentation-neutral port."""
    configure_shell_presenter(present_shell_execution)


register_shell_presenter()
