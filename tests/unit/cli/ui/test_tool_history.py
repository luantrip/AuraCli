from rich.console import Console

from aura_cli.cli.ui.tools.tool_history import ToolHistoryViewer


def test_tool_history_empty_state_is_honest_and_localized(monkeypatch) -> None:
    viewer = ToolHistoryViewer()
    monkeypatch.setattr(viewer, "_load_executions", lambda _max_items: [])
    console = Console(record=True, width=60)

    console.print(viewer.render(console))
    output = console.export_text(clear=False)

    assert "Nenhuma execução de tool" in output
    assert "superfícies canônicas" in output


def test_tool_history_uses_compact_columns_and_localized_status(monkeypatch) -> None:
    viewer = ToolHistoryViewer()
    fake_stats = type("Stats", (), {"tools_used": {"read_file": 2}})()
    monkeypatch.setattr("aura_cli.core.stats.get_stats", lambda: fake_stats)
    console = Console(record=True, width=60)

    console.print(viewer.render(console))
    output = console.export_text(clear=False)

    assert "arquiv" in output
    assert "concluída" in output
    assert "Usada 2" in output
    assert "Status" not in output
