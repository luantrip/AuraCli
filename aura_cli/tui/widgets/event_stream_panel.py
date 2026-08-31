"""Event Stream Panel for Aura TUI.

Real-time stream viewer for all AgiEvents with color-coded formatting.
"""

import contextlib
from datetime import datetime
import json
from typing import Dict, Iterable, List, Optional, cast

from textual.containers import Horizontal, VerticalScroll
from textual.widgets import Label, Select, Static

from aura_cli.application.agents.events import AgiEvent
from aura_cli.application.presentation.safe_payloads import (
    sanitize_event_dict_for_presentation,
    sanitize_event_for_presentation,
)
import aura_cli.tui.constants as tui_constants


class _EventStatic(Static):
    """Static event entry with its canonical filter key."""

    aura_event_type: str = ""


class EventStreamPanel(VerticalScroll):
    """Widget to display a real-time stream of all AgiEvents.

    Features:
    - Real-time event streaming with auto-scroll
    - Color-coded event types via CSS classes
    - Timestamp display for each event
    - Event filtering by type
    - Max 1000 lines with automatic trimming
    """

    MAX_LINES = 1000
    EVENT_FILTER_OPTIONS = (
        ("Todos os eventos", ""),
        ("Tarefas AGI iniciadas", "agi_task_start"),
        ("Atualizações AGI", "agi_task_update"),
        ("Conclusões AGI", "agi_task_complete"),
        ("Ferramentas em execução", "tool_executing"),
        ("Resultados de ferramentas", "tool_result"),
        ("Decisões de segurança", "capability_decision"),
        ("Mensagens do chat", "chat_message"),
    )
    _event_count = 0

    def __init__(self, **kwargs):
        """Initialize the instance."""
        super().__init__(**kwargs)
        self._events: List[_EventStatic] = []
        self._event_count = 0
        self._event_filter: Optional[frozenset[str]] = None

    def compose(self):
        """Render guidance while no agent events have arrived."""
        with Horizontal(classes="event-filter-row"):
            yield Label("Filtrar:", classes="event-filter-label")
            yield Select(
                self.EVENT_FILTER_OPTIONS,
                value="",
                id="event-filter-select",
                allow_blank=False,
            )
        yield Static(
            "Nenhum evento ainda. Inicie uma tarefa para acompanhar a atividade.",
            id="event-empty-state",
            classes="empty-state",
        )

    def _set_empty_state_visible(self, visible: bool) -> None:
        with contextlib.suppress(Exception):
            self.query_one("#event-empty-state", Static).display = visible

    @property
    def event_filter(self) -> frozenset[str] | None:
        """Return the active event-type filter, or ``None`` for all events."""
        return self._event_filter

    def set_event_filter(self, event_types: Optional[Iterable[str]]) -> None:
        """Show only events whose type is in *event_types*.

        Filtering changes presentation only: the event widgets remain in the
        bounded stream so clearing the filter does not lose activity history.
        Passing ``None`` or an empty iterable restores all event types.
        """
        normalized = frozenset(
            str(event_type).strip().casefold()
            for event_type in (event_types or ())
            if str(event_type).strip()
        )
        self._event_filter = normalized or None
        self._apply_event_filter()

    def clear_event_filter(self) -> None:
        """Restore visibility for every retained event."""
        self.set_event_filter(None)

    def _apply_event_filter(self) -> None:
        for event_widget in self._events:
            event_type = str(getattr(event_widget, "aura_event_type", "")).casefold()
            event_widget.display = (
                self._event_filter is None or event_type in self._event_filter
            )
        self._set_empty_state_visible(
            not any(event_widget.display for event_widget in self._events)
        )

    def on_select_changed(self, event: Select.Changed) -> None:
        """Apply the visible event-type selection."""
        if event.select.id != "event-filter-select":
            return
        selected = str(event.value or "")
        self.set_event_filter([selected] if selected else None)

    def write_event(self, event_dict: Dict) -> None:
        """Write an AgiEvent to the stream.

        Args:
            event_dict: Dictionary containing event data
        """
        event_dict = sanitize_event_dict_for_presentation(event_dict)
        event_type = str(
            getattr(
                event_dict.get("type", "UNKNOWN"),
                "value",
                event_dict.get("type", "UNKNOWN"),
            )
        )
        task_id = event_dict.get("task_id", "N/A")
        timestamp = datetime.fromtimestamp(
            event_dict.get("timestamp", datetime.now().timestamp())
        ).strftime("%H:%M:%S")
        data = event_dict.get("data", {})

        event_class = self._get_event_class(event_type, data)
        content = self._format_event_content(event_type, task_id, data)

        event_widget = cast(
            _EventStatic,
            Static(
                f"[{timestamp}] {content}",
                classes=f"event-entry {event_class}",
            ),
        )
        event_widget.aura_event_type = event_type
        event_widget.display = (
            self._event_filter is None
            or event_type.casefold() in self._event_filter
        )
        self.mount(event_widget)
        self._events.append(event_widget)
        self._event_count += 1

        if len(self._events) > self.MAX_LINES:
            oldest = self._events.pop(0)
            oldest.remove()

        self._set_empty_state_visible(
            not any(event_widget.display for event_widget in self._events)
        )
        self.scroll_end()

    def write_event_details(self, event: AgiEvent) -> None:
        """Write a detailed view of a single AgiEvent to the stream.

        Args:
            event: AgiEvent instance
        """

        event = sanitize_event_for_presentation(event)
        timestamp_str = datetime.fromtimestamp(event.timestamp).strftime(
            "%Y-%m-%d %H:%M:%S"
        )
        event_type = str(getattr(event.type, "value", event.type))

        details_lines = [
            f"Event Type: {event_type}",
            f"Task ID: {event.task_id}",
        ]
        if event.parent_task_id:
            details_lines.append(f"Parent ID: {event.parent_task_id}")
        details_lines.append(f"Timestamp: {timestamp_str}")
        details_lines.append("")
        details_lines.append("Data:")

        try:
            data_json = json.dumps(event.data, indent=2)
            details_lines.append(data_json)
        except Exception:
            details_lines.append(str(event.data))

        details_content = "\n".join(details_lines)
        details_widget = cast(
            _EventStatic,
            Static(details_content, classes="event-entry event-details"),
        )
        details_widget.aura_event_type = event_type
        details_widget.display = (
            self._event_filter is None
            or event_type.casefold() in self._event_filter
        )
        self.mount(details_widget)
        self._events.append(details_widget)
        self._event_count += 1

        if len(self._events) > self.MAX_LINES:
            oldest = self._events.pop(0)
            oldest.remove()

        self._set_empty_state_visible(
            not any(event_widget.display for event_widget in self._events)
        )
        self.scroll_end()

    def _get_event_class(self, event_type: str, data: Dict) -> str:
        """Get CSS class for event type."""
        if event_type == "agi_task_start":
            return "event-task-start"
        elif event_type == "agi_task_update":
            return "event-task-update"
        elif event_type == "agi_task_complete":
            return (
                "event-task-complete"
                if data.get("success", False)
                else "event-task-failed"
            )
        elif event_type == "tool_executing":
            return "event-tool-executing"
        elif event_type == "tool_result":
            return (
                "event-tool-result"
                if data.get("success", False)
                else "event-tool-error"
            )
        elif event_type == "capability_decision":
            phase = str(data.get("phase", "evaluation"))
            if not data.get("allowed", False) or phase == "blocked":
                return "event-capability-blocked"
            if phase == "confirmation" or data.get("requires_confirmation", False):
                return "event-capability-confirmation"
            if phase == "commit":
                return "event-capability-commit"
            return "event-capability-evaluation"
        elif event_type == "chat_message":
            return "event-chat-message"
        return "event-unknown"

    def _format_event_content(self, event_type: str, task_id: str, data: Dict) -> str:
        """Format an event as a compact, localized activity line."""
        if event_type == "agi_task_start":
            desc = data.get("description", "")[:60]
            return f"{tui_constants.AGI} AGI iniciou: {desc}"
        elif event_type == "agi_task_update":
            status = data.get("status", "")
            msg = data.get("message", "")[:50]
            prefix = tui_constants.LOADING
            return f"{prefix} {status}: {msg}" if msg else f"{prefix} {status}"
        elif event_type == "agi_task_complete":
            success = data.get("success", False)
            icon = tui_constants.SUCCESS if success else tui_constants.ERROR
            state = "concluída" if success else "falhou"
            return f"{icon} AGI {state}"
        elif event_type == "tool_executing":
            tool = data.get("tool_name", "")
            has_args = bool(data.get("tool_args"))
            suffix = " (parâmetros ocultos: [oculto])" if has_args else ""
            return f"{tui_constants.TOOL} {tool}{suffix}"
        elif event_type == "tool_result":
            tool = data.get("tool_name", "")
            success = data.get("success", False)
            icon = tui_constants.SUCCESS if success else tui_constants.ERROR
            duration = data.get("execution_time")
            time_str = (
                f" {duration:.0f}ms"
                if duration and duration < 1
                else (f" {duration:.1f}s" if duration else "")
            )
            return f"{icon} {tool}{time_str}"
        elif event_type == "capability_decision":
            tool = str(data.get("tool_name", "ferramenta"))[:48]
            phase = str(data.get("phase", "evaluation"))
            reason_lines = str(data.get("reason") or "").splitlines()
            reason = reason_lines[0][:72] if reason_lines else ""
            if not data.get("allowed", False) or phase == "blocked":
                suffix = f": {reason}" if reason else ""
                return f"{tui_constants.ERROR} Segurança bloqueou {tool}{suffix}"
            if phase == "confirmation" or data.get("requires_confirmation", False):
                return f"{tui_constants.WARNING} Confirmação necessária: {tool}"
            if phase == "commit":
                return f"{tui_constants.SUCCESS} Capability reservada: {tool}"
            return f"{tui_constants.INFO} Capability avaliada: {tool}"
        elif event_type == "chat_message":
            sender = data.get("sender", "")
            content = data.get("content", "")[:40]
            return f"{tui_constants.CHAT} {sender}: {content}"
        return f"{tui_constants.BULLET} {event_type}: {str(data)[:40]}"

    def clear(self) -> None:
        """Clear all events from the stream."""
        for event in self._events:
            event.remove()
        self._events.clear()
        self._event_count = 0
        self._event_filter = None
        with contextlib.suppress(Exception):
            self.query_one("#event-filter-select", Select).value = ""
        self._set_empty_state_visible(True)
