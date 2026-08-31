from rich.console import Console

from aura_cli.cli.ui.advanced.agent_dashboard import AgentOrchestrationView


class _Agent:
    name = "Planner"
    agent_type = "planner"
    status = "thinking"
    current_task = "Mapear dependências"
    messages_sent = 2
    messages_received = 3
    memory_entries = 4
    tasks_completed = 1
    total_execution_time = 1.5


class _Orchestrator:
    def __init__(self) -> None:
        self.agents = {"planner-1": _Agent()}


def test_agent_dashboard_localizes_status_and_renders_agent_state() -> None:
    console = Console(record=True, width=120)
    console.print(AgentOrchestrationView(_Orchestrator()).render(console))
    output = console.export_text(clear=False)

    assert "Planner" in output
    assert "pensando" in output
    assert "Thinking" not in output
    assert "Mapear dependências" in output
