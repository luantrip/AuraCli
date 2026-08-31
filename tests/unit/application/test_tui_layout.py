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
