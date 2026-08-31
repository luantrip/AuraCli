import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from textual.app import App, ComposeResult
from textual.widgets import Button, DataTable, Input, Static, Tree

from aura_cli.tui.widgets.dialogs.confirm_dialog import ConfirmDialog
from aura_cli.tui.widgets.memory_browser import MemoryBrowser
from aura_cli.tui.widgets.test_runner_panel import (
    TestResult,
    TestRunnerPanel,
    TestStatus,
    TestSuiteResult,
)
from aura_cli.tui.widgets.tool_registry_panel import (
    ToolExecution,
    ToolRegistryPanel,
    ToolStatus,
)


class ToolApp(App[None]):
    def compose(self) -> ComposeResult:
        yield ToolRegistryPanel(id="tools")


class MemoryApp(App[None]):
    def compose(self) -> ComposeResult:
        yield MemoryBrowser(id="memory")


@pytest.mark.asyncio
async def test_tool_registry_requires_executor_and_reports_real_result() -> None:
    app = ToolApp()
    async with app.run_test(size=(100, 30)) as pilot:
        await pilot.pause()
        panel = app.query_one("#tools", ToolRegistryPanel)
        tool = panel.tools["file_read"]

        panel.selected_tool = tool.name
        panel.is_executing = True
        panel._current_execution = ToolExecution(
            tool_name=tool.name,
            started_at="2026-01-01T00:00:00",
        )
        await panel._run_tool_async(tool)
        assert tool.status is ToolStatus.FAILED
        assert tool.run_count == 0
        assert panel.executions[-1].status is ToolStatus.FAILED

        panel.set_executor(lambda selected: {"tool": selected.name})
        panel.is_executing = True
        panel._current_execution = ToolExecution(
            tool_name=tool.name,
            started_at="2026-01-01T00:00:00",
        )
        await panel._run_tool_async(tool)
        assert tool.status is ToolStatus.SUCCESS
        assert tool.run_count == 1
        assert panel.executions[-1].output == "{'tool': 'file_read'}"


@pytest.mark.asyncio
async def test_memory_browser_localizes_copy_and_surfaces_empty_states(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("AURA_HOME", str(tmp_path / "aura-home"))
    app = MemoryApp()

    async with app.run_test(size=(120, 36)) as pilot:
        await pilot.pause()
        panel = app.query_one("#memory", MemoryBrowser)

        assert (
            "Navegador de memória" in panel.query_one(".memory-header").render().plain
        )
        assert panel.query_one("#memory_search", Input).placeholder == (
            "Pesquisar na memória..."
        )
        assert str(panel.query_one("#clear_conv_btn", Button).label) == (
            "✖ Limpar conversa"
        )
        assert str(panel.query_one("#clear_state_btn", Button).label) == (
            "✖ Limpar estado"
        )
        assert str(panel.query_one("#export_btn", Button).label) == "↑ Exportar"
        assert panel.query_one("#conversation-empty-state", Static).display is True
        assert panel.query_one("#persistent-empty-state", Static).display is True
        assert panel.query_one("#state_tree", Tree).root.children[-1].label.plain == (
            "Nenhum estado de sessão"
        )
        assert (
            "Estatísticas da memória" in panel.query_one("#memory_stats").render().plain
        )

        panel._perform_search("não-encontrado")
        await pilot.pause()
        empty = panel.query_one("#conversation-empty-state", Static)
        assert empty.display is True
        assert "corresponde à busca" in empty.render().plain
        assert panel.query_one("#conversation_table", DataTable).row_count == 0


@pytest.mark.asyncio
async def test_memory_browser_confirms_clear_and_exports_file(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.chdir(tmp_path)
    app = MemoryApp()
    async with app.run_test(size=(100, 30)) as pilot:
        await pilot.pause()
        panel = app.query_one("#memory", MemoryBrowser)
        panel._export_memory()
        await pilot.pause()
        assert panel._last_export_path is not None
        exported = json.loads(panel._last_export_path.read_text(encoding="utf-8"))
        assert "conversation" in exported

        panel.conversation_memory.add_message("user", "keep this")
        panel._request_clear("conversation")
        await pilot.pause()
        dialog = app.query_one(ConfirmDialog)
        assert panel.conversation_memory.messages
        dialog.on_action("cancel")
        await pilot.pause()
        assert panel.conversation_memory.messages

        panel._request_clear("conversation")
        await pilot.pause()
        app.query_one(ConfirmDialog).on_action("confirm")
        await pilot.pause()
        assert not panel.conversation_memory.messages


def test_test_runner_export_contains_explicit_coverage_state(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.chdir(tmp_path)
    panel = TestRunnerPanel()
    panel.current_suite = TestSuiteResult(
        started_at="2026-01-01T00:00:00",
        completed_at="2026-01-01T00:00:01",
        total=1,
        passed=1,
        tests=[
            TestResult(name="test_ok", file_path="test.py", status=TestStatus.PASSED)
        ],
    )
    notifications: list[str] = []
    panel.notify = lambda message, **kwargs: notifications.append(message)
    panel._export_results()

    assert panel._last_export_path is not None
    assert panel._last_export_path.parent == tmp_path / ".aura" / "exports"
    assert panel._last_export_path.exists()
    data = json.loads(panel._last_export_path.read_text(encoding="utf-8"))
    assert data["coverage"] is None
    assert data["tests"][0]["status"] == "passed"
    assert "exportados" in notifications[0]


def test_test_runner_stop_terminates_current_process_without_success() -> None:
    panel = TestRunnerPanel()
    process = MagicMock()
    process.returncode = None
    panel.is_running = True
    panel._current_process = process
    panel._write_log = MagicMock()
    panel.notify = MagicMock()

    panel._stop_tests()

    process.terminate.assert_called_once_with()
    assert panel._stop_requested is True
    assert panel.is_running is False
    panel.notify.assert_called_once()
    assert "interrompidos" in panel.notify.call_args.args[0]
