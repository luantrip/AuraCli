"""Actionable empty state for the event activity stream."""

import pytest
from textual.app import App, ComposeResult
from textual.widgets import Select

from aura_cli.tui.widgets.event_stream_panel import EventStreamPanel


class EventStreamHarness(App[None]):
    """Minimal host for the event stream widget."""

    def compose(self) -> ComposeResult:
        yield EventStreamPanel(id="events")


@pytest.mark.asyncio
async def test_event_stream_empty_state_tracks_events_and_clear() -> None:
    app = EventStreamHarness()

    async with app.run_test() as pilot:
        panel = app.query_one("#events", EventStreamPanel)
        empty = panel.query_one("#event-empty-state")
        filter_select = panel.query_one("#event-filter-select", Select)

        assert empty.display is True
        assert filter_select.value == ""
        panel.write_event(
            {
                "type": "agi_task_start",
                "task_id": "task-1",
                "timestamp": 0,
                "data": {"description": "Testar"},
            }
        )
        await pilot.pause()
        assert empty.display is False

        panel.clear()
        await pilot.pause()
        assert empty.display is True
        assert panel._events == []
        assert filter_select.value == ""


@pytest.mark.asyncio
async def test_event_stream_filter_hides_without_dropping_events() -> None:
    """Filtering must be reversible and must preserve the retained stream."""
    app = EventStreamHarness()

    async with app.run_test() as pilot:
        panel = app.query_one("#events", EventStreamPanel)
        panel.write_event(
            {
                "type": "agi_task_start",
                "task_id": "task-1",
                "timestamp": 0,
                "data": {"description": "Iniciar"},
            }
        )
        panel.write_event(
            {
                "type": "tool_executing",
                "task_id": "task-1",
                "timestamp": 0,
                "data": {"tool_name": "read_file"},
            }
        )
        await pilot.pause()

        panel.set_event_filter(["tool_executing"])
        assert len(panel._events) == 2
        assert [event.display for event in panel._events] == [False, True]
        assert panel.event_filter == frozenset({"tool_executing"})

        panel.clear_event_filter()
        assert [event.display for event in panel._events] == [True, True]
        assert panel.event_filter is None


@pytest.mark.asyncio
async def test_event_stream_filter_control_updates_projection() -> None:
    """The mounted selector must drive the same reversible filter API."""
    app = EventStreamHarness()

    async with app.run_test() as pilot:
        panel = app.query_one("#events", EventStreamPanel)
        panel.write_event(
            {
                "type": "agi_task_start",
                "task_id": "task-1",
                "timestamp": 0,
                "data": {"description": "Iniciar"},
            }
        )
        panel.write_event(
            {
                "type": "tool_executing",
                "task_id": "task-1",
                "timestamp": 0,
                "data": {"tool_name": "read_file"},
            }
        )
        select = panel.query_one("#event-filter-select", Select)
        select.value = "tool_executing"
        await pilot.pause()

        assert panel.event_filter == frozenset({"tool_executing"})
        assert [event.display for event in panel._events] == [False, True]


def test_event_stream_event_count_is_instance_local() -> None:
    first = EventStreamPanel()
    second = EventStreamPanel()

    first._event_count = 3

    assert first._event_count == 3
    assert second._event_count == 0
