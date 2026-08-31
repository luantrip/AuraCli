"""Headless composition coverage for auxiliary TUI screens."""

from unittest.mock import patch

import pytest
from textual.app import App, ComposeResult
from textual.widgets import Button, Static

from aura_cli.tui.screens.files_screen import FilesScreen
from aura_cli.tui.screens.monitor_screen import MonitorScreen
from aura_cli.tui.screens.paint_screen import PaintScreen
from aura_cli.tui.screens.tools_menu_screen import ToolsMenuScreen
from aura_cli.tui.tools import ToolAvailability
from aura_cli.tui.widgets.layout.external_tool_launcher import ExternalToolLauncher
from aura_cli.tui.widgets.monitor import AddressBar, ContentViewer, MonitorStatusBar
from aura_cli.tui.widgets.monitor.unavailable_panel import MonitorUnavailablePanel


class ScreenHost(App[None]):
    """Minimal host that permits pushing auxiliary screens."""

    def compose(self) -> ComposeResult:
        yield Static("host", id="host")


class LauncherHost(App[None]):
    """Minimal host for the reusable external launcher."""

    def __init__(self, available: bool) -> None:
        super().__init__()
        self.available = available

    def compose(self) -> ComposeResult:
        yield ExternalToolLauncher(
            available=self.available,
            description_lines=["Descrição"],
            features=["Recurso"],
            install_command="tool install",
        )


@pytest.mark.asyncio
async def test_external_launcher_exposes_only_valid_action_for_state() -> None:
    available_app = LauncherHost(True)
    async with available_app.run_test() as pilot:
        assert available_app.query_one("#launch_btn", Button).disabled is False
        assert not available_app.query(".install-command")
        await pilot.pause()

    unavailable_app = LauncherHost(False)
    async with unavailable_app.run_test() as pilot:
        assert not unavailable_app.query("#launch_btn")
        assert unavailable_app.query_one(".install-command", Static).render().plain == (
            "tool install"
        )
        await pilot.pause()


@pytest.mark.asyncio
async def test_files_and_paint_screens_render_unavailable_state() -> None:
    app = ScreenHost()
    unavailable = ToolAvailability(paint=False, files=False, monitor=False)

    async with app.run_test() as pilot:
        with patch("aura_cli.tui.screens.files_screen.get_tool_availability", return_value=unavailable):
            files = FilesScreen()
            app.push_screen(files)
            await pilot.pause()
            assert files.query_one("#files_launcher", ExternalToolLauncher)
            assert not files.query_one("#files_launcher").query("#launch_btn")
            app.pop_screen()

        with patch("aura_cli.tui.screens.paint_screen.get_tool_availability", return_value=unavailable):
            paint = PaintScreen()
            app.push_screen(paint)
            await pilot.pause()
            assert paint.query_one("#paint_launcher", ExternalToolLauncher)
            assert not paint.query_one("#paint_launcher").query("#launch_btn")
            await pilot.pause()


@pytest.mark.asyncio
async def test_tools_menu_mounts_availability_and_starts_on_aura() -> None:
    app = ScreenHost()
    availability = ToolAvailability(paint=False, files=True, monitor=False)

    with patch(
        "aura_cli.tui.screens.tools_menu_screen.get_tool_availability",
        return_value=availability,
    ):
        screen = ToolsMenuScreen()

    async with app.run_test() as pilot:
        app.push_screen(screen)
        await pilot.pause()

        cards = list(screen.query(".tool-card"))
        assert len(cards) == 5
        assert cards[0].has_class("selected")
        assert cards[1].has_class("unavailable")
        assert not cards[2].has_class("unavailable")
        assert cards[3].has_class("unavailable")
        assert screen.selected_index == 0
        await pilot.pause()


@pytest.mark.asyncio
async def test_monitor_screen_renders_dependency_fallback() -> None:
    app = ScreenHost()
    with patch(
        "aura_cli.tui.screens.monitor_screen.get_monitor_binary",
        return_value=None,
    ):
        screen = MonitorScreen()

    async with app.run_test() as pilot:
        app.push_screen(screen)
        await pilot.pause()
        assert screen.query_one(MonitorUnavailablePanel)
        assert not screen.query("#browser-container")
        await pilot.pause()


@pytest.mark.asyncio
async def test_monitor_screen_mounts_browser_surface_when_available() -> None:
    app = ScreenHost()
    with patch(
        "aura_cli.tui.screens.monitor_screen.get_monitor_binary",
        return_value="/tmp/chawan",
    ):
        screen = MonitorScreen()
        async with app.run_test() as pilot:
            app.push_screen(screen)
            await pilot.pause()
            assert screen.query_one(AddressBar)
            assert screen.query_one(ContentViewer)
            assert screen.query_one(MonitorStatusBar)
            assert not screen.query("#monitor-unavailable-state")
