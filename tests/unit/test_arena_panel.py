from aura_cli.cli.ui.components.arena_panel import render_arena_panel


def test_arena_panel_renders_status():
    panel = render_arena_panel({"run_id": "r1", "alive": ["a001"], "agents": 2})
    assert panel.title == "Arena"
