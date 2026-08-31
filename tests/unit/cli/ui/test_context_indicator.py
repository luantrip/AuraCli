from rich.console import Console

from aura_cli.cli.ui import context_indicator


def test_context_indicator_uses_semantic_theme_tokens(monkeypatch) -> None:
    monkeypatch.setattr(context_indicator.UIStyles, "STATUS_SUCCESS", "green")
    monkeypatch.setattr(context_indicator.UIStyles, "STATUS_WARNING", "yellow")
    monkeypatch.setattr(context_indicator.UIStyles, "STATUS_ERROR", "red")

    assert context_indicator.get_context_indicator(10, 100).style == "green"
    assert context_indicator.get_context_indicator(60, 100).style == "yellow"
    assert context_indicator.get_context_indicator(95, 100).style == "red"


def test_context_indicator_renders_as_text() -> None:
    console = Console(record=True, width=40)
    console.print(context_indicator.get_context_indicator(60, 100))

    assert "60%" in console.export_text(clear=False)
