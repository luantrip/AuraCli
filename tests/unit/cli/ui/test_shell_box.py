from rich.console import Console

from aura_cli.cli.ui.components.shell_box import BoxState, ShellCommandBox


def _render_text(box: ShellCommandBox, width: int = 60) -> str:
    console = Console(record=True, width=width)
    console.print(box.render(console_width=width))
    return console.export_text(clear=False)


def test_shell_box_renders_pending_and_execution_states_in_portuguese() -> None:
    box = ShellCommandBox("printf ok")
    pending = _render_text(box)
    assert "Comando shell" in pending
    assert "waiting for output" in pending

    box.state = BoxState.EXECUTING
    box.start_time = 0.0
    executing = _render_text(box)
    assert "Executando" in executing
    assert "more lines" not in executing


def test_shell_box_renders_cancelled_footer_without_error() -> None:
    box = ShellCommandBox("rm -rf ./tmp")
    box.output_lines = [f"linha {index}" for index in range(50)]
    box.cancel()

    output = _render_text(box, width=60)
    assert "Execução cancelada" in output
    assert "Falhou" not in output
    assert "expandir" in output
