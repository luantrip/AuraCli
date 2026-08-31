"""Input Bar Widget for Aura TUI.

Fixed bottom input bar for user commands with auto-focus, placeholder,
and command suggestions.

Features:
- Fixed bottom positioning
- Auto-focus on mount
- Placeholder with icon
- Command suggestions dropdown
- History navigation support
- Value property for easy access
"""

from typing import List, Optional

from textual.containers import Container, Vertical
from textual.reactive import reactive
from textual.widgets import Input, OptionList
from textual.widgets.option_list import Option

from aura_cli.application.commands import slash_command_pairs
import aura_cli.tui.constants as tui_constants
from aura_cli.tui.widgets.autocomplete_input import CommandCompletionProvider

# Available slash commands for autocomplete (shared registry)
SLASH_COMMANDS = slash_command_pairs("pt")


class AuraInputBar(Container):
    """Fixed bottom input bar for user commands with suggestions.

    Features:
    - Fixed bottom positioning
    - Auto-focus on mount
    - Placeholder with icon
    - Command suggestions dropdown
    - History navigation (up/down)
    - Value property for easy access
    """

    show_suggestions: reactive[bool] = reactive(False)

    def __init__(self, **kwargs):
        """Initialize the instance."""
        super().__init__(**kwargs)
        self._history: List[str] = []
        self._history_index: int = -1
        self._filtered_commands: List[tuple] = []
        self._completion_provider = CommandCompletionProvider()

    def compose(self):
        """Compose input bar structure."""
        with Vertical():
            yield OptionList(
                id="command_suggestions", classes="command-suggestions -hidden"
            )
            yield Input(
                placeholder=f"{tui_constants.get_glyph('AURA_STAR')} Digite uma pergunta ou /comando...",
                id="main_input",
            )

    def on_mount(self):
        """Focus input on mount."""
        self.query_one(Input).focus()

    def on_input_changed(self, event: Input.Changed) -> None:
        """Handle input changes to show command suggestions."""
        value = event.value

        if value.startswith("/"):
            completions = self._completion_provider.get_completions(
                value, event.input.cursor_position
            )
            self._filtered_commands = [
                (completion.text, completion.description)
                for completion in completions
            ]

            if self._filtered_commands:
                self._update_suggestions()
                self.show_suggestions = True
            else:
                self.show_suggestions = False
        else:
            self.show_suggestions = False
            self._filtered_commands = []

    def _update_suggestions(self) -> None:
        """Update the suggestions list."""
        try:
            option_list = self.query_one("#command_suggestions", OptionList)
            option_list.clear_options()

            for cmd, desc in self._filtered_commands[:6]:  # Limit to 6 suggestions
                option_list.add_option(Option(f"{cmd} - {desc}", id=cmd))
        except Exception as error:
            self.log.debug("Command suggestions are not mounted yet: %s", error)

    def watch_show_suggestions(self, show: bool) -> None:
        """Toggle suggestions visibility."""
        try:
            option_list = self.query_one("#command_suggestions", OptionList)
            if show:
                option_list.remove_class("-hidden")
            else:
                option_list.add_class("-hidden")
        except Exception as error:
            self.log.debug("Suggestion list visibility unavailable: %s", error)

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        """Handle command selection from suggestions."""
        if event.option.id:
            input_widget = self.query_one("#main_input", Input)
            # Set the selected command
            input_widget.value = event.option.id + " "
            input_widget.cursor_position = len(input_widget.value)
            self.show_suggestions = False
            input_widget.focus()

    def add_to_history(self, command: str) -> None:
        """Add a command to the history."""
        if command and (not self._history or command != self._history[-1]):
            self._history.append(command)
            if len(self._history) > 100:  # Limit history size
                self._history.pop(0)
        self._history_index = len(self._history)

    def navigate_history(self, direction: int) -> Optional[str]:
        """Navigate through command history.

        Args:
            direction: -1 for previous, 1 for next

        Returns:
            The command at the new history position, or None
        """
        if not self._history:
            return None

        new_index = self._history_index + direction
        new_index = max(0, min(new_index, len(self._history)))

        self._history_index = new_index

        if 0 <= self._history_index < len(self._history):
            return self._history[self._history_index]

        return None

    @property
    def value(self) -> str:
        """Get current input value."""
        return self.query_one(Input).value

    @value.setter
    def value(self, val: str):
        """Set input value."""
        self.query_one(Input).value = val

    def clear(self) -> None:
        """Clear the input."""
        self.query_one(Input).value = ""
        self.show_suggestions = False

    def focus_input(self) -> None:
        """Focus the input widget."""
        self.query_one(Input).focus()
