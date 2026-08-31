"""Footer Widget for Aura TUI.

IDE-style footer bar showing keybindings, current mode, and status information.
"""

import logging
from typing import Any, ClassVar

from textual.containers import Horizontal
from textual.reactive import reactive
from textual.widgets import Label, Static

from aura_cli.application.presentation.external_tools import (
    ExternalToolPhase,
    ExternalToolSession,
)
from aura_cli.application.presentation.tui_runtime_state import (
    RuntimePhase,
    TuiRuntimeState,
)
import aura_cli.tui.constants as tui_constants

logger = logging.getLogger(__name__)


class AuraFooter(Static):
    """IDE-style footer bar with keybindings, mode, and status.

    Features:
    - Keybinding display with visual key hints
    - Current mode indicator (NORMAL, INSERT, AGI, OPS)
    - Status message area with auto-clear
    - Active agent indicator
    - Contextual information
    """

    mode: reactive[str] = reactive("NORMAL")
    status_message: reactive[str] = reactive("Pronto")
    runtime_phase: reactive[str] = reactive(RuntimePhase.READY.value)
    active_agent: reactive[str] = reactive("")
    model_name: reactive[str] = reactive("")

    _RUNTIME_CLASSES = tuple(f"runtime-{phase.value}" for phase in RuntimePhase)
    _EXTERNAL_TOOL_CLASSES = tuple(
        f"external-tool-{phase.value}" for phase in ExternalToolPhase
    )
    _EXTERNAL_PHASE_LABELS: ClassVar[dict[ExternalToolPhase, str]] = {
        ExternalToolPhase.SUSPENDING: "preparando",
        ExternalToolPhase.LAUNCHING: "abrindo",
        ExternalToolPhase.ATTACHED: "aberta",
        ExternalToolPhase.RETURNING: "retornando",
        ExternalToolPhase.COMPLETED: "concluída",
        ExternalToolPhase.FAILED: "falhou",
        ExternalToolPhase.INTERRUPTED: "interrompida",
    }

    # Fallback keybindings shown when KeybindManager is not yet available.
    # Once the app registers a KeybindManager, call update_keybindings() and
    # these defaults are replaced with the real registered shortcuts.
    KEYBINDINGS: ClassVar[list[tuple[str, str]]] = [
        ("Shift+Tab", "modo"),
        ("Ctrl+.", "atalhos"),
    ]

    def __init__(self, **kwargs):
        """Initialize footer state and timer ownership."""
        super().__init__(**kwargs)
        self._status_timer: Any | None = None
        # Live keybindings list — starts as a copy of the class-level default
        # so each instance is independent and can be updated at runtime.
        self._keybindings: list[tuple[str, str]] = list(self.KEYBINDINGS)

    def compose(self):
        """Compose footer structure."""
        with Horizontal():
            yield Label(
                f"{tui_constants.get_glyph('AURA_STAR')} AURA", id="footer-icon"
            )
            separator = tui_constants.get_glyph("SEPARATOR", "-")
            yield Label(separator, classes="footer-separator")
            yield Label("\\[NORMAL]", id="footer-mode", classes="footer-mode")
            yield Label(separator, classes="footer-separator")

            with Horizontal(classes="footer-keybindings", id="footer-keybindings"):
                for key, action in self._keybindings:
                    yield AuraKeyHint(key, action, classes="footer-keybinding")

            yield Label(separator, classes="footer-separator")
            yield Label("", id="footer-agent", classes="footer-agent")
            yield Label("", id="footer-model", classes="footer-model")
            yield Label("", id="footer-external-tool", classes="footer-external-tool")
            yield Label("", id="footer-status", classes="footer-status")

    def update_keybindings(self, keybind_manager: Any) -> None:
        """Rebuild the keybinding hints from a live KeybindManager.

        Extracts the top-level (non-leader, show_in_help=True) bindings,
        formats them as ``(display_key, description)`` pairs, and remounts
        the ``#footer-keybindings`` container so the footer always reflects
        the real registered shortcuts instead of the hardcoded fallback.

        Args:
            keybind_manager: A ``KeybindManager`` instance.
        """
        try:
            keybinds = keybind_manager.get_keybinds(include_leader=False)
            # Keep only show_in_help entries; cap at 4 to avoid overflow.
            pairs = [
                (kb.display_key, kb.description)
                for kb in keybinds
                if kb.show_in_help
            ][:4]
            if not pairs:
                return

            self._keybindings = pairs

            try:
                container = self.query_one("#footer-keybindings")
                container.remove_children()
                for key, action in self._keybindings:
                    container.mount(AuraKeyHint(key, action, classes="footer-keybinding"))
            except Exception as mount_exc:
                # Widget not mounted yet — keybindings will reflect on next compose.
                logger.debug("footer keybindings container not ready: %s", mount_exc)
        except Exception as exc:
            logger.debug("update_keybindings failed: %s", exc)

    def on_mount(self) -> None:
        """Initialize footer display after mount."""
        self._update_mode_display()
        self._update_status_display()
        self._update_runtime_phase_classes()
        self._update_agent_display()
        self._update_model_display()

    def _update_mode_display(self) -> None:
        """Update mode label with icon."""
        try:
            mode_label = self.query_one("#footer-mode", Label)
            mode_upper = self.mode.upper()
            icon = tui_constants.MODE_ICONS.get(mode_upper.lower(), "")
            inner = f"{icon} {mode_upper}" if icon else mode_upper
            # Escape the surrounding brackets so Rich markup does not treat
            # "[NORMAL]" as an (empty) markup tag and strip the whole label.
            display = f"\\[{inner}]"
            mode_label.update(display)

            # Clear all mode classes first
            mode_label.remove_class(
                "footer-mode-insert", "footer-mode-agi", "footer-mode-ops"
            )

            # Add appropriate class
            if mode_upper == "INSERT":
                mode_label.add_class("footer-mode-insert")
            elif mode_upper == "AGI":
                mode_label.add_class("footer-mode-agi")
            elif mode_upper == "OPS":
                mode_label.add_class("footer-mode-ops")
        except Exception as error:
            logger.debug("Footer mode is not mounted yet: %s", error)

    def _update_status_display(self) -> None:
        """Update status message label."""
        try:
            status_label = self.query_one("#footer-status", Label)
            if self.status_message:
                status_label.update(f" {self.status_message}")
            else:
                status_label.update("")
        except Exception as error:
            logger.debug("Footer status is not mounted yet: %s", error)

    def _update_agent_display(self) -> None:
        """Update active agent indicator."""
        try:
            agent_label = self.query_one("#footer-agent", Label)
            if self.active_agent:
                agent_label.update(
                    f"{tui_constants.get_glyph('AGENT')} {self.active_agent}"
                )
            else:
                agent_label.update("")
        except Exception as error:
            logger.debug("Footer agent is not mounted yet: %s", error)

    def _update_model_display(self) -> None:
        """Update model name indicator."""
        try:
            model_label = self.query_one("#footer-model", Label)
            if self.model_name:
                # Shorten model name for display
                short_name = (
                    self.model_name.split("/")[-1]
                    if "/" in self.model_name
                    else self.model_name
                )
                short_name = (
                    short_name[:20] + "..." if len(short_name) > 20 else short_name
                )
                model_label.update(
                    f" {tui_constants.get_glyph('SEPARATOR', '-')}{tui_constants.get_glyph('AGI')} {short_name}"
                )
            else:
                model_label.update("")
        except Exception as error:
            logger.debug("Footer model is not mounted yet: %s", error)

    def watch_mode(self, mode: str) -> None:
        """Update mode display when mode changes."""
        self._update_mode_display()

    def watch_status_message(self, message: str) -> None:
        """Update status message when it changes."""
        self._update_status_display()

    def watch_runtime_phase(self, phase: str) -> None:
        """Update semantic phase classes when runtime state changes."""
        self._update_runtime_phase_classes()

    def _update_runtime_phase_classes(self) -> None:
        """Keep one semantic runtime class on the footer root."""
        try:
            self.remove_class(*self._RUNTIME_CLASSES)
            if self.runtime_phase:
                self.add_class(f"runtime-{self.runtime_phase}")
        except Exception as error:
            logger.debug("Footer runtime phase is not mounted yet: %s", error)

    def watch_active_agent(self, agent: str) -> None:
        """Update agent display when it changes."""
        self._update_agent_display()

    def watch_model_name(self, model: str) -> None:
        """Update model display when it changes."""
        self._update_model_display()

    def set_mode(self, mode: str) -> None:
        """Update the current mode display."""
        self.mode = mode.upper()

    def set_runtime_state(self, state: TuiRuntimeState) -> None:
        """Render one semantic runtime state and manage transient timers."""
        self._cancel_status_timer()
        self.runtime_phase = state.phase.value
        self.status_message = state.footer_message
        if state.phase in {
            RuntimePhase.COMPLETED,
            RuntimePhase.CANCELLED,
            RuntimePhase.STOPPED,
        }:
            self._status_timer = self.set_timer(5.0, self._clear_status)

    def set_status(self, message: str) -> None:
        """Set a backwards-compatible temporary status message."""
        self._cancel_status_timer()
        self.runtime_phase = (
            RuntimePhase.EXECUTING.value if message else RuntimePhase.READY.value
        )
        self.status_message = message or "Pronto"
        if message:
            self._status_timer = self.set_timer(5.0, self._clear_status)

    def set_active_agent(self, agent: str) -> None:
        """Set the active agent indicator."""
        self.active_agent = agent

    def set_model(self, model: str) -> None:
        """Set the current model name."""
        self.model_name = model

    def set_external_tool_session(self, session: ExternalToolSession | None) -> None:
        """Render the persistent phase of an external tool session."""
        try:
            label = self.query_one("#footer-external-tool", Label)
            label.remove_class(*self._EXTERNAL_TOOL_CLASSES)
            if session is None:
                label.update("")
                return
            phase_label = self._EXTERNAL_PHASE_LABELS[session.phase]
            label.update(f" {session.tool_name} · {phase_label}")
            label.add_class(f"external-tool-{session.phase.value}")
        except Exception as error:
            logger.debug("Footer external tool is not mounted yet: %s", error)

    def _cancel_status_timer(self) -> None:
        """Cancel a previous timer so stale callbacks cannot clear new state."""
        timer = self._status_timer
        self._status_timer = None
        if timer is not None:
            try:
                timer.stop()
            except Exception as error:
                logger.debug("Footer status timer could not stop: %s", error)

    def _clear_status(self) -> None:
        """Return transient terminal status to the ready label."""
        self._status_timer = None
        self.runtime_phase = RuntimePhase.READY.value
        self.status_message = "Pronto"


class AuraKeyHint(Static):
    """Compact widget for displaying a specific key hint.

    Useful for showing contextual shortcuts in different parts of the UI.
    """

    def __init__(self, key: str, action: str, **kwargs):
        """Initialize the key hint with its key label and action description."""
        super().__init__(**kwargs)
        self._key = key
        self._action = action

    def compose(self):
        """Compose key hint structure."""
        yield Label(f"\\[{self._key}]", classes="key")
        yield Label(f" {self._action}", classes="action")
