from datetime import datetime, timedelta, timezone

import pytest

from aura_cli.application.presentation.realtime_execution import (
    ExecutionMotion,
    describe_realtime_execution,
    format_elapsed,
)
from aura_cli.application.presentation.work_items import (
    WorkItemEnvelope,
    WorkItemIdentity,
    WorkItemKind,
    WorkItemState,
)

NOW = datetime(2026, 8, 13, 12, 0, tzinfo=timezone.utc)


def item(state: WorkItemState, *, seconds: int = 20) -> WorkItemEnvelope:
    return WorkItemEnvelope(
        identity=WorkItemIdentity(task_id="task-1"),
        kind=WorkItemKind.AGENT,
        state=state,
        summary="Build",
        started_at=NOW - timedelta(seconds=seconds),
        updated_at=NOW,
        finished_at=NOW if state is WorkItemState.COMPLETED else None,
    )


@pytest.mark.parametrize(
    ("state", "motion"),
    [
        (WorkItemState.QUEUED, ExecutionMotion.STILL),
        (WorkItemState.RUNNING, ExecutionMotion.ACTIVE),
        (WorkItemState.STREAMING, ExecutionMotion.STREAMING),
        (WorkItemState.WAITING_EXTERNAL, ExecutionMotion.WAITING),
        (WorkItemState.AWAITING_USER, ExecutionMotion.WAITING),
        (WorkItemState.COMPLETED, ExecutionMotion.TERMINAL),
        (WorkItemState.CANCELLED, ExecutionMotion.TERMINAL),
        (WorkItemState.INTERRUPTED, ExecutionMotion.TERMINAL),
    ],
)
def test_realtime_motion_is_derived_from_work_item_state(state, motion) -> None:
    view = describe_realtime_execution(item(state), now=NOW)
    assert view.motion is motion


def test_live_item_replaces_and_emits_heartbeat_after_threshold() -> None:
    view = describe_realtime_execution(item(WorkItemState.RUNNING), now=NOW)
    assert view.elapsed_seconds == 20
    assert view.heartbeat_due
    assert view.replace
    assert not view.consolidate


def test_terminal_item_consolidates_without_heartbeat() -> None:
    view = describe_realtime_execution(item(WorkItemState.COMPLETED), now=NOW)
    assert view.consolidate
    assert not view.replace
    assert not view.heartbeat_due


@pytest.mark.parametrize(
    ("seconds", "text"),
    [(0, "0s"), (9, "9s"), (65, "1m05s"), (3665, "1h01m")],
)
def test_elapsed_format_is_compact_and_stable(seconds, text) -> None:
    assert format_elapsed(seconds) == text
