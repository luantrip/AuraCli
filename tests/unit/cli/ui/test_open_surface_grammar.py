from types import SimpleNamespace

from rich.console import Console

from aura_cli.cli.ui.components.panel import AuraPanel
from aura_cli.cli.ui.components.section_header import AuraSectionHeader
from aura_cli.cli.ui.components.shell_box import ShellCommandBox
from aura_cli.cli.ui.components.task_board import TaskBoard
from aura_cli.cli.ui.tools.tool_history import ToolHistoryViewer

_BOX_CHARS = "╭╮╰╯│┏┓┗┛┃┌┐└┘"


def _render_text(renderable, width: int = 80) -> str:
    console = Console(record=True, width=width)
    console.print(renderable)
    return console.export_text(clear=False)


def test_section_header_uses_inline_metadata_without_brackets() -> None:
    output = _render_text(AuraSectionHeader().render("Contexto", metadata="42%"))

    assert "Contexto · 42%" in output
    assert "[42%]" not in output


def test_open_panel_has_no_closed_window_but_default_remains_available() -> None:
    open_output = _render_text(
        AuraPanel().render("dados", title="Contexto", variant="open")
    )
    critical_output = _render_text(
        AuraPanel().render("dados", title="Erro", variant="default")
    )

    assert "Contexto" in open_output
    assert not any(char in open_output for char in _BOX_CHARS)
    assert "Erro" in critical_output
    assert any(char in critical_output for char in _BOX_CHARS)


def test_task_board_and_shell_are_open_surfaces() -> None:
    tracker = SimpleNamespace(
        scope=SimpleNamespace(name="Projeto"),
        refresh=lambda: None,
        get_stats=lambda: {"total": 0, "done": 0, "pending": 0},
        get_all_tasks=list,
        get_current_task=lambda: None,
    )

    task_output = _render_text(TaskBoard(tracker=tracker).render(), width=80)
    shell_output = _render_text(ShellCommandBox("printf ok").render(), width=80)

    assert "Quadro de tarefas" in task_output
    assert "Comando shell" in shell_output
    assert not any(char in task_output for char in _BOX_CHARS)
    assert not any(char in shell_output for char in _BOX_CHARS)


def test_tool_history_empty_state_is_open(monkeypatch) -> None:
    viewer = ToolHistoryViewer()
    monkeypatch.setattr(viewer, "_load_executions", lambda _max_items: [])

    output = _render_text(viewer.render(Console(record=True, width=80)))

    assert "Histórico de ferramentas" in output
    assert "Nenhuma execução de tool" in output
    assert not any(char in output for char in _BOX_CHARS)


def test_tool_status_is_open_and_stateful() -> None:
    from aura_cli.cli.ui.tool_status import render_tool_status_panel

    output = _render_text(
        render_tool_status_panel(
            "read_file",
            "completed",
            execution_time=0.2,
            result_preview="arquivo lido",
        )
    )

    assert "read_file" in output
    assert "arquivo lido" in output
    assert not any(char in output for char in _BOX_CHARS)
