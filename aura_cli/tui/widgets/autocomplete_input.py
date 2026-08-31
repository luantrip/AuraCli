"""Enhanced Autocomplete Input for Aura TUI.

Advanced input widget with fuzzy matching and contextual suggestions.

Features:
- Command autocomplete with fuzzy matching
- Subcommand suggestions based on context
- File path completion
- History-based suggestions
- Contextual relevance scoring
- Clear visual cues and keyboard navigation
- Parameter hints display

Components:
- CompletionItem: Suggestion metadata
- Fuzzy matching algorithm
- Context-aware filtering
"""

from dataclasses import dataclass
from typing import ClassVar, List, Optional

from textual.app import ComposeResult
from textual.binding import Binding
from textual.message import Message
from textual.reactive import reactive
from textual.widgets import Input, OptionList, Static


@dataclass
class CompletionItem:
    """A single completion item."""

    text: str
    description: str = ""
    category: str = "command"
    icon: str = ""
    score: float = 0.0

    @property
    def display(self) -> str:
        """Get display string."""
        icon = self.icon or self._default_icon()
        return f"{icon} {self.text}"

    def _default_icon(self) -> str:
        """Get default icon based on category."""
        icons = {
            "command": "⌘",
            "subcommand": "↳",
            "file": "◇",
            "directory": "▷",
            "history": "◇",
            "parameter": "⚙",
            "tool": "⚒",
            "agi": "◈",
        }
        return icons.get(self.category, "•")


class CompletionProvider:
    """Base class for completion providers."""

    def get_completions(self, text: str, cursor_pos: int) -> List[CompletionItem]:
        """Get completions for given text and cursor position."""
        raise NotImplementedError


class CommandCompletionProvider(CompletionProvider):
    """Provides command completions for Aura CLI."""

    @staticmethod
    def _commands() -> dict:
        from aura_cli.application.commands import command_dict_for_autocomplete

        return command_dict_for_autocomplete("pt")

    def get_completions(self, text: str, cursor_pos: int) -> List[CompletionItem]:
        """Get command completions."""
        completions = []
        text_lower = text.lower().strip()
        commands = self._commands()

        # Check for subcommand context
        parts = text_lower.split()

        if len(parts) == 0 or (len(parts) == 1 and not text.endswith(" ")):
            # Complete main command
            query = parts[0] if parts else ""
            for cmd, info in commands.items():
                if self._fuzzy_match(cmd, query):
                    score = self._calculate_score(cmd, query)
                    completions.append(
                        CompletionItem(
                            text=cmd,
                            description=str(info["desc"]) if info.get("desc") else "",
                            category="command",
                            score=score,
                        )
                    )

        elif len(parts) >= 1:
            # Complete subcommand
            main_cmd = parts[0]
            if main_cmd in commands:
                subcommands = commands[main_cmd]["subcommands"]
                query = parts[1] if len(parts) > 1 and not text.endswith(" ") else ""

                for sub in subcommands:
                    if self._fuzzy_match(sub, query):
                        score = self._calculate_score(sub, query)
                        completions.append(
                            CompletionItem(
                                text=f"{main_cmd} {sub}",
                                description=f"{main_cmd} → {sub}",
                                category="subcommand",
                                score=score,
                            )
                        )

        # Sort by score
        completions.sort(key=lambda x: x.score, reverse=True)
        return completions[:10]

    def _fuzzy_match(self, target: str, query: str) -> bool:
        """Check if query fuzzy matches target."""
        if not query:
            return True

        query_lower = query.lower()
        target_lower = target.lower()

        # Exact prefix match
        if target_lower.startswith(query_lower):
            return True

        # Contains match
        if query_lower in target_lower:
            return True

        # Fuzzy subsequence match
        qi = 0
        for char in target_lower:
            if qi < len(query_lower) and char == query_lower[qi]:
                qi += 1

        return qi == len(query_lower)

    def _calculate_score(self, target: str, query: str) -> float:
        """Calculate match score."""
        if not query:
            return 0.5

        query_lower = query.lower()
        target_lower = target.lower()

        # Exact match
        if target_lower == query_lower:
            return 1.0

        # Prefix match
        if target_lower.startswith(query_lower):
            return 0.9 + (len(query) / len(target)) * 0.1

        # Contains match
        if query_lower in target_lower:
            return 0.7 + (len(query) / len(target)) * 0.1

        # Fuzzy match
        return 0.5


class HistoryCompletionProvider(CompletionProvider):
    """Provides history-based completions."""

    def __init__(self, max_history: int = 100):
        """Initialize the instance."""
        self.history: List[str] = []
        self.max_history = max_history

    def add_to_history(self, command: str) -> None:
        """Add command to history."""
        if command and command not in self.history:
            self.history.insert(0, command)
            if len(self.history) > self.max_history:
                self.history.pop()

    def get_completions(self, text: str, cursor_pos: int) -> List[CompletionItem]:
        """Get history completions."""
        completions = []
        text_lower = text.lower().strip()

        for cmd in self.history[:20]:
            if not text or text_lower in cmd.lower():
                completions.append(
                    CompletionItem(
                        text=cmd,
                        description="From history",
                        category="history",
                        score=0.4,
                    )
                )

        return completions


class AutocompleteInput(Static):
    """
    Enhanced input with autocomplete dropdown.

    Features:
    - Real-time completion suggestions
    - Fuzzy matching
    - Keyboard navigation
    - Multiple completion providers
    """

    BINDINGS: ClassVar[list] = [
        Binding("tab", "complete", "Complete", show=False),
        Binding("escape", "hide_completions", "Hide", show=False),
        Binding("up", "prev_completion", "Previous", show=False),
        Binding("down", "next_completion", "Next", show=False),
    ]

    # Reactive state
    show_completions = reactive(False)
    selected_index = reactive(0)

    class CommandSubmitted(Message):
        """Emitted when command is submitted."""

        def __init__(self, command: str):
            """Initialize the instance."""
            super().__init__()
            self.command = command

    class CompletionSelected(Message):
        """Emitted when completion is selected."""

        def __init__(self, completion: CompletionItem):
            """Initialize the instance."""
            super().__init__()
            self.completion = completion

    def __init__(
        self,
        placeholder: str = "Type a command...",
        providers: Optional[List[CompletionProvider]] = None,
        **kwargs,
    ):
        """Initialize the instance."""
        super().__init__(**kwargs)
        self.placeholder = placeholder
        self.providers = providers or [
            CommandCompletionProvider(),
            HistoryCompletionProvider(),
        ]
        self.completions: List[CompletionItem] = []
        self._history_provider = next(
            (p for p in self.providers if isinstance(p, HistoryCompletionProvider)),
            None,
        )

    def compose(self) -> ComposeResult:
        """Compose the widget layout."""
        yield Input(placeholder=self.placeholder, id="autocomplete_input")
        yield OptionList(id="completion_list", classes="completion-list -hidden")
        yield Static("", id="completion_hint", classes="completion-hint")

    def on_input_changed(self, event: Input.Changed) -> None:
        """Handle input changes."""
        if event.input.id == "autocomplete_input":
            self._update_completions(event.value)

    def _update_completions(self, text: str) -> None:
        """Update completion list."""
        self.completions = []

        # Get completions from all providers
        for provider in self.providers:
            self.completions.extend(provider.get_completions(text, len(text)))

        # Sort by score and deduplicate
        seen = set()
        unique_completions = []
        for comp in sorted(self.completions, key=lambda x: x.score, reverse=True):
            if comp.text not in seen:
                seen.add(comp.text)
                unique_completions.append(comp)

        self.completions = unique_completions[:10]

        # Update UI
        completion_list = self.query_one("#completion_list", OptionList)
        completion_list.clear_options()

        if self.completions and text:
            for comp in self.completions:
                # Use plain string with separator - styling via CSS
                display_text = f"{comp.display}  {comp.description}"
                completion_list.add_option(display_text)

            completion_list.remove_class("-hidden")
            self.show_completions = True
            self.selected_index = 0

            # Update hint - plain text, styling via CSS
            hint = self.query_one("#completion_hint", Static)
            hint.update("Tab to complete • ↑↓ to navigate • Esc to close")
        else:
            completion_list.add_class("-hidden")
            self.show_completions = False

            hint = self.query_one("#completion_hint", Static)
            hint.update("")

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle input submission."""
        if event.input.id == "autocomplete_input":
            command = event.value.strip()

            if command:
                # Add to history
                if self._history_provider:
                    self._history_provider.add_to_history(command)

                # Clear input
                event.input.value = ""

                # Hide completions
                self._hide_completions()

                # Emit event
                self.post_message(self.CommandSubmitted(command))

    def action_complete(self) -> None:
        """Complete with selected item."""
        if self.show_completions and self.completions:
            completion = self.completions[self.selected_index]

            input_widget = self.query_one("#autocomplete_input", Input)
            input_widget.value = completion.text
            input_widget.cursor_position = len(completion.text)

            self._hide_completions()
            self.post_message(self.CompletionSelected(completion))

    def action_hide_completions(self) -> None:
        """Hide completion list."""
        self._hide_completions()

    def action_prev_completion(self) -> None:
        """Select previous completion."""
        if self.show_completions and self.completions:
            self.selected_index = (self.selected_index - 1) % len(self.completions)
            self._highlight_selection()

    def action_next_completion(self) -> None:
        """Select next completion."""
        if self.show_completions and self.completions:
            self.selected_index = (self.selected_index + 1) % len(self.completions)
            self._highlight_selection()

    def _hide_completions(self) -> None:
        """Hide completion list."""
        completion_list = self.query_one("#completion_list", OptionList)
        completion_list.add_class("-hidden")
        self.show_completions = False

        hint = self.query_one("#completion_hint", Static)
        hint.update("")

    def _highlight_selection(self) -> None:
        """Highlight selected completion."""
        completion_list = self.query_one("#completion_list", OptionList)
        if self.selected_index < len(self.completions):
            completion_list.highlighted = self.selected_index

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        """Handle option selection from list."""
        if event.option_list.id == "completion_list":
            idx = event.option_index
            if 0 <= idx < len(self.completions):
                completion = self.completions[idx]

                input_widget = self.query_one("#autocomplete_input", Input)
                input_widget.value = completion.text
                input_widget.cursor_position = len(completion.text)

                self._hide_completions()
                self.post_message(self.CompletionSelected(completion))

    @property
    def value(self) -> str:
        """Get current input value."""
        return self.query_one("#autocomplete_input", Input).value

    @value.setter
    def value(self, val: str) -> None:
        """Set input value."""
        self.query_one("#autocomplete_input", Input).value = val

    def focus(self) -> None:  # type: ignore[override]
        """Focus the input."""
        self.query_one("#autocomplete_input", Input).focus()

    def add_to_history(self, command: str) -> None:
        """Add command to history."""
        if self._history_provider:
            self._history_provider.add_to_history(command)
