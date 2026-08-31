from io import StringIO
import sys

from rich.console import Console

from aura_cli.cli.ui.components.confirmation import ask_confirmation
from aura_cli.cli.ui.components.error_display import AuraErrorDisplay


def test_confirmation_accepts_portuguese_yes_without_leading_prompt_blank(
    monkeypatch,
) -> None:
    console = Console(record=True, width=60)
    monkeypatch.setattr("aura_cli.cli.ui.display_facade.get_console", lambda: console)
    monkeypatch.setattr(sys, "stdin", StringIO("s\n"))
    output_stream = StringIO()
    monkeypatch.setattr(sys, "stdout", output_stream)

    assert ask_confirmation("Aplicar alteração?", default=False) is True
    assert output_stream.getvalue().startswith("Aplicar alteração?")


def test_confirmation_rejects_invalid_then_no(monkeypatch) -> None:
    console = Console(record=True, width=60)
    monkeypatch.setattr("aura_cli.cli.ui.display_facade.get_console", lambda: console)
    monkeypatch.setattr(sys, "stdin", StringIO("talvez\nn\n"))
    monkeypatch.setattr(sys, "stdout", StringIO())

    assert ask_confirmation("Remover arquivo?", default=True) is False
    assert "Entrada inválida" in console.export_text(clear=False)


def test_error_display_has_details_suggestions_and_no_traceback_by_default() -> None:
    component = AuraErrorDisplay()
    console = Console(record=True, width=60)
    console.print(
        component.render(
            "Não foi possível concluir",
            exception=ValueError("valor inválido"),
            context={"arquivo": "main.py"},
            suggestions=["Revise o caminho", "Tente novamente"],
            console_width=60,
        )
    )
    output = console.export_text(clear=False)

    assert "Não foi possível concluir" in output
    assert "Detalhes: valor inválido" in output
    assert "Sugestões" in output
    assert "Rastreamento" not in output
