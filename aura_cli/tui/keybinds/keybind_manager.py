"""
Keybind Manager for Aura TUI.

Implements an advanced keybinding system with:
- Leader key support for multi-key sequences
- Context-aware bindings
- Configurable shortcuts
- Visual feedback
"""

from __future__ import annotations

import contextlib
from dataclasses import dataclass, field
import logging
import re
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional

from aura_cli.tui.core.event_bus import TUIEvents

if TYPE_CHECKING:
    from textual import events
    from textual.app import App

logger = logging.getLogger(__name__)


@dataclass
class KeybindInfo:
    """Information about a keybinding."""

    key: str  # e.g., "ctrl+s", "<leader> a"
    action: str  # Action identifier
    description: str
    callback: Optional[Callable] = None
    category: str = "general"
    show_in_help: bool = True
    requires_leader: bool = False
    context: Optional[str] = None  # e.g., "input", "chat", "global"

    @property
    def display_key(self) -> str:
        """Get display-friendly key representation."""
        key = self.key
        key = key.replace("ctrl+", "Ctrl+")
        key = key.replace("alt+", "Alt+")
        key = key.replace("shift+", "Shift+")
        key = key.replace("<leader>", "Leader")
        return key


@dataclass
class LeaderState:
    """State of the leader key mode."""

    active: bool = False
    sequence: List[str] = field(default_factory=list)
    started_at: Optional[float] = None
    previous_focus: Optional[Any] = None


class LeaderKeyManager:
    """
    Manages the leader key mode for multi-key sequences.

    The leader key (default: Ctrl+Space) enables multi-key sequences:
    - Press leader key to enter leader mode
    - Press additional keys to complete the sequence
    - Sequences timeout after a configurable duration

    Example:
        ```
        <leader> a  -> Show agents
        <leader> m  -> Show models
        <leader> t  -> Show tools
        <leader> h  -> Show help
        ```
    """

    DEFAULT_LEADER_KEY = "ctrl+space"
    DEFAULT_TIMEOUT = 2.0  # seconds

    def __init__(self, app: App):
        """
        Initialize the leader key manager.

        Args:
            app: Textual App instance
        """
        self.app = app
        self.leader_key = self.DEFAULT_LEADER_KEY
        self.timeout = self.DEFAULT_TIMEOUT
        self.state = LeaderState()

        self._sequences: Dict[str, KeybindInfo] = {}
        self._timer = None

    def register_sequence(self, sequence: str, keybind: KeybindInfo) -> None:
        """
        Register a leader key sequence.

        Args:
            sequence: Key sequence after leader (e.g., "a" for <leader> a)
            keybind: Keybind information
        """
        keybind.requires_leader = True
        self._sequences[sequence.lower()] = keybind
        logger.debug(f"Registered leader sequence: <leader> {sequence}")

    def is_leader_key(self, key: str) -> bool:
        """Check if key is the leader key."""
        return self._normalize_key(key) == self._normalize_key(self.leader_key)

    def enter_leader_mode(self) -> None:
        """Enter leader key mode."""
        import time

        self.state.active = True
        self.state.sequence = []
        self.state.started_at = time.time()

        try:
            if self.app.focused:
                self.state.previous_focus = self.app.focused
                self.app.focused.blur()
        except Exception as error:
            logger.debug("Unable to preserve focus for leader mode: %s", error)

        self._cancel_timer()
        self._timer = self.app.set_timer(self.timeout, self._on_timeout)  # type: ignore[assignment]

        self.app.notify(
            "Leader mode: waiting for key...",
            severity="information",
            timeout=self.timeout,
        )

        TUIEvents.bus.publish("tui.leader.mode", {"active": True, "sequence": []})

        logger.debug("Entered leader mode")

    def exit_leader_mode(self, execute: bool = False) -> None:
        """
        Exit leader key mode.

        Args:
            execute: Whether to execute the sequence (vs cancel)
        """
        self._cancel_timer()

        sequence_str = "".join(self.state.sequence)
        was_active = self.state.active

        self.state.active = False
        self.state.sequence = []
        self.state.started_at = None

        if self.state.previous_focus:
            with contextlib.suppress(Exception):
                self.state.previous_focus.focus()
            self.state.previous_focus = None

        TUIEvents.bus.publish("tui.leader.mode", {"active": False, "sequence": []})

        if was_active:
            logger.debug(
                f"Exited leader mode (execute={execute}, sequence='{sequence_str}')"
            )

    def handle_key(self, key: str) -> bool:
        """
        Handle a key press in leader mode.

        Args:
            key: The key that was pressed

        Returns:
            True if key was handled
        """
        if not self.state.active:
            return False

        normalized = self._normalize_key(key)

        if normalized == "escape":
            self.exit_leader_mode(execute=False)
            return True

        self.state.sequence.append(normalized)
        sequence_str = "".join(self.state.sequence)

        if sequence_str in self._sequences:
            keybind = self._sequences[sequence_str]
            self.exit_leader_mode(execute=True)

            if keybind.callback:
                try:
                    keybind.callback()
                except Exception as e:
                    logger.error(f"Leader sequence callback error: {e}")
                    self.app.notify(f"Error: {e}", severity="error")
            else:
                TUIEvents.bus.publish(
                    "tui.command.execute", {"command": keybind.action, "args": {}}
                )

            return True

        has_potential_match = any(
            seq.startswith(sequence_str) and seq != sequence_str
            for seq in self._sequences
        )

        if not has_potential_match:
            self.app.notify(
                f"Unknown sequence: <leader> {sequence_str}",
                severity="warning",
                timeout=2,
            )
            self.exit_leader_mode(execute=False)
            return True

        self.app.notify(
            f"Leader: {sequence_str}...", severity="information", timeout=self.timeout
        )

        TUIEvents.bus.publish(
            "tui.leader.mode", {"active": True, "sequence": self.state.sequence}
        )

        return True

    def stop(self) -> None:
        """Stop leader mode and release its timeout timer safely."""
        if self.state.active:
            self.exit_leader_mode(execute=False)
        else:
            self._cancel_timer()
            self.state.previous_focus = None

    def _on_timeout(self) -> None:
        """Handle leader mode timeout."""
        if self.state.active:
            sequence_str = (
                "".join(self.state.sequence) if self.state.sequence else "(none)"
            )
            self.app.notify(
                f"Leader mode timed out. Sequence: {sequence_str}",
                severity="warning",
                timeout=2,
            )
            self.exit_leader_mode(execute=False)

    def _cancel_timer(self) -> None:
        """Cancel the timeout timer."""
        if self._timer:
            self._timer.stop()
            self._timer = None

    def _normalize_key(self, key: str) -> str:
        """Normalize a key string for comparison."""
        return key.lower().strip()

    def get_sequences(self) -> Dict[str, KeybindInfo]:
        """Get all registered sequences."""
        return self._sequences.copy()

    def get_help_text(self) -> str:
        """Get help text for leader sequences."""
        if not self._sequences:
            return "No leader key sequences registered."

        lines = [f"Leader Key: {self.leader_key}", ""]

        by_category: Dict[str, List[KeybindInfo]] = {}
        for kb in self._sequences.values():
            by_category.setdefault(kb.category, []).append(kb)

        for category, keybinds in sorted(by_category.items()):
            lines.append(f"## {category.title()}")
            for kb in keybinds:
                seq = kb.key.replace("<leader> ", "")
                lines.append(f"  <leader> {seq}  - {kb.description}")
            lines.append("")

        return "\n".join(lines)


class KeybindManager:
    """Central keybinding manager for the TUI.

    Handles direct keybindings (e.g. Ctrl+S), leader-key sequences
    (e.g. <leader> a), context-specific bindings and plugin-provided
    bindings. Call handle_key(event) to dispatch; returns True if the
    event was consumed.
    """

    def __init__(self, app: App):
        """
        Initialize the keybind manager.

        Args:
            app: Textual App instance
        """
        self.app = app
        self.leader = LeaderKeyManager(app)

        self._keybinds: Dict[str, KeybindInfo] = {}
        self._context_keybinds: Dict[str, Dict[str, KeybindInfo]] = {}
        self._current_context: Optional[str] = None

    def stop(self) -> None:
        """Stop transient keybinding state owned by this manager."""
        self.leader.stop()

    def register(self, keybind: KeybindInfo) -> None:
        """
        Register a keybinding.

        Args:
            keybind: Keybind information
        """
        if "<leader>" in keybind.key.lower():
            match = re.search(r"<leader>\s*(.+)", keybind.key, re.IGNORECASE)
            if match:
                sequence = match.group(1).strip()
                self.leader.register_sequence(sequence, keybind)
        else:
            normalized = self._normalize_key(keybind.key)

            if keybind.context:
                self._context_keybinds.setdefault(keybind.context, {})[normalized] = (
                    keybind
                )
            else:
                self._keybinds[normalized] = keybind

        logger.debug(f"Registered keybind: {keybind.key} -> {keybind.action}")

    def unregister(self, key: str) -> bool:
        """
        Unregister a keybinding.

        Args:
            key: Key to unregister

        Returns:
            True if keybind existed
        """
        normalized = self._normalize_key(key)

        if normalized in self._keybinds:
            del self._keybinds[normalized]
            return True

        for context_binds in self._context_keybinds.values():
            if normalized in context_binds:
                del context_binds[normalized]
                return True

        return False

    def handle_key(self, event: events.Key) -> bool:
        """
        Handle a key event.

        Args:
            event: Textual Key event

        Returns:
            True if event was handled
        """
        key = self._event_to_key_string(event)

        if self.leader.state.active:
            return self.leader.handle_key(key)

        if self.leader.is_leader_key(key):
            self.leader.enter_leader_mode()
            return True

        if self._current_context and self._current_context in self._context_keybinds:
            context_binds = self._context_keybinds[self._current_context]
            keybind = context_binds.get(self._normalize_key(key))
            if keybind:
                return self._execute_keybind(keybind)

        keybind = self._keybinds.get(self._normalize_key(key))
        if keybind:
            return self._execute_keybind(keybind)

        return False

    def _execute_keybind(self, keybind: KeybindInfo) -> bool:
        """Execute a keybinding."""
        if keybind.callback:
            try:
                keybind.callback()
                return True
            except Exception as e:
                logger.error(f"Keybind callback error: {e}")
                self.app.notify(f"Error: {e}", severity="error")
                return False
        else:
            TUIEvents.bus.publish(
                "tui.command.execute", {"command": keybind.action, "args": {}}
            )
            return True

    def set_context(self, context: Optional[str]) -> None:
        """
        Set the current keybinding context.

        Args:
            context: Context name or None for global
        """
        self._current_context = context

    def get_keybinds(
        self,
        context: Optional[str] = None,
        category: Optional[str] = None,
        include_leader: bool = True,
    ) -> List[KeybindInfo]:
        """
        Get registered keybindings.

        Args:
            context: Filter by context
            category: Filter by category
            include_leader: Include leader sequences

        Returns:
            List of KeybindInfo
        """
        result = []

        for kb in self._keybinds.values():
            if category and kb.category != category:
                continue
            if kb.show_in_help:
                result.append(kb)

        if context and context in self._context_keybinds:
            for kb in self._context_keybinds[context].values():
                if category and kb.category != category:
                    continue
                if kb.show_in_help:
                    result.append(kb)

        if include_leader:
            for kb in self.leader.get_sequences().values():
                if category and kb.category != category:
                    continue
                if kb.show_in_help:
                    result.append(kb)

        return result

    def get_help_text(self) -> str:
        """Get formatted help text for all keybindings."""
        lines = ["# Keyboard Shortcuts", ""]

        by_category: Dict[str, List[KeybindInfo]] = {}
        for kb in self.get_keybinds():
            by_category.setdefault(kb.category, []).append(kb)

        for category, keybinds in sorted(by_category.items()):
            lines.append(f"## {category.title()}")
            lines.append("")

            for kb in sorted(keybinds, key=lambda x: x.key):
                lines.append(f"  {kb.display_key:<20} {kb.description}")

            lines.append("")

        return "\n".join(lines)

    def _event_to_key_string(self, event: events.Key) -> str:
        """Convert Textual key event to key string."""
        parts = []

        if event.key.startswith("ctrl+"):
            return event.key

        if hasattr(event, "ctrl") and event.ctrl:
            parts.append("ctrl")
        if hasattr(event, "alt") and event.alt:
            parts.append("alt")
        if hasattr(event, "shift") and event.shift:
            parts.append("shift")

        key_name = event.key if hasattr(event, "key") else str(event.character or "")

        if parts:
            parts.append(key_name)
            return "+".join(parts)

        return key_name

    def _normalize_key(self, key: str) -> str:
        """Normalize a key string for comparison."""
        key = key.lower()
        key = key.replace("control+", "ctrl+")
        key = key.replace("option+", "alt+")
        key = key.replace("command+", "meta+")
        key = key.replace("cmd+", "meta+")

        return key
