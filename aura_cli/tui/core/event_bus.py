"""TUI event catalog backed by the presentation-neutral typed event bus."""

from __future__ import annotations

import logging
from typing import Any, Literal

from pydantic import BaseModel, Field

from aura_cli.application.presentation.event_bus import (
    EventDefinition,
    EventRecord,
    TypedEventBus,
)

logger = logging.getLogger(__name__)


class TUIEventBus(TypedEventBus):
    """Typed event bus exposed as part of the TUI public API."""


class TUIEvents:
    """Schemas and names for application-wide TUI broadcasts."""

    bus = TUIEventBus()

    @classmethod
    def _register_agi_contracts(cls) -> None:
        try:
            from aura_cli.core.events.contracts import _PAYLOAD_REGISTRY

            for event_type, schema in _PAYLOAD_REGISTRY.items():
                cls.bus.define(event_type, schema, f"AGI event: {event_type}")
        except Exception as error:
            logger.warning("Could not register AGI event contracts: %s", error)

    class ToastShowPayload(BaseModel):
        message: str
        severity: Literal["info", "success", "warning", "error"] = "info"
        title: str | None = None
        timeout: float = 5.0

    ToastShow = bus.define("tui.toast.show", ToastShowPayload, "Show a toast")

    class ToastDismissPayload(BaseModel):
        toast_id: str | None = None

    ToastDismiss = bus.define(
        "tui.toast.dismiss", ToastDismissPayload, "Dismiss a toast"
    )

    class PromptAppendPayload(BaseModel):
        text: str
        cursor_position: int | None = None

    PromptAppend = bus.define(
        "tui.prompt.append", PromptAppendPayload, "Append prompt text"
    )

    class PromptClearPayload(BaseModel):
        """Marker payload for prompt clearing."""

    PromptClear = bus.define("tui.prompt.clear", PromptClearPayload, "Clear the prompt")

    class PromptSubmitPayload(BaseModel):
        content: str
        parts: list[dict[str, Any]] = Field(default_factory=list)

    PromptSubmit = bus.define(
        "tui.prompt.submit", PromptSubmitPayload, "Submit the prompt"
    )

    class CommandExecutePayload(BaseModel):
        command: str
        args: dict[str, Any] = Field(default_factory=dict)

    CommandExecute = bus.define(
        "tui.command.execute", CommandExecutePayload, "Execute a command"
    )

    class CommandRegisterPayload(BaseModel):
        name: str
        description: str
        keybind: str | None = None
        icon: str | None = None

    CommandRegister = bus.define(
        "tui.command.register", CommandRegisterPayload, "Register a command"
    )

    class NavigatePayload(BaseModel):
        route_type: str
        params: dict[str, Any] = Field(default_factory=dict)

    Navigate = bus.define("tui.navigate", NavigatePayload, "Navigate to a route")

    class NavigateBackPayload(BaseModel):
        """Marker payload for backward navigation."""

    NavigateBack = bus.define("tui.navigate.back", NavigateBackPayload, "Navigate back")

    class DialogShowPayload(BaseModel):
        dialog_type: str
        title: str = ""
        data: dict[str, Any] = Field(default_factory=dict)

    DialogShow = bus.define("tui.dialog.show", DialogShowPayload, "Show a dialog")

    class DialogClosePayload(BaseModel):
        dialog_id: str | None = None
        result: Any | None = None

    DialogClose = bus.define("tui.dialog.close", DialogClosePayload, "Close a dialog")

    class LeaderModePayload(BaseModel):
        active: bool
        sequence: list[str] = Field(default_factory=list)

    LeaderMode = bus.define("tui.leader.mode", LeaderModePayload, "Change leader mode")

    class ThemeChangePayload(BaseModel):
        theme_name: str
        auto_detected: bool = False

    ThemeChange = bus.define("tui.theme.change", ThemeChangePayload, "Change theme")

    class ErrorPayload(BaseModel):
        error_type: str
        message: str
        context: str = ""
        fatal: bool = False
        traceback: str | None = None

    Error = bus.define("tui.error", ErrorPayload, "Report an error")

    class SyncStatePayload(BaseModel):
        path: str
        value: Any

    SyncState = bus.define("tui.sync.state", SyncStatePayload, "Synchronize state")

    class SyncBatchPayload(BaseModel):
        updates: list[dict[str, Any]]

    SyncBatch = bus.define(
        "tui.sync.batch", SyncBatchPayload, "Synchronize state batch"
    )


def show_toast(
    message: str,
    severity: Literal["info", "success", "warning", "error"] = "info",
    title: str | None = None,
    timeout: float = 5.0,
) -> None:
    TUIEvents.bus.publish(
        "tui.toast.show",
        {"message": message, "severity": severity, "title": title, "timeout": timeout},
    )


def emit_error(
    error_type: str,
    message: str,
    context: str = "",
    fatal: bool = False,
    traceback: str | None = None,
) -> None:
    TUIEvents.bus.publish(
        "tui.error",
        {
            "error_type": error_type,
            "message": message,
            "context": context,
            "fatal": fatal,
            "traceback": traceback,
        },
    )


TUIEvents._register_agi_contracts()

__all__ = [
    "EventDefinition",
    "EventRecord",
    "TUIEventBus",
    "TUIEvents",
    "emit_error",
    "show_toast",
]
