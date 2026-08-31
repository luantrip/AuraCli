"""Tests for the headless Core tool-display port."""

import pytest

from aura_cli.core import ui_panel


@pytest.fixture(autouse=True)
def restore_panel_state():
    original = (
        ui_panel._tool_call_presenter,
        ui_panel._compact_mode,
        ui_panel._panel_enabled,
        ui_panel._current_execution,
    )
    yield
    ui_panel._tool_call_presenter = original[0]
    ui_panel._compact_mode = original[1]
    ui_panel._panel_enabled = original[2]
    ui_panel._current_execution = original[3]


def test_display_is_inert_without_presentation_adapter() -> None:
    ui_panel.configure_tool_call_presenter(None)

    ui_panel.display_tool_call("read_file", {"path": "x"})

    assert ui_panel._current_execution is None


def test_display_delegates_modes_and_tracks_execution() -> None:
    calls = []

    class Execution:
        def __init__(self):
            self.success = None

        def mark_success(self, result, duration):
            self.success = (result, duration)

    execution = Execution()
    ui_panel.configure_tool_call_presenter(
        lambda name, params, compact, panel: (
            calls.append((name, params, compact, panel)) or execution
        )
    )
    ui_panel.set_compact_mode(False)
    ui_panel.enable_panel_mode()

    ui_panel.display_tool_call("write_file", {"path": "x"})
    ui_panel.mark_tool_success("ok", 0.2)

    assert calls == [("write_file", {"path": "x"}, False, True)]
    assert execution.success == ("ok", 0.2)
    assert ui_panel._current_execution is None
