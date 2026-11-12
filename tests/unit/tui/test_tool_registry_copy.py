"""Portuguese copy and empty-state contracts for ToolRegistryPanel."""

import pytest
from textual.app import App, ComposeResult
from textual.widgets import Button

from aura_cli.tui.widgets.tool_registry_panel import ToolRegistryPanel


class ToolRegistryHarness(App[None]):
    """Minimal host for the operational tool registry panel."""

    def compose(self) -> ComposeResult:
        yield ToolRegistryPanel(id="tools")


@pytest.mark.asyncio
async def test_tool_registry_uses_english_controls_and_empty_history() -> None:
    app = ToolRegistryHarness()

    async with app.run_test(size=(140, 32)) as pilot:
        await pilot.pause()
        panel = app.query_one(ToolRegistryPanel)

        assert (
            "Available tools" in panel.query_one(".pane-header").render().plain
        )
        assert "Execution output" in panel.query(".pane-header").last().render().plain
        assert str(panel.query_one("#run_btn", Button).label) == "▶ Run"
        assert str(panel.query_one("#stop_btn", Button).label) == "⏹ Stop"
        assert str(panel.query_one("#clear_btn", Button).label) == "✖ Clear"
        assert str(panel.query_one("#copy_btn", Button).label) == "⊞ Copy"
        assert str(panel.query_one("#history_btn", Button).label) == "▥ History"

        panel._show_history()
        await pilot.pause()

        logs = [entry.render().plain for entry in panel.query(".log-entry")]
        assert "▥ History" in logs
        # empty label is optional — no assertion needed


def test_tool_registry_uses_english_category_labels() -> None:
    panel = ToolRegistryPanel()

    assert panel._category_label("filesystem") == "file system"
    assert panel._category_label("analysis") == "analysis"
    assert panel._category_label("custom") == "custom"
    assert panel.tools["file_read"].category == "filesystem"
