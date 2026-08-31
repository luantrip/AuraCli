"""Toolkit-neutral temporal acceptance harness for the visual system."""

from __future__ import annotations

from dataclasses import dataclass
import logging
from typing import Any, Mapping, Sequence

from aura_cli.application.agents.events import AgiEvent
from aura_cli.application.presentation.activity_feed import (
    ActivityFeed,
    reduce_activity,
)
from aura_cli.application.presentation.attention_delivery import (
    AttentionDeliveryState,
    decide_attention_delivery,
    resolve_attention_delivery,
)
from aura_cli.application.presentation.attention_inbox import (
    AttentionEntry,
    AttentionInbox,
    put_attention,
    resolve_attention,
)
from aura_cli.application.presentation.tui_layout import (
    TuiLayoutState,
    decide_tui_layout,
)
from aura_cli.application.presentation.tui_runtime_state import (
    TuiRuntimeState,
    reduce_runtime_state,
)
from aura_cli.application.presentation.tui_surfaces import (
    SurfaceKind,
    decide_surface,
)
from aura_cli.application.presentation.work_item_projection import (
    RealtimeProjectionReducer,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class VisualAcceptanceFrame:
    event_type: str
    width: int
    height: int
    active_keys: tuple[str, ...]
    completed_keys: tuple[str, ...]
    blocking_keys: tuple[str, ...]
    announcements: tuple[str, ...]
    conversation: tuple[str, ...]
    density: str
    drawer_mode: str
    runtime_phase: str
    loading_visible: bool


def run_visual_scenario(
    events: Sequence[Mapping[str, Any]],
    *,
    viewports: Sequence[tuple[int, int]],
    focused_task_id: str | None = None,
    app_focused: bool = True,
) -> tuple[VisualAcceptanceFrame, ...]:
    """Replay a lifecycle and capture every observable semantic frame."""
    reducer = RealtimeProjectionReducer()
    feed = ActivityFeed()
    inbox = AttentionInbox()
    delivery_state = AttentionDeliveryState()
    runtime_state = TuiRuntimeState()
    conversation: list[str] = []
    announcements: list[str] = []
    frames: list[VisualAcceptanceFrame] = []
    for index, raw in enumerate(events):
        if not isinstance(raw, Mapping):
            logger.warning("Evento visual ignorado: payload não é mapeável")
            continue
        try:
            event = AgiEvent.from_dict(dict(raw))
        except (KeyError, TypeError, ValueError) as error:
            logger.warning("Visual event ignored due to invalid payload: %s", error)
            continue
        requests = reducer.reduce(event)
        for request in requests:
            runtime_state = reduce_runtime_state(runtime_state, request)
            decision = decide_surface(request)
            if SurfaceKind.ACTIVITY in decision.destinations:
                feed = reduce_activity(feed, request)
            if request.resolves_attention and request.key:
                inbox = resolve_attention(inbox, request.key)
            if decision.primary is SurfaceKind.BLOCKING and request.key:
                inbox = put_attention(
                    inbox,
                    AttentionEntry(
                        request.key,
                        request.task_id,
                        request.title or "Ação necessária",
                        request.content,
                        True,
                    ),
                )
            if SurfaceKind.CONVERSATION in decision.destinations:
                conversation.append(request.content)
            delivery_state = resolve_attention_delivery(delivery_state, request)
            delivery_state, delivery = decide_attention_delivery(
                delivery_state,
                request,
                focused_task_id=focused_task_id,
                app_focused=app_focused,
            )
            if delivery is not None:
                announcements.append(delivery.message)
        width, height = viewports[min(index, len(viewports) - 1)]
        layout = decide_tui_layout(TuiLayoutState(width, height))
        frames.append(
            VisualAcceptanceFrame(
                event_type=str(event.type),
                width=width,
                height=height,
                active_keys=tuple(item.key or "" for item in feed.active),
                completed_keys=tuple(item.key or "" for item in feed.completed),
                blocking_keys=tuple(item.key for item in inbox.entries),
                announcements=tuple(announcements),
                conversation=tuple(conversation),
                density=layout.density.value,
                drawer_mode=layout.drawer_mode.value,
                runtime_phase=runtime_state.phase.value,
                loading_visible=runtime_state.loading_visible,
            )
        )
    return tuple(frames)


__all__ = ["VisualAcceptanceFrame", "run_visual_scenario"]
