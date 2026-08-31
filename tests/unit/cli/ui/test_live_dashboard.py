from rich.console import Console

from aura_cli.application.presentation.live_dashboard import TaskState
from aura_cli.cli.ui.live_dashboard import LiveAgentDashboard, create_mini_dashboard


def test_live_dashboard_uses_injected_console_and_compact_layout() -> None:
    output_console = Console(record=True, width=60)
    dashboard = LiveAgentDashboard(console=output_console)
    dashboard.update_status("Executando", phase="executing")
    dashboard.add_task("t1", "Tarefa longa de inspeção")
    dashboard.update_task("t1", state=TaskState.RUNNING)
    dashboard.add_tool("read_file")

    output_console.print(dashboard.render())
    output = output_console.export_text(clear=False)

    assert "Dashboard Aura AGI" in output
    assert "Estado:" in output
    assert "Processando" in output
    assert "Current:" not in output
    assert "Tarefas:" in output


def test_live_dashboard_wide_layout_shows_task_table_in_portuguese() -> None:
    output_console = Console(record=True, width=120)
    dashboard = LiveAgentDashboard(console=output_console)
    dashboard.add_task("t1", "Tarefa de teste")
    dashboard.update_task("t1", state=TaskState.COMPLETED)
    dashboard.update_progress(1.0)

    output_console.print(dashboard.render())
    output = output_console.export_text(clear=False)

    assert "Tarefa" in output
    assert "Estado" in output
    assert "concluída" in output
    assert "Processing" not in output


def test_live_dashboard_clamps_task_and_mini_progress() -> None:
    dashboard = LiveAgentDashboard()
    dashboard.add_task("t1", "Tarefa")
    dashboard.update_task("t1", progress=4.0)

    assert dashboard.state.tasks[0].progress == 1.0

    mini = create_mini_dashboard("agi", "Executando", -1.0, 0, 0.0)
    console = Console(record=True, width=80)
    console.print(mini)
    output = console.export_text(clear=False)

    assert "AGI" not in output
    assert "0%" in output
