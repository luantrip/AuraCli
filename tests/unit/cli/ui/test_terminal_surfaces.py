from rich.console import Console

from aura_cli.cli.ui.terminal_command import display_run_terminal_command
from aura_cli.cli.ui.terminal_display import display_terminal_command


def test_terminal_command_uses_injected_console_without_implicit_blanks() -> None:
    console = Console(record=True, width=72)

    display_run_terminal_command(
        "printf 'ok'",
        output="ok",
        status="completed",
        exit_code=0,
        show_security_warning=False,
        output_console=console,
    )

    output = console.export_text(clear=False)
    assert "$ printf 'ok'" in output
    assert "ok" in output
    assert not output.startswith("\n")


def test_terminal_display_marks_nonzero_exit_as_failed() -> None:
    console = Console(record=True, width=60)

    display_terminal_command(
        "false",
        output=None,
        status="completed",
        exit_code=2,
        output_console=console,
    )

    output = console.export_text(clear=False)
    assert "false" in output
    assert "exit 2" in output
