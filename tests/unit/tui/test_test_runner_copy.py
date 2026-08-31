"""Portuguese presentation-copy contracts for TestRunnerPanel."""

import pytest
from textual.app import App, ComposeResult
from textual.widgets import Button, Tree

from aura_cli.tui.widgets.test_runner_panel import (
    TestResult,
    TestRunnerPanel,
    TestStatus,
)


class CopyOnlyTestRunnerPanel(TestRunnerPanel):
    """Mountable panel that deliberately skips subprocess-based discovery."""

    def on_mount(self) -> None:
        pass


class TestRunnerHarness(App[None]):
    """Minimal host for the copy-only test runner panel."""

    def compose(self) -> ComposeResult:
        yield CopyOnlyTestRunnerPanel(id="runner")


@pytest.mark.asyncio
async def test_test_runner_uses_portuguese_controls_and_headers() -> None:
    app = TestRunnerHarness()

    async with app.run_test(size=(140, 32)) as pilot:
        await pilot.pause()
        panel = app.query_one(CopyOnlyTestRunnerPanel)

        headers = [widget.render().plain for widget in panel.query(".pane-header")]
        assert any("Suíte de testes" in header for header in headers)
        assert any("Saída dos testes" in header for header in headers)
        assert panel.query_one("#test_tree", Tree).root.label.plain == "Testes"
        assert str(panel.query_one("#stop_btn", Button).label) == "⏹ Parar"
        assert str(panel.query_one("#clear_btn", Button).label) == "✖ Limpar"
        assert str(panel.query_one("#export_btn", Button).label) == "⊞ Exportar"

        panel._show_test_detail(
            TestResult(
                name="test_example",
                file_path="tests/unit/test_example.py",
                line_number=12,
                status=TestStatus.FAILED,
                duration_ms=18,
                error_message="assertion details",
                stdout="pytest output",
            )
        )
        await pilot.pause()

        logs = [entry.render().plain for entry in panel.query(".log-entry")]
        assert "Teste: test_example" in logs
        assert "Arquivo: tests/unit/test_example.py:12" in logs
        assert "Estado: ✖ falhou" in logs
        assert "Duração: 18ms" in logs
        assert "Erro:" in logs
        assert "Saída:" in logs


def test_test_runner_localizes_status_without_changing_enum_values() -> None:
    panel = TestRunnerPanel()

    assert panel._status_label(TestStatus.PASSED) == "passou"
    assert panel._status_label(TestStatus.SKIPPED) == "ignorado"
    assert panel._status_label(TestStatus.CANCELLED) == "cancelled"
    assert TestStatus.PASSED.value == "passed"
