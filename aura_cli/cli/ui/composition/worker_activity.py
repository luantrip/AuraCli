"""Render structured worker events as a one-line CLI activity trail (F-P1-8).

The CLI event stream historically understood only ``chat_message`` text tagged
``[Aura AGI]`` / ``[Aura Ops]``; the structured lifecycle events (`tool_executing`,
`tool_result`, `task_complete` and friends) were dropped on the floor, so a running
`/agi` showed nothing between "started" and the final chat reply.

This module turns each structured event into the *same* neutral projection the TUI
uses (``RealtimeProjectionReducer`` → activity ``SurfaceRequest``) and prints the
activity-bound requests as single, themed lines. It owns no policy: tone and text
come from the projection; this layer only maps tone → ``render_*`` and escapes the content so paths like
``app/[id]/page.tsx`` are shown literally. A failed tool uses a single red line
(``render_activity_error``), not the full error panel, to keep the trail to one
line per event.

A ``WorkerActivityRenderer`` instance holds one reducer per CLI session so elapsed
time and de-duplication survive across events. Chat messages are intentionally
ignored here — they stay on their existing feed path.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from rich.markup import escape

from aura_cli.application.agents.events import AgiEvent, AgiEventType
from aura_cli.application.presentation.tui_surfaces import SurfaceKind, decide_surface
from aura_cli.application.presentation.work_item_projection import (
    ProjectionTone,
    RealtimeProjectionReducer,
)

if TYPE_CHECKING:
    from aura_cli.cli.ui.rendering import RenderCoordinator


class WorkerActivityRenderer:
    """Project structured worker events onto the CLI activity trail."""

    def __init__(self, render: RenderCoordinator) -> None:
        self._render = render
        self._reducer = RealtimeProjectionReducer()

    def render_event(self, event_dict: Any) -> bool:
        """Render one structured event. Returns ``True`` if it was consumed here.

        ``False`` means the caller should keep handling it on the legacy path
        (chat messages, unknown payloads, parse failures).
        """
        if not isinstance(event_dict, dict):
            return False
        raw_type = event_dict.get("type")
        if raw_type == AgiEventType.CHAT_MESSAGE.value:
            return False  # chat stays on its own feed
        if raw_type not in _STRUCTURED_EVENT_TYPES:
            return False
        try:
            event = AgiEvent.from_dict(event_dict)
        except Exception:
            return False

        # A recognized lifecycle event with no activity line (e.g. a pure bookkeeping
        # transition) is still "consumed": it must not fall through to the text feed
        # and be mis-parsed.
        self._emit(self._reducer.reduce(event))
        return True

    def heartbeat(self) -> int:
        """Emit "still running · 1m20s" lines for long-running work. Returns count.

        The CLI loop blocks in the prompt, so this is called once per refresh (each
        time the prompt is shown). The reducer de-duplicates per 15s bucket, so
        repeated calls inside the same bucket print nothing.
        """
        return self._emit(self._reducer.heartbeat())

    def _emit(self, requests: Any) -> int:
        activity = [
            request
            for request in requests
            if decide_surface(request).primary is SurfaceKind.ACTIVITY
        ]
        for request in activity:
            tone = ProjectionTone(request.tone or ProjectionTone.INFO.value)
            _RENDER_BY_TONE[tone](self._render)(escape(request.content))
        return len(activity)


_STRUCTURED_EVENT_TYPES = frozenset(
    member.value for member in AgiEventType if member is not AgiEventType.CHAT_MESSAGE
)


def _render_for(method_name: str):
    return lambda render: getattr(render, method_name)


# Tone → RenderCoordinator method. MUTED shares the INFO line style on purpose:
# the CLI trail has no dimmer primitive and a muted transition is still worth one
# quiet line.
_RENDER_BY_TONE = {
    ProjectionTone.SUCCESS: _render_for("render_success"),
    ProjectionTone.WARNING: _render_for("render_warning"),
    ProjectionTone.ERROR: _render_for("render_activity_error"),
    ProjectionTone.INFO: _render_for("render_info"),
    ProjectionTone.MUTED: _render_for("render_info"),
}


__all__ = ["WorkerActivityRenderer"]
