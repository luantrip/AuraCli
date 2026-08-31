"""Command Palette Widget for Aura TUI.

VS Code/Sublime Text style command palette for quick access to all commands.

Features:
- Fuzzy search filtering with real-time results
- Keyboard navigation (arrow keys, enter)
- Keybind display for each command
- Command categories and grouping
- Recent commands history
- Icon support for visual identification

Components:
- Command: Command metadata dataclass
- Fuzzy matching algorithm
- Category-based organization
- Keyboard shortcuts integration
"""

from __future__ import annotations

from dataclasses import dataclass
import logging
from typing import Callable, ClassVar, Dict, List, Optional

from textual import on
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.message import Message
from textual.reactive import reactive
from textual.widgets import Input, OptionList, Static
from textual.widgets.option_list import Option

from aura_cli.tui.core.event_bus import TUIEvents

logger = logging.getLogger(__name__)


@dataclass
class Command:
    """Represents a command in the palette."""

    id: str
    name: str
    description: str = ""
    keybind: str = ""
    icon: str = ""
    category: str = "general"
    callback: Optional[Callable] = None
    enabled: bool = True
    recently_used: int = 0  # Counter for sorting

    @property
    def display_name(self) -> str:
        """Get display name with icon."""
        icon = self.icon or self._default_icon()
        return f"{icon} {self.name}"

    def _default_icon(self) -> str:
        """Get default icon based on category."""
        icons = {
            "general": "⌘",
            "navigation": "→",
            "dialogs": "◇",
            "panels": "▣",
            "session": "⊙",
            "theme": "◐",
            "clipboard": "⊞",
            "tools": "⚒",
            "agent": "◈",
        }
        return icons.get(self.category, "•")


class CommandRegistry:
    """
    Registry of all available commands.

    Commands can be registered from various sources:
    - Built-in commands
    - Keybind configurations
    - Plugins
    """

    def __init__(self):
        """Initialize the instance."""
        self._commands: Dict[str, Command] = {}
        self._recent: List[str] = []
        self._max_recent = 10

    def register(self, command: Command) -> None:
        """Register a command."""
        self._commands[command.id] = command
        logger.debug(f"Registered command: {command.id}")

    def unregister(self, command_id: str) -> bool:
        """Unregister a command."""
        if command_id in self._commands:
            del self._commands[command_id]
            return True
        return False

    def get(self, command_id: str) -> Optional[Command]:
        """Get a command by ID."""
        return self._commands.get(command_id)

    def all_commands(self) -> List[Command]:
        """Get all registered commands."""
        return list(self._commands.values())

    def search(self, query: str) -> List[Command]:
        """
        Search commands with fuzzy matching.

        Args:
            query: Search query

        Returns:
            Matching commands sorted by relevance
        """
        if not query:
            return self._get_sorted_commands()

        query_lower = query.lower()
        results = []

        for cmd in self._commands.values():
            if not cmd.enabled:
                continue

            score = self._calculate_match_score(cmd, query_lower)
            if score > 0:
                results.append((score, cmd))

        results.sort(key=lambda x: (-x[0], x[1].name))
        return [cmd for _, cmd in results]

    def _calculate_match_score(self, cmd: Command, query: str) -> float:
        """Calculate match score for a command."""
        score = 0.0

        name_lower = cmd.name.lower()
        desc_lower = cmd.description.lower()
        id_lower = cmd.id.lower()

        if query in (name_lower, id_lower):
            score += 100

        if name_lower.startswith(query):
            score += 50
        if id_lower.startswith(query):
            score += 40

        if query in name_lower:
            score += 30
        if query in desc_lower:
            score += 20
        if query in id_lower:
            score += 15

        if self._is_subsequence(query, name_lower):
            score += 10

        if cmd.id in self._recent:
            rank = self._recent.index(cmd.id)
            score += (self._max_recent - rank) * 2

        return score

    def _is_subsequence(self, query: str, target: str) -> bool:
        """Check if query is a subsequence of target."""
        qi = 0
        for char in target:
            if qi < len(query) and char == query[qi]:
                qi += 1
        return qi == len(query)

    def _get_sorted_commands(self) -> List[Command]:
        """Get commands sorted by recent usage."""
        commands = [c for c in self._commands.values() if c.enabled]

        def sort_key(cmd):
            """Return a sort key for ordering palette items."""
            if cmd.id in self._recent:
                return (0, self._recent.index(cmd.id), cmd.name)
            return (1, 0, cmd.name)

        commands.sort(key=sort_key)
        return commands

    def mark_used(self, command_id: str) -> None:
        """Mark a command as recently used."""
        if command_id in self._recent:
            self._recent.remove(command_id)
        self._recent.insert(0, command_id)

        if len(self._recent) > self._max_recent:
            self._recent = self._recent[: self._max_recent]

    def get_by_category(self, category: str) -> List[Command]:
        """Get commands in a category."""
        return [
            c for c in self._commands.values() if c.category == category and c.enabled
        ]

    def get_categories(self) -> List[str]:
        """Get all categories with commands."""
        return list({c.category for c in self._commands.values() if c.enabled})


class CommandPalette(Static):
    """
    Command palette widget for quick command access.

    Triggered by Ctrl+P or Ctrl+K, provides a searchable
    list of all available commands.

    Example:
        ```python
        palette = CommandPalette(registry=command_registry)
        app.mount(palette)

        # Show palette
        palette.show()

        # Hide palette
        palette.hide()
        ```
    """

    class CommandSelected(Message):
        """Emitted when a command is selected."""

        def __init__(self, command: Command):
            """Initialize the instance."""
            super().__init__()
            self.command = command

    class Toggle(Message):
        """Posted to toggle the command palette's visibility."""

    BINDINGS: ClassVar[list] = [
        Binding("escape", "close", "Fechar", show=False),
        Binding("enter", "execute", "Executar", show=False),
    ]

    is_visible = reactive(False)

    def __init__(self, registry: Optional[CommandRegistry] = None, **kwargs):
        """
        Initialize the command palette.

        Args:
            registry: Command registry (creates new if not provided)
        """
        super().__init__(**kwargs)
        self.registry = registry or CommandRegistry()
        self._filtered_commands: List[Command] = []

    def compose(self) -> ComposeResult:
        """Compose the palette UI."""
        with Vertical(classes="palette-input"):
            yield Input(
                placeholder="> Digite para buscar comandos...", id="palette_search"
            )
        yield OptionList(id="palette_list", classes="palette-list")
        yield Static("↑↓ Navegar  Enter Selecionar  Esc Fechar", classes="palette-hint")

    def on_mount(self) -> None:
        """Set up the palette."""
        self._update_list("")

    @on(Toggle)
    def on_toggle(self, event: Toggle) -> None:
        """Handle the Toggle message."""
        self.toggle()

    def on_input_changed(self, event: Input.Changed) -> None:
        """Handle search input changes."""
        if event.input.id == "palette_search":
            self._update_list(event.value)

    def _update_list(self, query: str) -> None:
        """Update the command list based on query."""
        self._filtered_commands = self.registry.search(query)

        option_list = self.query_one("#palette_list", OptionList)
        option_list.clear_options()

        for cmd in self._filtered_commands[:20]:
            parts = [cmd.display_name]

            if cmd.description:
                parts.append(f"  {cmd.description}")

            if cmd.keybind:
                parts.append(f"  [{cmd.keybind}]")

            option_text = "".join(parts)
            option_list.add_option(Option(option_text, id=cmd.id))

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        """Handle option selection."""
        if event.option_list.id == "palette_list" and event.option_id:
            self._execute_command(event.option_id)

    def _execute_command(self, command_id: str) -> None:
        """Execute a command."""
        cmd = self.registry.get(command_id)
        if not cmd:
            return

        self.registry.mark_used(command_id)
        self.hide()

        if cmd.callback:
            try:
                cmd.callback()
            except Exception as e:
                logger.error(f"Command execution error: {e}")
                self.app.notify(f"Error: {e}", severity="error")
        else:
            TUIEvents.bus.publish(
                "tui.command.execute", {"command": cmd.id, "args": {}}
            )

        self.post_message(self.CommandSelected(cmd))

    def action_execute(self) -> None:
        """Execute currently highlighted command."""
        option_list = self.query_one("#palette_list", OptionList)
        if option_list.highlighted is not None and self._filtered_commands:
            idx = option_list.highlighted
            if 0 <= idx < len(self._filtered_commands):
                self._execute_command(self._filtered_commands[idx].id)

    def action_close(self) -> None:
        """Close the palette."""
        self.hide()

    def show(self) -> None:
        """Show the command palette."""
        self.add_class("-visible")
        self.is_visible = True

        search_input = self.query_one("#palette_search", Input)
        search_input.value = ""
        search_input.focus()
        self._update_list("")

    def hide(self) -> None:
        """Hide the command palette and return focus to the composer."""
        was_visible = self.is_visible
        self.remove_class("-visible")
        self.is_visible = False

        if was_visible:
            restore_focus = getattr(
                getattr(self, "app", None), "_restore_composer_focus", None
            )
            if callable(restore_focus):
                restore_focus()

    def toggle(self) -> None:
        """Toggle palette visibility."""
        if self.is_visible:
            self.hide()
        else:
            self.show()


_global_registry: Optional[CommandRegistry] = None


def get_command_registry() -> CommandRegistry:
    """Get the global command registry."""
    global _global_registry
    if _global_registry is None:
        _global_registry = CommandRegistry()
    return _global_registry


def register_command(command: Command) -> None:
    """Register a command in the global registry."""
    get_command_registry().register(command)
