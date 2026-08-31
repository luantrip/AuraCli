"""
AppPresenter Module.

This module is responsible for handling the presentation layer of the Aura CLI application.
It decouples UI rendering logic from the main application loop, following the
Model-View-Presenter (MVP) pattern where:
- AppLoop acts as the Controller/Manager
- AppPresenter acts as the View/Presenter
- Core models act as the Model
"""

import os

from rich.console import Console

from aura_cli.cli.ui.components.file_op_summary import FileOperationSummary
from aura_cli.cli.ui.components.message_bubble import (
    MessageBubble,
    MessageMetadata,
    MessageType,
)
from aura_cli.cli.ui.layout_contract import layout_for_width
from aura_cli.cli.ui.manager import UIManager
from aura_cli.core.stats import StatsTracker


class AppPresenter:
    """
    Handles all UI presentation logic for the main application loop.
    Wraps Rich Console and UIManager interactions.
    """

    def __init__(
        self, console: Console, ui_manager: UIManager, stats_tracker: StatsTracker
    ):
        """Initialize the instance."""
        self.console = console
        self.ui = ui_manager
        self.stats = stats_tracker

    def display_constitution(self, constitution_content: str):
        """Displays the project constitution."""
        self.ui.display_info("◇ Constituição do Projeto carregada:")
        from aura_cli.cli.ui.constants import UIStyles

        self.ui.print(f"\n[{UIStyles.MUTED}]{'=' * 60}[/{UIStyles.MUTED}]")
        self.ui.print(f"[{UIStyles.TITLE}]◇ CONSTITUIÇÃO DO PROJETO[/{UIStyles.TITLE}]")
        self.ui.print(f"[{UIStyles.MUTED}]{'=' * 60}[/{UIStyles.MUTED}]")
        self.ui.print(f"[{UIStyles.BODY}]{constitution_content}[/{UIStyles.BODY}]")
        self.ui.print(f"[{UIStyles.MUTED}]{'=' * 60}[/{UIStyles.MUTED}]\n")

    def display_constitution_missing(self):
        """Displays message when constitution is missing."""
        self.ui.display_info("Nenhuma 'Constituição do Projeto' encontrada.")
        self.ui.display_info(
            "Iniciando o Agente Constituição para definir as regras do projeto..."
        )

    def display_llm_response(
        self,
        response_content: str,
        start_time: float,
        response_tokens: int = 0,
        model: str = "",
    ):
        """
        Displays the LLM response and file operation summary.

        Spacing contract (lines between elements):
            [tools]        ← printed by function_call_handler inline
            (1 blank)
            ─── separator
            (0 blank)      ← bubble has internal top padding
            bubble content
            (0 blank)      ← bubble has internal bottom padding
            file summary   ← only if files changed
            (1 blank)
            status footer
        """
        # TUI mode: just send the response text directly
        if getattr(self.ui, "is_tui_mode", False):
            self.ui.display_response(response_content)
            return

        # CLI mode: render with Rich components
        from aura_cli.cli.ui.components.turn_separator import TurnSeparator

        # Separator between tools and response
        separator = TurnSeparator()
        self.ui.print(separator.render(variant="standard"))

        # Response bubble (has internal padding)
        bubble = MessageBubble(
            sender="Aura",
            content=response_content,
            message_type=MessageType.ASSISTANT,
            metadata=MessageMetadata(),
        )
        layout = layout_for_width(self.console.width)
        self.ui.print(bubble.render(layout.width))

        # File operation summary (compact, no extra blank before)
        if self.stats.get_files_changed():
            projected = self.stats.get_turn_files()
            confirmed_created = [f for f in projected["created"] if os.path.exists(f)]
            confirmed_edited = [f for f in projected["edited"] if os.path.exists(f)]
            if confirmed_created or confirmed_edited or projected["read"]:
                summary_component = FileOperationSummary()
                summary_renderable = summary_component.render(
                    files_edited=confirmed_edited,
                    files_created=confirmed_created,
                    files_read=projected["read"],
                )
                self.ui.print(summary_renderable)
            self.stats.clear_file_op_lists()

    @staticmethod
    def _format_tokens_compact(n: int) -> str:
        """Format token count into compact human-readable string.

        Returns:
            Under 1000: "847"
            1000-999999: "1.2k", "45k"
            1M+: "1.2M"
        """
        if n < 1000:
            return str(n)
        elif n < 1_000_000:
            value = n / 1000
            if value < 10:
                formatted = f"{value:.1f}"
                # Strip trailing zero: "1.0" → "1", but keep "1.2"
                if formatted.endswith(".0"):
                    formatted = formatted[:-2]
                return f"{formatted}k"
            return f"{int(value)}k"
        else:
            value = n / 1_000_000
            if value < 10:
                formatted = f"{value:.1f}"
                if formatted.endswith(".0"):
                    formatted = formatted[:-2]
                return f"{formatted}M"
            return f"{int(value)}M"

    def display_status_footer(self, exec_time: float = 0.0, model: str = ""):
        """
        Displays the status footer — single compact line.

        The metrics are stored and rendered by the persistent StatusBar before
        the next prompt; this method intentionally emits no standalone footer.
        """
        try:
            self.ui.record_turn_metrics(exec_time=exec_time, model=model)
        except Exception:
            # Keep compatibility with lightweight test/TUI adapters.
            return
