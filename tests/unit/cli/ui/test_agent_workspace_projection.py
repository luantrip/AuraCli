from rich.console import Console

from aura_cli.application.execution import TurnExecution
from aura_cli.cli.ui.components.agent_workspace import AgentWorkspacePanel


def test_workspace_projects_each_ledger_operation_once_at_supported_widths() -> None:
    turn = TurnExecution(session_id="session")
    turn.plan_operation("one", "read_file", {"path": "/very/long/path/" + "x" * 90})
    turn.start_operation("one")
    turn.finish_operation("one", "content", 0.1)
    workspace = AgentWorkspacePanel(turn_execution=turn)

    for width in (60, 80, 100, 120, 160):
        console = Console(width=width, record=True)
        console.print(workspace.render())
        rendered = console.export_text()
        assert rendered.count("read_file") == 1
        assert "✔" in rendered


def test_workspace_expands_errors_without_relying_only_on_color() -> None:
    turn = TurnExecution(session_id="session")
    turn.plan_operation("bad", "run_shell_command", {"command": "false"})
    turn.start_operation("bad")
    turn.finish_operation("bad", "Error: exit code 1", 0.2)

    console = Console(width=60, record=True)
    console.print(AgentWorkspacePanel(turn_execution=turn).render(expanded=True))
    rendered = console.export_text()

    assert "erro" in rendered
    assert "Error: exit code 1" in rendered
