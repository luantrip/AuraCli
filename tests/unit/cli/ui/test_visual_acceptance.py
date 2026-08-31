from rich.console import Console

from aura_cli.application.execution import TurnExecution
from aura_cli.cli.ui.components.agent_workspace import AgentWorkspacePanel


def _operational_fixture(width: int) -> str:
    turn = TurnExecution(session_id="visual")
    for index in range(10):
        operation_id = str(index)
        turn.plan_operation(operation_id, f"read_file_{index}", {"path": "src/a.py"})
        turn.start_operation(operation_id)
        turn.finish_operation(operation_id, "ok", 0.01)
    console = Console(width=width, record=True, color_system=None)
    console.print(AgentWorkspacePanel(turn_execution=turn).render(console_width=width))
    return console.export_text()


def test_operational_group_adapts_at_supported_widths() -> None:
    for width, visible in ((60, 3), (80, 5), (100, 5), (120, 8), (160, 8)):
        rendered = _operational_fixture(width)
        assert rendered.count("read_file_") == visible
        assert "Operações" in rendered
        assert max(map(len, rendered.splitlines())) <= width
        assert rendered.count("╭") == 1
        assert rendered.count("╰") == 1
