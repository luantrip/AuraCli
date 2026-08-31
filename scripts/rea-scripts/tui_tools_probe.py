"""Exercise auxiliary TUI tool screens without launching external binaries."""

from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
from unittest.mock import patch

from textual.app import App, ComposeResult
from textual.widgets import Static

from aura_cli.tui.screens.files_screen import FilesScreen
from aura_cli.tui.screens.monitor_screen import MonitorScreen
from aura_cli.tui.screens.paint_screen import PaintScreen
from aura_cli.tui.screens.tools_menu_screen import ToolsMenuScreen
from aura_cli.tui.tools import ToolAvailability
from aura_cli.tui.widgets.layout.external_tool_launcher import ExternalToolLauncher
from aura_cli.tui.widgets.monitor.unavailable_panel import MonitorUnavailablePanel


class ScreenHost(App[None]):
    def compose(self) -> ComposeResult:
        yield Static("host", id="host")


async def run_probe() -> dict[str, object]:
    app = ScreenHost()
    unavailable = ToolAvailability(paint=False, files=False, monitor=False)
    checks: dict[str, object] = {}
    async with app.run_test(size=(140, 48)) as pilot:
        with patch("aura_cli.tui.screens.files_screen.get_tool_availability", return_value=unavailable):
            files = FilesScreen()
            app.push_screen(files)
            await pilot.pause()
            assert files.query_one("#files_launcher", ExternalToolLauncher)
            assert not files.query_one("#files_launcher").query("#launch_btn")
            checks["files_unavailable"] = True
            app.pop_screen()

        with patch("aura_cli.tui.screens.paint_screen.get_tool_availability", return_value=unavailable):
            paint = PaintScreen()
            app.push_screen(paint)
            await pilot.pause()
            assert paint.query_one("#paint_launcher", ExternalToolLauncher)
            assert not paint.query_one("#paint_launcher").query("#launch_btn")
            checks["paint_unavailable"] = True
            app.pop_screen()

        with patch("aura_cli.tui.screens.monitor_screen.get_monitor_binary", return_value=None):
            monitor = MonitorScreen()
            app.push_screen(monitor)
            await pilot.pause()
            assert monitor.query_one(MonitorUnavailablePanel)
            assert not monitor.query("#browser-container")
            checks["monitor_fallback"] = True
            app.pop_screen()

        with patch("aura_cli.tui.screens.tools_menu_screen.get_tool_availability", return_value=unavailable):
            menu = ToolsMenuScreen()
            app.push_screen(menu)
            await pilot.pause()
            cards = list(menu.query(".tool-card"))
            assert len(cards) == 5
            assert cards[0].has_class("selected")
            assert cards[1].has_class("unavailable")
            checks["menu_cards"] = len(cards)
            app.pop_screen()
        app.exit()
        await pilot.pause()
    return checks


def main() -> None:
    report = {
        "contract": "aura-tui-tools-v1",
        "checks": asyncio.run(run_probe()),
        "aura_home": os.environ.get("AURA_HOME", ""),
        "status": "READY",
    }
    root = Path(os.environ.get("AURA_HOME", "."))
    root.mkdir(parents=True, exist_ok=True)
    (root / "tui-tools-probe.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print("TUI_TOOLS_READY")
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
