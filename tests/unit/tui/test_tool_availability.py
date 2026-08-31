"""Deterministic contracts for auxiliary TUI tool availability."""

from unittest.mock import Mock, patch

from aura_cli.tui.screens import tools_menu_screen
import aura_cli.tui.tools as tools
from aura_cli.tui.tools import ToolAvailability
from aura_cli.tui.tools.monitor.browser import MonitorBrowser


def test_tool_availability_refreshes_all_capabilities(monkeypatch) -> None:
    monkeypatch.setattr(
        tools,
        "_check_command",
        lambda command: command in {"python3", "tuifi"},
    )
    monkeypatch.setattr(tools.importlib.util, "find_spec", lambda _name: object())
    monkeypatch.setattr(tools, "_find_monitor_binary", lambda: "/tmp/cha")

    snapshot = tools.get_tool_availability()

    assert snapshot == ToolAvailability(True, True, True, "/tmp/cha")
    assert snapshot.any_available is True


def test_tool_availability_reports_missing_optional_tools(monkeypatch) -> None:
    monkeypatch.setattr(tools, "_check_command", lambda _command: False)
    monkeypatch.setattr(tools.importlib.util, "find_spec", lambda _name: None)
    monkeypatch.setattr(tools, "_find_monitor_binary", lambda: None)

    snapshot = tools.get_tool_availability()

    assert snapshot == ToolAvailability(False, False, False, None)
    assert snapshot.any_available is False


def test_tools_menu_uses_a_fresh_availability_snapshot() -> None:
    snapshot = ToolAvailability(paint=True, files=False, monitor=True)
    with patch.object(
        tools_menu_screen, "get_tool_availability", return_value=snapshot
    ):
        screen = tools_menu_screen.ToolsMenuScreen()

    availability = {tool.id: tool.available for tool in screen.tools}
    assert availability["paint"] is True
    assert availability["file_manager"] is False
    assert availability["monitor"] is True


def test_monitor_browser_queries_current_binary_status() -> None:
    browser = MonitorBrowser()
    with patch(
        "aura_cli.tui.tools.monitor.browser.get_monitor_binary",
        side_effect=["/tmp/cha", None],
    ):
        assert browser.is_available is True
        assert browser.is_available is False


def test_tools_menu_consumes_navigation_keys() -> None:
    screen = tools_menu_screen.ToolsMenuScreen()
    event = Mock(key="right")

    with patch.object(screen, "_update_selection"):
        screen.on_key(event)

    event.prevent_default.assert_called_once_with()
    event.stop.assert_called_once_with()
