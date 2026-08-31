"""Localized copy, focus targets, and unavailable-domain state contracts."""

from unittest.mock import patch

import pytest
from textual.app import App, ComposeResult
from textual.widgets import Button, Static

from aura_cli.tui.screens import files_screen, paint_screen
from aura_cli.tui.tools import ToolAvailability
from aura_cli.tui.widgets.monitor.unavailable_panel import MonitorUnavailablePanel


class UnavailableHarness(App[None]):
    def compose(self) -> ComposeResult:
        yield MonitorUnavailablePanel()


class ScreenHostHarness(App[None]):
    def compose(self) -> ComposeResult:
        yield Static("")


@pytest.mark.asyncio
async def test_monitor_unavailable_panel_explains_dependency_in_portuguese() -> None:
    app = UnavailableHarness()

    async with app.run_test() as pilot:
        title = app.query_one(".unavailable-title", Static)
        state = app.query_one("#monitor-unavailable-state")

        assert state.has_class("unavailable-message")
        assert str(title.render()) == "Monitor indisponível"
        assert "Dependência: Chawan" in str(
            app.query_one(".unavailable-label", Static).render()
        )
        await pilot.pause()


@pytest.mark.asyncio
async def test_files_launch_restores_focus_before_callback() -> None:
    app = ScreenHostHarness()
    async with app.run_test() as pilot:
        screen = files_screen.FilesScreen()
        with (
            patch.object(
                files_screen,
                "get_tool_availability",
                return_value=ToolAvailability(paint=False, files=True, monitor=False),
            ),
            patch.object(files_screen, "pop_screen_and_restore_focus") as restore_focus,
            patch.object(app, "action_launch_files", create=True) as launch,
        ):
            app.push_screen(screen)
            await pilot.pause()
            screen.action_launch()

        restore_focus.assert_called_once_with(app)
        launch.assert_called_once_with()


@pytest.mark.asyncio
async def test_paint_launch_restores_focus_before_callback() -> None:
    app = ScreenHostHarness()
    async with app.run_test() as pilot:
        screen = paint_screen.PaintScreen()
        with (
            patch.object(
                paint_screen,
                "get_tool_availability",
                return_value=ToolAvailability(paint=True, files=False, monitor=False),
            ),
            patch.object(paint_screen, "pop_screen_and_restore_focus") as restore_focus,
            patch.object(app, "action_launch_paint", create=True) as launch,
        ):
            app.push_screen(screen)
            await pilot.pause()
            screen.action_launch()

        restore_focus.assert_called_once_with(app)
        launch.assert_called_once_with()


@pytest.mark.asyncio
async def test_history_empty_state_focuses_first_action(tmp_path) -> None:
    from aura_cli.tui.widgets.history.browser_panel import HistoryBrowserPanel

    class HistoryFocusHarness(App[None]):
        def compose(self) -> ComposeResult:
            yield HistoryBrowserPanel(sessions_dir=tmp_path)

    app = HistoryFocusHarness()
    async with app.run_test() as pilot:
        assert isinstance(app.focused, Button)
        assert app.focused.id == "history-start"
        await pilot.pause()
