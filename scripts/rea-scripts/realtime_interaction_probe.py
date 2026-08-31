"""Exercise realtime input, surface navigation, and dashboard contracts."""

from __future__ import annotations

import json
import os
from pathlib import Path

from aura_cli.application.presentation.command_routing import (
    PresentationCommandAction,
    PresentationCommandRouter,
)
from aura_cli.application.presentation.input_routing import (
    PresentationInputRoute,
    route_presentation_input,
)
from aura_cli.application.presentation.live_dashboard import (
    DashboardState,
    TaskState,
    build_dashboard_summary,
    classify_dashboard_message,
)
from aura_cli.application.presentation.tui_layout import TuiDrawer
from aura_cli.application.presentation.tui_surface_state import (
    ActivitySection,
    TuiSurfaceState,
    activity_section_for_route,
    dismiss_navigation_layer,
    mark_activity,
    select_activity,
    set_spatial_focus,
    set_task_filter,
    toggle_drawer,
)


class IntentRouter:
    def __init__(self, agi: bool) -> None:
        self.agi = agi

    def should_use_agi_worker(self, _command: str) -> bool:
        return self.agi


def check_input_and_commands() -> dict[str, object]:
    router = PresentationCommandRouter()
    assert router.classify_command("/help") is PresentationCommandAction.HELP
    assert router.classify_command("/model cerebras") is PresentationCommandAction.MODEL
    assert router.classify_command("/config set x") is PresentationCommandAction.PASSTHROUGH
    assert router.classify_command("/unknown") is PresentationCommandAction.UNHANDLED
    assert router.should_use_agi_worker("implemente uma API segura")
    assert not router.should_use_agi_worker("/agi faça isso")
    assert route_presentation_input(
        "analise o codebase inteiro",
        router=IntentRouter(True),
        runtime_available=True,
    ) is PresentationInputRoute.CODEBASE_INVESTIGATION
    assert route_presentation_input(
        "crie um endpoint com database e migration",
        router=IntentRouter(True),
        runtime_available=True,
    ) is PresentationInputRoute.AGI_WORKER
    assert route_presentation_input(
        "olá",
        router=IntentRouter(False),
        runtime_available=True,
    ) is PresentationInputRoute.DIRECT
    assert route_presentation_input(
        "olá",
        router=IntentRouter(True),
        runtime_available=False,
    ) is PresentationInputRoute.UNAVAILABLE
    return {
        "commands": 4,
        "input_routes": [route.value for route in PresentationInputRoute],
    }


def check_surface_navigation() -> dict[str, object]:
    state = TuiSurfaceState()
    state = mark_activity(state, ActivitySection.ANALYSIS)
    assert state.activity_attention == 1
    state = select_activity(state, ActivitySection.ANALYSIS)
    assert state.active_drawer is TuiDrawer.ACTIVITY
    assert state.activity_attention == 0
    state = set_task_filter(state, "task-1")
    state = set_spatial_focus(state, True)
    assert state.active_drawer is None and state.spatial_focus
    state = toggle_drawer(state, TuiDrawer.WORKSPACE)
    assert state.active_drawer is TuiDrawer.WORKSPACE
    state = dismiss_navigation_layer(state)
    assert state.active_drawer is None
    state = dismiss_navigation_layer(state)
    assert state.task_filter is None and not state.spatial_focus
    assert activity_section_for_route("code-analysis") is ActivitySection.ANALYSIS
    assert activity_section_for_route("notebook") is ActivitySection.MEMORY
    assert activity_section_for_route("unknown") is ActivitySection.EVENTS
    return {"attention_after_select": state.activity_attention, "final_drawer": None}


def check_dashboard() -> dict[str, object]:
    dashboard = DashboardState(mode="AGI", status="Executando")
    dashboard.add_task("task-1", "Indexar")
    dashboard.add_task("task-2", "Validar")
    dashboard.update_task("task-1", state=TaskState.RUNNING, progress=0.5, timestamp=10)
    dashboard.update_task(
        "task-1", state=TaskState.COMPLETED, progress=1.2, result="Done", timestamp=20
    )
    dashboard.update_task("task-2", state=TaskState.FAILED, error="Failed", timestamp=21)
    dashboard.add_tool("read_file")
    dashboard.add_tool("read_file")
    dashboard.add_message("working", "info", 10)
    assert classify_dashboard_message("Analisando com read_file").phase == "analyzing"
    decision = classify_dashboard_message("Concluído após run_shell")
    assert decision.completed and decision.tool_name == "Run Shell"
    summary = build_dashboard_summary(dashboard, 21.0)
    assert summary["completed_tasks"] == 1
    assert summary["failed_tasks"] == 1
    assert summary["tools_used"] == 1
    assert dashboard.tasks[0].progress == 1.0
    return summary


def main() -> None:
    report = {
        "contract": "aura-realtime-interaction-v1",
        "checks": {
            "input_commands": check_input_and_commands(),
            "surface_navigation": check_surface_navigation(),
            "dashboard": check_dashboard(),
        },
        "aura_home": os.environ.get("AURA_HOME", ""),
        "status": "READY",
    }
    output_path = Path(os.environ.get("AURA_HOME", ".")) / "realtime-interaction-probe.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print("INTERACTION_READY")
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
