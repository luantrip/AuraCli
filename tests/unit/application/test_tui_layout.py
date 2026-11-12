import pytest

from aura_cli.application.presentation.tui_layout import (
    DrawerMode,
    TuiDensity,
    TuiDrawer,
    TuiLayoutState,
    decide_tui_layout,
)


@pytest.mark.parametrize("width", [60, 80, 100])
def test_narrow_layout_keeps_conversation_primary(width: int) -> None:
    plan = decide_tui_layout(
        TuiLayoutState(width, 30, requested_drawer=TuiDrawer.ACTIVITY)
    )

    assert plan.drawer_mode is DrawerMode.OVERLAY
    assert plan.drawer_width == width


@pytest.mark.parametrize("width", [120, 160])
def test_wide_layout_allows_only_one_bounded_drawer(width: int) -> None:
    plan = decide_tui_layout(
        TuiLayoutState(width, 40, requested_drawer=TuiDrawer.WORKSPACE)
    )

    assert plan.drawer is TuiDrawer.WORKSPACE
    assert plan.drawer_mode is DrawerMode.SPLIT
    assert 32 <= plan.drawer_width <= 44
    assert width - plan.drawer_width >= 80


def test_focus_mode_suppresses_drawers_and_secondary_chrome() -> None:
    plan = decide_tui_layout(
        TuiLayoutState(160, 50, requested_drawer=TuiDrawer.ACTIVITY, focus_mode=True)
    )

    assert plan.drawer is None
    assert not plan.show_task_panel


def test_low_terminal_uses_compact_density() -> None:
    plan = decide_tui_layout(TuiLayoutState(120, 20))

    assert plan.density is TuiDensity.COMPACT
    assert not plan.show_header
    assert not plan.show_footer_details


def test_startup_state_opens_no_drawer_so_the_default_is_single_column_chat() -> None:
    """P1-9 — the TUI boots conversation-first.

    ``TuiSurfaceState`` starts with no active drawer, so with the default state the
    layout plan allocates the full width to the conversation at every viewport.
    This pins the default against a regression that re-opens a side panel on boot.
    """
    from aura_cli.application.presentation.tui_surface_state import TuiSurfaceState

    startup = TuiSurfaceState()
    assert startup.active_drawer is None

    for width, height in ((200, 50), (120, 40), (100, 30), (80, 24), (70, 20)):
        plan = decide_tui_layout(
            TuiLayoutState(
                width=width,
                height=height,
                requested_drawer=startup.active_drawer,
                focus_mode=startup.spatial_focus,
            )
        )
        assert plan.drawer is None, (width, height)
        assert plan.conversation_width == 0, (width, height)  # no column stolen


def test_a_drawer_appears_only_after_it_is_requested() -> None:
    """The panels are on-demand, not default chrome."""
    base = TuiLayoutState(width=160, height=40)
    assert decide_tui_layout(base).drawer is None
    assert (
        decide_tui_layout(
            TuiLayoutState(width=160, height=40, requested_drawer=TuiDrawer.ACTIVITY)
        ).drawer
        is TuiDrawer.ACTIVITY
    )
