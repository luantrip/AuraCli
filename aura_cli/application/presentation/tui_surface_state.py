"""State machine for contextual TUI surfaces and attention."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from enum import Enum

from aura_cli.application.presentation.tui_layout import TuiDrawer

MAX_UNREAD_PER_SECTION = 99


class ActivitySection(str, Enum):
    EVENTS = "events"
    ANALYSIS = "analysis"
    MEMORY = "memory"
    WORKFLOWS = "workflows"


def activity_section_for_route(route: str | None) -> ActivitySection:
    """Resolve an activity section from an optional semantic route.

    Unknown or absent routes intentionally fall back to the event stream so
    legacy producers keep their previous behavior.
    """
    normalized = (route or "").strip().casefold().replace("-", "_")
    aliases = {
        "events": ActivitySection.EVENTS,
        "event": ActivitySection.EVENTS,
        "event_stream": ActivitySection.EVENTS,
        "analysis": ActivitySection.ANALYSIS,
        "code_analysis": ActivitySection.ANALYSIS,
        "memory": ActivitySection.MEMORY,
        "notebook": ActivitySection.MEMORY,
        "workflows": ActivitySection.WORKFLOWS,
        "workflow": ActivitySection.WORKFLOWS,
    }
    return aliases.get(normalized, ActivitySection.EVENTS)


@dataclass(frozen=True)
class TuiSurfaceState:
    active_drawer: TuiDrawer | None = None
    activity_section: ActivitySection = ActivitySection.EVENTS
    spatial_focus: bool = False
    task_filter: str | None = None
    unread: dict[ActivitySection, int] = field(default_factory=dict)

    @property
    def activity_attention(self) -> int:
        return sum(self.unread.values())


def toggle_drawer(state: TuiSurfaceState, drawer: TuiDrawer) -> TuiSurfaceState:
    active = None if state.active_drawer is drawer else drawer
    return replace(state, active_drawer=active, spatial_focus=False)


def set_spatial_focus(state: TuiSurfaceState, enabled: bool) -> TuiSurfaceState:
    return replace(
        state,
        spatial_focus=enabled,
        active_drawer=None if enabled else state.active_drawer,
    )


def set_task_filter(state: TuiSurfaceState, task_id: str | None) -> TuiSurfaceState:
    return replace(state, task_filter=task_id)


def clear_focus(state: TuiSurfaceState) -> TuiSurfaceState:
    """Clear task focus without changing the currently selected drawer."""
    return replace(state, spatial_focus=False, task_filter=None)


def dismiss_navigation_layer(state: TuiSurfaceState) -> TuiSurfaceState:
    """Dismiss the top transient navigation layer in a deterministic order."""
    if state.active_drawer is not None:
        return replace(state, active_drawer=None)
    if state.spatial_focus or state.task_filter is not None:
        return clear_focus(state)
    return state


def select_activity(
    state: TuiSurfaceState,
    section: ActivitySection,
    *,
    reveal: bool = True,
) -> TuiSurfaceState:
    unread = dict(state.unread)
    unread.pop(section, None)
    return replace(
        state,
        activity_section=section,
        active_drawer=TuiDrawer.ACTIVITY if reveal else state.active_drawer,
        spatial_focus=False if reveal else state.spatial_focus,
        unread=unread,
    )


def mark_activity(state: TuiSurfaceState, section: ActivitySection) -> TuiSurfaceState:
    if state.active_drawer is TuiDrawer.ACTIVITY and state.activity_section is section:
        return state
    unread = dict(state.unread)
    unread[section] = min(
        unread.get(section, 0) + 1,
        MAX_UNREAD_PER_SECTION,
    )
    return replace(state, unread=unread)


__all__ = [
    "MAX_UNREAD_PER_SECTION",
    "ActivitySection",
    "TuiSurfaceState",
    "activity_section_for_route",
    "clear_focus",
    "dismiss_navigation_layer",
    "mark_activity",
    "select_activity",
    "set_spatial_focus",
    "set_task_filter",
    "toggle_drawer",
]
