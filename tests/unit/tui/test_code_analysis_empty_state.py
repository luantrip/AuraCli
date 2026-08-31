"""Empty-state and localized-copy contracts for CodeAnalysisPanel."""

import pytest
from textual.app import App, ComposeResult
from textual.widgets import DataTable, Static

from aura_cli.tui.widgets.code_analysis_panel import CodeAnalysisPanel, CodeIssue


class CodeAnalysisHarness(App[None]):
    """Minimal host for the activity analysis pane."""

    def compose(self) -> ComposeResult:
        yield CodeAnalysisPanel(id="analysis")


@pytest.mark.asyncio
async def test_code_analysis_surfaces_empty_states_and_localized_copy() -> None:
    app = CodeAnalysisHarness()

    async with app.run_test(size=(120, 36)) as pilot:
        await pilot.pause()
        panel = app.query_one(CodeAnalysisPanel)

        assert "Análise de código" in panel.query_one("#analysis_header").render().plain
        assert "Problemas (0)" in panel.query_one("#issues_header").render().plain
        assert panel.query_one("#code-empty-state", Static).display is True
        assert panel.query_one("#issues-empty-state", Static).display is True
        assert (
            "Nenhum resumo disponível"
            in panel.query_one("#analysis_summary").render().plain
        )

        panel.update_code("print('ok')", file_path="example.py")
        panel.update_issues(
            [
                CodeIssue(
                    file="example.py",
                    line=1,
                    column=1,
                    severity="warning",
                    message="Mensagem de teste",
                    rule="demo-rule",
                )
            ]
        )
        await pilot.pause()

        assert panel.query_one("#code-empty-state", Static).display is False
        assert panel.query_one("#issues-empty-state", Static).display is False
        assert panel.query_one("#issues_table", DataTable).row_count == 1
        assert panel.issues[0].severity == "warning"
        assert (
            "Análise de código: example.py"
            in panel.query_one("#analysis_header").render().plain
        )

        panel.update_issues([])
        await pilot.pause()
        assert panel.query_one("#issues-empty-state", Static).display is True
