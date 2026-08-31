import pytest

from aura_cli.application.presentation.tui_layout import (
    DrawerMode,
    TuiDensity,
    TuiDrawer,
    TuiLayoutState,
    decide_tui_layout,
)


@pytest.mark.parametrize(
    ("width", "height", "density", "mode"),
    [
        (60, 20, TuiDensity.COMPACT, DrawerMode.OVERLAY),
        (80, 24, TuiDensity.COMFORTABLE, DrawerMode.OVERLAY),
        (100, 30, TuiDensity.COMFORTABLE, DrawerMode.OVERLAY),
        (120, 30, TuiDensity.COMFORTABLE, DrawerMode.SPLIT),
        (160, 40, TuiDensity.SPACIOUS, DrawerMode.SPLIT),
        (200, 50, TuiDensity.SPACIOUS, DrawerMode.SPLIT),
    ],
)
def test_visual_acceptance_matrix(width, height, density, mode) -> None:
    default = decide_tui_layout(TuiLayoutState(width, height))
    opened = decide_tui_layout(
        TuiLayoutState(width, height, requested_drawer=TuiDrawer.ACTIVITY)
    )
    focused = decide_tui_layout(
        TuiLayoutState(
            width,
            height,
            requested_drawer=TuiDrawer.ACTIVITY,
            focus_mode=True,
        )
    )

    assert default.drawer is None
    assert opened.density is density
    assert opened.drawer_mode is mode
    assert focused.drawer is None
    if mode is DrawerMode.SPLIT:
        assert width - opened.drawer_width >= 80
    else:
        assert opened.drawer_width == width
