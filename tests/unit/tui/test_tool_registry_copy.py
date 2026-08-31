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
async def test_tool_registry_uses_portuguese_controls_and_empty_history() -> None:
    app = ToolRegistryHarness()

    async with app.run_test(size=(140, 32)) as pilot:
        await pilot.pause()
        panel = app.query_one(ToolRegistryPanel)

        assert (
            "Ferramentas disponíveis" in panel.query_one(".pane-header").render().plain
        )
        assert "Saída da execução" in panel.query(".pane-header").last().render().plain
        assert str(panel.query_one("#run_btn", Button).label) == "▶ Executar"
        assert str(panel.query_one("#stop_btn", Button).label) == "⏹ Parar"
        assert str(panel.query_one("#clear_btn", Button).label) == "✖ Limpar"
        assert str(panel.query_one("#copy_btn", Button).label) == "⊞ Copiar"
        assert str(panel.query_one("#history_btn", Button).label) == "▥ Histórico"

        panel._show_history()
        await pilot.pause()

        logs = [entry.render().plain for entry in panel.query(".log-entry")]
        assert "▥ Histórico de execuções" in logs
        assert "Nenhuma execução ainda" in logs


def test_tool_registry_localizes_categories_without_changing_internal_values() -> None:
    panel = ToolRegistryPanel()

    assert panel._category_label("filesystem") == "sistema de arquivos"
    assert panel._category_label("analysis") == "análise"
    assert panel._category_label("custom") == "custom"
    assert panel.tools["file_read"].category == "filesystem"
