from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from textual.containers import Container, Grid
from textual.widgets import TabbedContent

from aura_cli.application.presentation.tui_layout import TuiDrawer
from aura_cli.application.presentation.tui_surface_state import ActivitySection
from aura_cli.tui.app import AuraTUI
from aura_cli.tui.widgets.code_analysis_panel import CodeAnalysisPanel


@pytest.mark.asyncio
async def test_conversation_owns_viewport_until_drawer_is_requested() -> None:
    app = AuraTUI(app_loop=MagicMock())

    async with app.run_test(size=(160, 40)) as pilot:
        await pilot.pause()
        grid = app.query_one("#main_grid", Grid)
        left = app.query_one("#left_panel", Container)
        center = app.query_one("#center_panel", Container)
        right = app.query_one("#right_panel", Container)

        assert not left.display
        assert not right.display
        assert center.region.width >= 150
        assert grid.has_class("density-spacious")

        app.action_toggle_analysis_event_panel()
        await pilot.pause()
        await pilot.pause()

        assert right.display
        assert not left.display
        assert grid.has_class("drawer-open")
        assert center.region.width >= 110
        assert app.focused is app.query_one("#right_tabs").children[0]


@pytest.mark.asyncio
async def test_narrow_drawer_becomes_overlay_and_focus_restores_chat() -> None:
    app = AuraTUI(app_loop=MagicMock())

    async with app.run_test(size=(80, 24)) as pilot:
        app.action_toggle_workspace_panel()
        await pilot.pause()
        grid = app.query_one("#main_grid", Grid)
        left = app.query_one("#left_panel", Container)

        assert left.display
        assert grid.has_class("drawer-overlay")

        app.action_toggle_focus_mode()
        await pilot.pause()

        assert not left.display
        assert not grid.has_class("drawer-open")


@pytest.mark.asyncio
async def test_drawer_switch_keeps_workspace_and_activity_exclusive() -> None:
    app = AuraTUI(app_loop=MagicMock())

    async with app.run_test(size=(160, 40)) as pilot:
        await pilot.pause()
        app.action_toggle_workspace_panel()
        await pilot.pause()
        await pilot.pause()

        assert app.surface_state.active_drawer is TuiDrawer.WORKSPACE
        assert app.query_one("#left_panel", Container).has_class("drawer-visible")
        assert not app.query_one("#right_panel", Container).has_class("drawer-visible")
        assert app.focused is app.query_one("#directory_tree")

        app.action_toggle_analysis_event_panel()
        await pilot.pause()
        await pilot.pause()

        assert app.surface_state.active_drawer is TuiDrawer.ACTIVITY
        assert not app.query_one("#left_panel", Container).has_class("drawer-visible")
        assert app.query_one("#right_panel", Container).has_class("drawer-visible")
        assert app.focused is app.query_one("#right_tabs").children[0]

        app.action_toggle_analysis_event_panel()
        await pilot.pause()
        await pilot.pause()
        assert app.surface_state.active_drawer is None
        assert app.focused is app.query_one("#main_input")


@pytest.mark.asyncio
async def test_codebase_results_sync_activity_state_and_visible_tab() -> None:
    app = AuraTUI(app_loop=MagicMock())
    view = SimpleNamespace(
        chat_markdown="Análise pronta",
        as_panel_payload=lambda: {"summary": "ok"},
    )

    async with app.run_test(size=(160, 40)) as pilot:
        await pilot.pause()
        with (
            patch("aura_cli.tui.app.build_codebase_analysis_view", return_value=view),
            patch.object(app, "post_message_to_chat"),
            patch.object(CodeAnalysisPanel, "update_analysis_results") as update,
        ):
            app._display_codebase_investigation_results({"files": []})
            await pilot.pause()

        tabs = app.query_one("#right_tabs", TabbedContent)
        assert tabs.active == "analysis_tab"
        assert app.surface_state.activity_section is ActivitySection.ANALYSIS
        update.assert_called_once_with({"summary": "ok"})


@pytest.mark.asyncio
async def test_expensive_activity_panels_mount_only_when_requested() -> None:
    app = AuraTUI(app_loop=MagicMock())

    async with app.run_test(size=(160, 40)) as pilot:
        await pilot.pause()
        assert not app.query("#code_analysis_panel")
        assert not app.query("#memory_browser")

        app.action_show_memory()
        await pilot.pause()

        assert app.query("#memory_browser")
        assert not app.query("#code_analysis_panel")
