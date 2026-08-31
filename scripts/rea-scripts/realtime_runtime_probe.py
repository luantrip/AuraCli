"""Exercise the framework-neutral realtime presentation contracts."""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

from pydantic import BaseModel

from aura_cli.application.presentation.activity_feed import ActivityFeed, reduce_activity
from aura_cli.application.presentation.event_bus import TypedEventBus
from aura_cli.application.presentation.realtime_execution import (
    ExecutionMotion,
    describe_realtime_execution,
)
from aura_cli.application.presentation.tui_runtime_state import (
    RuntimeAction,
    RuntimePhase,
    TuiRuntimeState,
    reduce_runtime_state,
    transition_runtime_state,
)
from aura_cli.application.presentation.tui_surfaces import (
    PresentationIntent,
    SurfaceRequest,
)
from aura_cli.application.presentation.visual_acceptance import run_visual_scenario
from aura_cli.application.presentation.work_items import (
    WorkItemEnvelope,
    WorkItemIdentity,
    WorkItemKind,
    WorkItemState,
    transition_work_item,
)


class HealthPayload(BaseModel):
    status: str


def build_item(state: WorkItemState, now: datetime) -> WorkItemEnvelope:
    return WorkItemEnvelope(
        identity=WorkItemIdentity(session_id="rea", task_id="realtime-task"),
        kind=WorkItemKind.AGENT,
        state=state,
        summary="Realtime probe",
        started_at=now - timedelta(seconds=20),
        updated_at=now,
        finished_at=now if state is WorkItemState.COMPLETED else None,
    )


def check_realtime_execution(now: datetime) -> dict[str, object]:
    active = describe_realtime_execution(build_item(WorkItemState.RUNNING, now), now=now)
    terminal = describe_realtime_execution(
        build_item(WorkItemState.COMPLETED, now), now=now
    )
    assert active.motion is ExecutionMotion.ACTIVE
    assert active.heartbeat_due and active.replace and not active.consolidate
    assert terminal.motion is ExecutionMotion.TERMINAL
    assert terminal.consolidate and not terminal.replace
    return {
        "active_motion": active.motion.value,
        "active_elapsed_seconds": active.elapsed_seconds,
        "terminal_motion": terminal.motion.value,
    }


def check_lifecycle_projection(now: datetime) -> dict[str, object]:
    item = build_item(WorkItemState.QUEUED, now)
    running = transition_work_item(item, WorkItemState.RUNNING, now=now)
    streaming = transition_work_item(running, WorkItemState.STREAMING, now=now)
    completed = transition_work_item(
        streaming, WorkItemState.COMPLETED, summary="Finished", now=now
    )
    assert completed.is_terminal and completed.finished_at == now
    feed = ActivityFeed()
    feed = reduce_activity(
        feed,
        SurfaceRequest(
            PresentationIntent.PROGRESS,
            "Streaming",
            task_id="realtime-task",
            key="task:realtime-task",
            replace=True,
        ),
    )
    feed = reduce_activity(
        feed,
        SurfaceRequest(
            PresentationIntent.SUCCESS,
            "Finished",
            task_id="realtime-task",
            key="task:realtime-task",
            consolidate=True,
        ),
    )
    assert not feed.active and [entry.content for entry in feed.completed] == ["Finished"]
    return {"states": [running.state.value, streaming.state.value, completed.state.value]}


def check_event_bus() -> dict[str, object]:
    bus = TypedEventBus()
    received: list[dict[str, object]] = []
    wildcard: list[str] = []
    bus.define("health", HealthPayload)
    bus.subscribe("health", received.append)
    bus.subscribe_all(lambda event_type, _payload: wildcard.append(event_type))
    bus.publish("health", {"status": "ok"})
    event_bus_logger = logging.getLogger(
        "aura_cli.application.presentation.event_bus"
    )
    previous_level = event_bus_logger.level
    event_bus_logger.setLevel(logging.ERROR)
    try:
        assert not bus.publish("health", {"status": 42})
    finally:
        event_bus_logger.setLevel(previous_level)
    bus.pause()
    assert not bus.publish("health", {"status": "paused"})
    bus.resume()
    assert len(received) == 1 and wildcard == ["health"]
    assert len(bus.get_history("health")) == 2
    return {"delivered": len(received), "history": len(bus.get_history("health"))}


def check_runtime_state() -> dict[str, object]:
    state = transition_runtime_state(
        TuiRuntimeState(), RuntimeAction.THINKING, message="Thinking", task_id="task"
    )
    assert state.phase is RuntimePhase.THINKING and state.loading_visible
    state = reduce_runtime_state(
        state,
        SurfaceRequest(PresentationIntent.DECISION, "Confirm?", task_id="task"),
    )
    assert state.phase is RuntimePhase.WAITING_INPUT and state.is_busy
    state = transition_runtime_state(state, RuntimeAction.READY)
    assert state.phase is RuntimePhase.READY and not state.is_busy
    return {"final_phase": state.phase.value}


def check_visual_replay() -> dict[str, object]:
    scenarios_path = Path("tests/fixtures/visual_system/scenarios.json")
    scenarios = json.loads(scenarios_path.read_text(encoding="utf-8"))
    results: dict[str, object] = {}
    for name, events in scenarios.items():
        frames = run_visual_scenario(events, viewports=((120, 40), (80, 24)))
        assert frames
        assert frames[-1].event_type
        results[name] = {
            "frames": len(frames),
            "final_phase": frames[-1].runtime_phase,
            "active": len(frames[-1].active_keys),
            "completed": len(frames[-1].completed_keys),
        }
    assert results["stream_resize"]["final_phase"] == "executing"
    assert results["stream_resize"]["completed"] == 1
    assert results["failure"]["final_phase"] == "error"
    return results


def main() -> None:
    now = datetime(2026, 10, 22, 17, 0, tzinfo=timezone.utc)
    report = {
        "contract": "aura-realtime-presentation-v1",
        "checks": {
            "realtime_execution": check_realtime_execution(now),
            "lifecycle_projection": check_lifecycle_projection(now),
            "event_bus": check_event_bus(),
            "runtime_state": check_runtime_state(),
            "visual_replay": check_visual_replay(),
        },
        "aura_home": os.environ.get("AURA_HOME", ""),
        "status": "READY",
    }
    output_path = Path(os.environ.get("AURA_HOME", ".")) / "realtime-probe.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print("REALTIME_READY")
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
