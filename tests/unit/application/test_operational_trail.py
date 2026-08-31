"""Bounded operational trail contracts."""

from aura_cli.application.agents.events import AgiEvent, AgiEventType
from aura_cli.application.agents.operational_feedback import (
    OperationalTrail,
    build_operational_trail,
)


def event(task_id: str) -> AgiEvent:
    return AgiEvent(
        type=AgiEventType.TASK_START,
        task_id=task_id,
        data={"description": task_id},
    )


def test_trail_is_immutable_bounded_and_clearable() -> None:
    original = OperationalTrail(limit=2)
    trail = original.append("one").append("two").append("three")

    assert original.lines == ()
    assert trail.lines == ("two", "three")
    assert trail.clear().lines == ()


def test_trail_build_and_export_use_real_event_feedback() -> None:
    trail = build_operational_trail([event("one"), event("two")], limit=10)
    exported = trail.export_text()

    assert "Agent started task: one" in exported
    assert "Agent started task: two" in exported
    assert exported.startswith("# Aura Operational Trail")
