"""Exercise AuraTUI mounting and navigation in Textual headless mode."""

from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path

from aura_cli.tui.app import AuraTUI
from aura_cli.tui.widgets.chat import AuraChatLog
from aura_cli.tui.widgets.event_stream_panel import EventStreamPanel
from aura_cli.tui.widgets.input import AuraInputBar


async def run_probe() -> dict[str, object]:
    app = AuraTUI()
    async with app.run_test(size=(140, 48)) as pilot:
        await pilot.pause()
        assert app.runtime_state.phase.value == "ready"
        assert app.query_one(AuraChatLog).is_attached
        assert app.query_one(AuraInputBar).is_attached
        assert app.query_one(EventStreamPanel).is_attached
        app.action_toggle_focus_mode()
        assert app.surface_state.spatial_focus
        app.action_toggle_focus_mode()
        assert not app.surface_state.spatial_focus
        app.action_show_events()
        assert app.surface_state.active_drawer is not None
        app.action_toggle_command_palette()
        await pilot.pause()
        palette_visible = app.query_one("#command_palette").display
        assert palette_visible
        app.action_toggle_command_palette()
        await pilot.pause()
        app.exit()
        await pilot.pause()
    return {
        "runtime_phase": app.runtime_state.phase.value,
        "focus_round_trip": True,
        "palette_toggled": True,
        "mounted_widgets": ["chat", "input", "event_stream"],
    }


def main() -> None:
    report = {
        "contract": "aura-tui-headless-v1",
        "checks": asyncio.run(run_probe()),
        "aura_home": os.environ.get("AURA_HOME", ""),
        "status": "READY",
    }
    root = Path(os.environ.get("AURA_HOME", "."))
    root.mkdir(parents=True, exist_ok=True)
    (root / "tui-headless-probe.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print("TUI_HEADLESS_READY")
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
