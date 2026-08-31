"""Exercise realtime event projection and attention coordination contracts."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

from aura_cli.application.agents.events import AgiEvent, AgiEventType
from aura_cli.application.presentation.attention_delivery import (
    AttentionChannel,
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
    DrawerMode,
    TuiDensity,
    TuiDrawer,
    TuiLayoutState,
    decide_tui_layout,
)
from aura_cli.application.presentation.tui_surfaces import (
    PresentationIntent,
    SurfaceKind,
    SurfaceRequest,
    decide_surface,
)
from aura_cli.application.presentation.work_item_projection import (
    RealtimeProjectionReducer,
)


def event(event_type: AgiEventType, timestamp: float, data: dict) -> AgiEvent:
    return AgiEvent(
        type=event_type,
        task_id="coordination-task",
        timestamp=timestamp,
        data=data,
    )


def check_projection_and_heartbeat() -> dict[str, object]:
    reducer = RealtimeProjectionReducer(heartbeat_seconds=5)
    start = reducer.reduce(
        event(
            AgiEventType.TASK_START,
            100,
            {"description": "Build", "status": "starting"},
        )
    )
    update = reducer.reduce(
        event(
            AgiEventType.TASK_UPDATE,
            104,
            {"status": "running", "message": "Working"},
        )
    )
    heartbeat = reducer.heartbeat(now=datetime.fromtimestamp(111, timezone.utc))
    approval = reducer.reduce(
        event(
            AgiEventType.APPROVAL_REQUESTED,
            112,
            {
                "status": "awaiting_user",
                "request_id": "approval-1",
                "action": "edit_file",
                "message": "Apply change?",
            },
        )
    )
    resolved = reducer.reduce(
        event(
            AgiEventType.APPROVAL_RESOLVED,
            113,
            {
                "status": "running",
                "request_id": "approval-1",
                "message": "Approved",
            },
        )
    )
    completed = reducer.reduce(
        event(
            AgiEventType.TASK_COMPLETE,
            120,
            {"success": True, "result": "Done", "status": "completed"},
        )
    )
    assert start and update and heartbeat
    assert any(request.heartbeat_due for request in heartbeat)
    assert any(request.intent is PresentationIntent.DECISION for request in approval)
    assert any(request.resolves_attention for request in resolved)
    assert any(request.consolidate for request in completed)
    return {
        "start_requests": len(start),
        "update_requests": len(update),
        "heartbeat_requests": len(heartbeat),
        "approval_requests": len(approval),
        "resolved_requests": len(resolved),
        "completed_requests": len(completed),
    }


def check_attention_and_inbox() -> dict[str, object]:
    request = SurfaceRequest(
        PresentationIntent.DECISION,
        "Apply change?",
        task_id="background-task",
        key="task:background-task",
    )
    state = AttentionDeliveryState()
    state, delivery = decide_attention_delivery(
        state,
        request,
        focused_task_id="focused-task",
        app_focused=False,
    )
    assert delivery is not None
    assert AttentionChannel.TERMINAL_TITLE in delivery.channels
    state, duplicate = decide_attention_delivery(
        state,
        request,
        focused_task_id="focused-task",
        app_focused=False,
    )
    assert duplicate is None
    state = resolve_attention_delivery(
        state,
        SurfaceRequest(
            request.intent,
            request.content,
            task_id=request.task_id,
            key=request.key,
            resolves_attention=True,
        ),
    )
    state, redelivered = decide_attention_delivery(
        state,
        request,
        focused_task_id="focused-task",
        app_focused=False,
    )
    assert redelivered is not None
    inbox = put_attention(
        AttentionInbox(),
        AttentionEntry(request.key or "", request.task_id, "Approval", request.content, True),
    )
    assert inbox.blocking_count == 1
    assert not resolve_attention(inbox, request.key or "").entries
    return {"channels": [channel.value for channel in delivery.channels], "redelivered": True}


def check_surface_and_layout() -> dict[str, object]:
    routes = {
        intent.value: [kind.value for kind in decide_surface(SurfaceRequest(intent, "x")).destinations]
        for intent in PresentationIntent
    }
    assert routes[PresentationIntent.RESPONSE.value] == [SurfaceKind.CONVERSATION.value]
    assert routes[PresentationIntent.DECISION.value] == [SurfaceKind.BLOCKING.value]
    assert SurfaceKind.ACTIVITY.value in routes[PresentationIntent.WARNING.value]
    layouts = {
        "compact": decide_tui_layout(TuiLayoutState(72, 20, TuiDrawer.ACTIVITY)),
        "split": decide_tui_layout(TuiLayoutState(140, 40, TuiDrawer.WORKSPACE)),
        "focus": decide_tui_layout(TuiLayoutState(180, 50, TuiDrawer.ACTIVITY, True)),
    }
    assert layouts["compact"].drawer_mode is DrawerMode.OVERLAY
    assert layouts["compact"].density is TuiDensity.COMPACT
    assert layouts["split"].drawer_mode is DrawerMode.SPLIT
    assert layouts["split"].show_task_panel
    assert layouts["focus"].drawer is None
    return {
        "routes": routes,
        "layouts": {
            name: {
                "drawer_mode": layout.drawer_mode.value,
                "density": layout.density.value,
                "drawer": layout.drawer.value if layout.drawer else None,
            }
            for name, layout in layouts.items()
        },
    }


def main() -> None:
    report = {
        "contract": "aura-realtime-coordination-v1",
        "checks": {
            "projection_heartbeat": check_projection_and_heartbeat(),
            "attention_inbox": check_attention_and_inbox(),
            "surface_layout": check_surface_and_layout(),
        },
        "aura_home": os.environ.get("AURA_HOME", ""),
        "status": "READY",
    }
    output_path = Path(os.environ.get("AURA_HOME", ".")) / "realtime-coordination-probe.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print("COORDINATION_READY")
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
