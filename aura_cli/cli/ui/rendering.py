"""RenderCoordinator - Handles display and rendering.

This module consolidates all rendering logic and high-level display functions.
"""

import inspect
from typing import Any, Optional

from rich.console import Console
from rich.status import Status
from rich.text import Text

from aura_cli.cli.ui.components.error_display import AuraErrorDisplay
from aura_cli.cli.ui.components.investigator_status_bar import AuraInvestigatorStatusBar
from aura_cli.cli.ui.components.investigator_summary import AuraInvestigatorSummary
from aura_cli.cli.ui.components.markdown_display import AuraMarkdownDisplay
from aura_cli.cli.ui.composition.visual_surface import VisualEmitter
from aura_cli.cli.ui.constants import UIIcons, UIStyles
from aura_cli.core.stats import StatsTracker


class StatusManager:
    """Visual state manager for the system."""

    def __init__(self, console: Console, stats: StatsTracker):
        """Initialize the instance."""
        self.console = console
        self.stats = stats
        self._current_status: Optional[Status] = None

    def set_idle(self):
        """Set status to idle."""
        self.stats.set_status("idle")
        if self._current_status:
            self._current_status.stop()
            self._current_status = None

    def set_thinking(self):
        """Set status to thinking with spinner."""
        self.stats.set_status("thinking")
        if self._current_status:
            self._current_status.stop()
        self._current_status = self.console.status(
            f"[bold {UIStyles.STATUS_THINKING}]{UIIcons.THINKING} Raciocinando...[/bold {UIStyles.STATUS_THINKING}]",
            spinner="dots",
        )
        self._current_status.start()

    def set_working(self, message: str = "Processando"):
        """Set status to working with custom message."""
        self.stats.set_status("working", message)
        if self._current_status:
            self._current_status.stop()
        self._current_status = self.console.status(
            f"[bold {UIStyles.STATUS_WORKING}]{UIIcons.WORKING} {message or 'Processando'}...[/bold {UIStyles.STATUS_WORKING}]",
            spinner="dots",
        )
        self._current_status.start()

    def stop(self):
        """Stop current status and set to idle."""
        if self._current_status:
            self._current_status.stop()
            self._current_status = None
        self.set_idle()


class RenderCoordinator:
    """Content rendering coordinator."""

    def __init__(self, console: Console, stats: StatsTracker):
        """Initialize the instance."""
        self.console = console
        self.stats = stats
        self.status = StatusManager(console, stats)
        self.emitter = VisualEmitter(console)

    def render_response(self, content: str, title: str = "Aura"):
        """Render response panel."""
        self.status.stop()
        header = Text(f"{UIIcons.AURA} {title}", style=UIStyles.TITLE)
        self.emitter.emit(header, separate=True)
        self.emitter.emit(AuraMarkdownDisplay().render(content))

    def render_error(self, error: str):
        """Render error panel."""
        self.status.stop()
        error_component = AuraErrorDisplay()
        panel = error_component.render(error_message=error)
        self.emitter.emit(panel, separate=True)

    def render_success(self, message: str):
        """Render success message."""
        self.status.stop()
        line = Text.from_markup(
            f"[{UIStyles.SUCCESS}]{UIIcons.SUCCESS} {message}[/{UIStyles.SUCCESS}]"
        )
        self.emitter.emit(line, separate=True)

    def render_warning(self, message: str):
        """Render warning message."""
        self.status.stop()
        line = Text.from_markup(
            f"[{UIStyles.WARNING}]{UIIcons.WARNING} {message}[/{UIStyles.WARNING}]"
        )
        self.emitter.emit(line, separate=True)

    def render_info(self, message: str):
        """Render info message."""
        self.status.stop()
        line = Text.from_markup(
            f"[{UIStyles.INFO}]{UIIcons.INFO} {message}[/{UIStyles.INFO}]"
        )
        self.emitter.emit(line, separate=True)

    def render_shell_output(self, command: str, success: bool, output: str):
        """Render shell command output via the canonical shell UI entrypoint."""
        self.status.stop()
        from aura_cli.cli.ui.terminal_command import display_run_terminal_command

        display_run_terminal_command(
            command=command,
            output=output,
            status="completed" if success else "failed",
            exit_code=0 if success else 1,
            show_security_warning=True,
            output_console=self.console,
        )

    def display_investigator_progress(self, step: str, status: str):
        """Display codebase investigator progress."""
        self.status.stop()
        status_bar_component = AuraInvestigatorStatusBar()
        status_bar = status_bar_component.render(status=status, current_step=step)
        self.emitter.emit(status_bar, separate=True)

    def display_investigator_summary(self, results: dict):
        """Display the final codebase analysis summary."""
        self.status.stop()
        summary_component = AuraInvestigatorSummary()
        summary = summary_component.render(results.get("summary", {}))
        self.emitter.emit(summary, separate=True)

    def render_component(self, component: Any) -> None:
        """Print a component or Rich renderable."""
        self.status.stop()
        if hasattr(component, "render") and callable(component.render):
            render_method = component.render
            parameters = inspect.signature(render_method).parameters
            if "console_width" in parameters:
                rendered = render_method(console_width=self.console.width)
            else:
                rendered = render_method()
            self.emitter.emit(rendered, separate=True)
        else:
            self.emitter.emit(component, separate=True)
