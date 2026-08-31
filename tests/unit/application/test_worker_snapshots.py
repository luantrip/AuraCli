from aura_cli.application.agents.snapshots import assess_snapshot_schedule


def test_snapshot_schedule_requires_minimum_and_interval() -> None:
    assert (
        assess_snapshot_schedule(
            message_count=4, last_snapshot_count=0, interval=3
        ).should_save
        is False
    )
    assert (
        assess_snapshot_schedule(
            message_count=5, last_snapshot_count=3, interval=3
        ).should_save
        is False
    )

    schedule = assess_snapshot_schedule(
        message_count=6, last_snapshot_count=3, interval=3
    )
    assert schedule.should_save is True
    assert schedule.message_count == 6


def test_snapshot_schedule_handles_history_reset() -> None:
    assert (
        assess_snapshot_schedule(
            message_count=5, last_snapshot_count=20, interval=5
        ).should_save
        is False
    )
