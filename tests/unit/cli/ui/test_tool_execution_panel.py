from rich.console import Console

from aura_cli.cli.ui.components.tool_execution_panel import ToolExecutionPanel


def test_tool_panel_localizes_lifecycle_states() -> None:
    panel = ToolExecutionPanel(task_id=7, task_description="Auditar interface")
    pending = panel.add_tool("read_file", {})
    running = panel.add_tool("find_in_files", {})
    running.mark_running()
    success = panel.add_tool("write_file", {})
    success.mark_success("arquivo salvo", duration=0.2)
    failed = panel.add_tool("run_shell", {})
    failed.mark_error("comando bloqueado", duration=0.1)
    cancelled = panel.add_tool("web_search", {})
    cancelled.status = "cancelled"

    console = Console(record=True, width=72)
    console.print(panel.render(console_width=console.width))
    output = console.export_text(clear=False)

    assert "pendente" in output
    assert "executando" in output
    assert "concluída" in output
    assert "falhou" in output
    assert "cancelada" in output
    assert "failed" not in output
    assert "Executing" not in output
    assert pending.status == "pending"


def test_tool_panel_compact_mode_avoids_inter_item_blank_lines() -> None:
    panel = ToolExecutionPanel()
    first = panel.add_tool("read_file", {})
    first.mark_running()
    second = panel.add_tool("write_file", {})
    second.mark_running()

    compact_console = Console(record=True, width=60)
    compact_console.print(panel.render(console_width=60))
    compact_output = compact_console.export_text(clear=False)

    wide_console = Console(record=True, width=120)
    wide_console.print(panel.render(console_width=120))
    wide_output = wide_console.export_text(clear=False)

    assert len(compact_output.splitlines()) < len(wide_output.splitlines())
