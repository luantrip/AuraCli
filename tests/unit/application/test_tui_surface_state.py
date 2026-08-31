from aura_cli.application.presentation.tui_layout import TuiDrawer
from aura_cli.application.presentation.tui_surface_state import (
    ActivitySection,
    TuiSurfaceState,
    clear_focus,
    dismiss_navigation_layer,
    mark_activity,
    select_activity,
    set_spatial_focus,
    set_task_filter,
    toggle_drawer,
)


def test_only_one_drawer_can_be_active() -> None:
    state = toggle_drawer(TuiSurfaceState(), TuiDrawer.WORKSPACE)
    state = toggle_drawer(state, TuiDrawer.ACTIVITY)

    assert state.active_drawer is TuiDrawer.ACTIVITY


def test_spatial_focus_closes_drawer_without_changing_task_filter() -> None:
    state = set_task_filter(TuiSurfaceState(TuiDrawer.ACTIVITY), "task-1")
    state = set_spatial_focus(state, True)

    assert state.active_drawer is None
    assert state.spatial_focus
    assert state.task_filter == "task-1"


def test_hidden_activity_accumulates_attention() -> None:
    state = mark_activity(TuiSurfaceState(), ActivitySection.MEMORY)
    state = mark_activity(state, ActivitySection.MEMORY)

    assert state.activity_attention == 2


def test_selecting_activity_clears_only_that_attention() -> None:
    state = mark_activity(TuiSurfaceState(), ActivitySection.MEMORY)
    state = mark_activity(state, ActivitySection.EVENTS)
    state = select_activity(state, ActivitySection.MEMORY)

    assert state.active_drawer is TuiDrawer.ACTIVITY
    assert state.activity_section is ActivitySection.MEMORY
    assert state.unread == {ActivitySection.EVENTS: 1}


def test_visible_activity_does_not_accumulate_attention() -> None:
    state = TuiSurfaceState(
        active_drawer=TuiDrawer.ACTIVITY,
        activity_section=ActivitySection.EVENTS,
    )

    assert mark_activity(state, ActivitySection.EVENTS) is state


def test_clear_focus_removes_task_filter_but_preserves_drawer() -> None:
    state = TuiSurfaceState(
        active_drawer=TuiDrawer.ACTIVITY,
        spatial_focus=True,
        task_filter="task-1",
    )

    cleared = clear_focus(state)

    assert cleared.active_drawer is TuiDrawer.ACTIVITY
    assert cleared.spatial_focus is False
    assert cleared.task_filter is None


def test_dismiss_navigation_closes_drawer_before_clearing_focus() -> None:
    state = TuiSurfaceState(
        active_drawer=TuiDrawer.ACTIVITY,
        spatial_focus=True,
        task_filter="task-1",
    )

    drawer_closed = dismiss_navigation_layer(state)
    focus_cleared = dismiss_navigation_layer(drawer_closed)

    assert drawer_closed.active_drawer is None
    assert drawer_closed.spatial_focus is True
    assert drawer_closed.task_filter == "task-1"
    assert focus_cleared == TuiSurfaceState()
