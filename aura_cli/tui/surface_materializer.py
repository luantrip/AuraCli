"""Observable orchestration steps for semantic TUI surface requests."""

from __future__ import annotations

from dataclasses import dataclass
import logging
from typing import Any, Literal

from aura_cli.application.presentation.activity_feed import reduce_activity
from aura_cli.application.presentation.attention_delivery import (
    AttentionChannel,
    decide_attention_delivery,
    resolve_attention_delivery,
)
from aura_cli.application.presentation.attention_inbox import (
    AttentionEntry,
    put_attention,
    resolve_attention,
)
from aura_cli.application.presentation.tui_runtime_state import (
    TuiRuntimeState,
    reduce_runtime_state,
)
from aura_cli.application.presentation.tui_surface_state import (
    activity_section_for_route,
    mark_activity,
    select_activity,
)
from aura_cli.application.presentation.tui_surfaces import (
    SurfaceDecision,
    SurfaceKind,
    SurfaceRequest,
    decide_surface,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SurfaceMaterialization:
    """Decision and attention delivery produced before widget updates."""

    decision: SurfaceDecision
    delivery: Any | None = None


def prepare_surface(app: Any, request: SurfaceRequest) -> SurfaceMaterialization:
    """Reduce semantic state and calculate destinations before side effects."""
    current_runtime_state = getattr(app, "runtime_state", TuiRuntimeState())
    app.runtime_state = reduce_runtime_state(current_runtime_state, request)
    sync_runtime_ui = getattr(app, "_sync_runtime_ui", None)
    if callable(sync_runtime_ui):
        sync_runtime_ui()

    if request.resolves_attention and request.key:
        app.attention_inbox = resolve_attention(app.attention_inbox, request.key)
    app.attention_delivery_state = resolve_attention_delivery(
        app.attention_delivery_state, request
    )
    decision = decide_surface(request)
    focused_task_id = getattr(app.surface_state, "task_filter", None)
    active = getattr(app, "is_active", None)
    app_focused = active if isinstance(active, bool) else True
    app.attention_delivery_state, delivery = decide_attention_delivery(
        app.attention_delivery_state,
        request,
        focused_task_id=focused_task_id,
        app_focused=app_focused,
        preferences=app.attention_preferences,
    )
    return SurfaceMaterialization(decision=decision, delivery=delivery)


def materialize_destinations(
    app: Any,
    request: SurfaceRequest,
    materialization: SurfaceMaterialization,
) -> None:
    """Apply each semantic destination to the corresponding TUI surface."""
    for destination in materialization.decision.destinations:
        if destination is SurfaceKind.CONVERSATION:
            sender = "Aura" if request.intent.value == "response" else "Sistema"
            app.post_message_to_chat(sender, request.content, request.task_id)
        elif destination is SurfaceKind.NOTIFICATION:
            severity: Literal["information", "warning", "error"]
            if request.intent.value == "error":
                severity = "error"
            elif request.intent.value == "warning":
                severity = "warning"
            else:
                severity = "information"
            app.notify(
                request.content,
                title=request.title or "Aura",
                severity=severity,
            )
        elif destination is SurfaceKind.ACTIVITY:
            app.activity_feed = reduce_activity(app.activity_feed, request)
            app.surface_state = mark_activity(
                app.surface_state, activity_section_for_route(request.route)
            )
        elif destination is SurfaceKind.BLOCKING:
            key = request.key or f"{request.task_id}:{request.title or request.content}"
            app.attention_inbox = put_attention(
                app.attention_inbox,
                AttentionEntry(
                    key=key,
                    task_id=request.task_id,
                    title=request.title or "Ação necessária",
                    message=request.content,
                    blocking=True,
                ),
            )
            app.surface_state = select_activity(
                app.surface_state, activity_section_for_route(request.route)
            )
            apply_layout_plan = getattr(app, "_apply_layout_plan", None)
            if callable(apply_layout_plan):
                try:
                    apply_layout_plan()
                except Exception as error:
                    logger.debug("Could not reveal blocking surface: %s", error)
            app.notify(
                request.content,
                title=request.title or "Ação necessária",
                severity="warning",
                timeout=10,
            )
        elif destination is SurfaceKind.TOOL:
            from aura_cli.tui.shell.screen_registry import navigate_route

            navigate_route(app, request.route or "tools")


def deliver_feedback(
    app: Any,
    materialization: SurfaceMaterialization,
) -> None:
    """Apply terminal title, bell and out-of-focus feedback after materialization."""
    delivery = materialization.delivery
    if delivery is None:
        return
    if delivery.terminal_title:
        app.title = delivery.terminal_title
    if AttentionChannel.BELL in delivery.channels:
        bell = getattr(app, "bell", None)
        if callable(bell):
            try:
                bell()
            except Exception as error:
                logger.debug("Could not ring TUI bell: %s", error)
    if materialization.decision.primary not in {
        SurfaceKind.NOTIFICATION,
        SurfaceKind.BLOCKING,
    }:
        app.notify(
            delivery.message,
            title="Atividade fora do foco",
            severity="information",
        )


def materialize_surface(app: Any, request: SurfaceRequest) -> None:
    """Run the observable prepare → destinations → feedback pipeline."""
    materialization = prepare_surface(app, request)
    materialize_destinations(app, request, materialization)
    deliver_feedback(app, materialization)


__all__ = [
    "SurfaceMaterialization",
    "deliver_feedback",
    "materialize_destinations",
    "materialize_surface",
    "prepare_surface",
]
