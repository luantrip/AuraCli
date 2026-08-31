import json
from pathlib import Path

from aura_cli.application.presentation.visual_acceptance import run_visual_scenario

SCENARIOS = json.loads(
    (Path(__file__).parents[2] / "fixtures/visual_system/scenarios.json").read_text()
)


def test_streaming_survives_resize_and_consolidates_without_duplicate() -> None:
    frames = run_visual_scenario(
        SCENARIOS["stream_resize"],
        viewports=[(60, 20), (80, 24), (120, 30), (160, 40)],
    )
    assert [frame.density for frame in frames] == [
        "compact",
        "comfortable",
        "comfortable",
        "spacious",
    ]
    assert all(len(frame.active_keys) <= 1 for frame in frames)
    assert frames[-1].active_keys == ()
    assert frames[-1].completed_keys == ("task:task",)
    assert len(frames[-1].conversation) == 1


def test_failure_cancel_and_resume_have_distinct_temporal_outcomes() -> None:
    failure = run_visual_scenario(
        SCENARIOS["failure"], viewports=[(80, 24)], app_focused=False
    )
    cancel = run_visual_scenario(SCENARIOS["cancel"], viewports=[(80, 24)])
    resume = run_visual_scenario(SCENARIOS["resume"], viewports=[(80, 24)])

    assert failure[-1].announcements == ("Falha real",)
    assert "falhou" in failure[-1].conversation[0]
    assert "cancelled" in cancel[-1].conversation[0]
    assert resume[1].active_keys == ()
    assert resume[2].active_keys == ("task:resume",)
    assert resume[-1].completed_keys == ("task:resume",)


def test_child_approval_is_announced_and_removed_only_after_resolution() -> None:
    frames = run_visual_scenario(
        SCENARIOS["child_approval"],
        viewports=[(100, 30)],
        focused_task_id="parent",
    )
    assert frames[1].blocking_keys == ("task:child/execution:a1",)
    assert frames[1].announcements == ("Aplicar alteração?",)
    assert frames[2].blocking_keys == ()


def test_background_completion_has_plain_accessible_announcement() -> None:
    frames = run_visual_scenario(SCENARIOS["background"], viewports=[(60, 20)])
    assert frames[-1].announcements
    announcement = frames[-1].announcements[-1]
    assert "completed" in announcement
    assert "[bold" not in announcement


def test_malformed_events_are_ignored_without_breaking_valid_replay() -> None:
    frames = run_visual_scenario(
        [
            {},
            {
                "type": "chat_message",
                "task_id": "task-valid",
                "data": {"sender": "agent", "content": "continua"},
            },
        ],
        viewports=[(80, 24)],
    )

    assert len(frames) == 1
    assert frames[0].event_type == "chat_message"
    assert frames[0].width == 80
