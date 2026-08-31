"""Pure contracts for TUI activity and navigation state."""

from aura_cli.application.presentation.tui_surface_state import (
    MAX_UNREAD_PER_SECTION,
    ActivitySection,
    TuiSurfaceState,
    activity_section_for_route,
    mark_activity,
)


def test_activity_section_routes_cover_public_aliases() -> None:
    assert activity_section_for_route("events") is ActivitySection.EVENTS
    assert activity_section_for_route("event-stream") is ActivitySection.EVENTS
    assert activity_section_for_route("code-analysis") is ActivitySection.ANALYSIS
    assert activity_section_for_route("notebook") is ActivitySection.MEMORY
    assert activity_section_for_route("workflow") is ActivitySection.WORKFLOWS


def test_activity_section_unknown_route_preserves_legacy_events_fallback() -> None:
    assert activity_section_for_route(None) is ActivitySection.EVENTS
    assert activity_section_for_route("new-future-surface") is ActivitySection.EVENTS


def test_unread_badge_is_bounded_for_long_event_streams() -> None:
    state = TuiSurfaceState()
    for _ in range(MAX_UNREAD_PER_SECTION + 20):
        state = mark_activity(state, ActivitySection.EVENTS)

    assert state.unread[ActivitySection.EVENTS] == MAX_UNREAD_PER_SECTION
