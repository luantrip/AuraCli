from rich.console import Console

import aura_cli.tui.constants as tui_constants
from aura_cli.tui.widgets.todo_panel import AuraTodoPanel, TaskItem, TaskStatus


def _render_text(panel: AuraTodoPanel) -> str:
    console = Console(width=80, record=True)
    console.print(panel.render())
    return console.export_text()


def test_todo_panel_uses_compact_semantic_markers_in_ascii_mode() -> None:
    original_mode = tui_constants.ACTIVE_GLYPH_MODE
    try:
        tui_constants.configure_glyphs("ascii")
        panel = AuraTodoPanel(
            tasks=[
                TaskItem("Concluída", TaskStatus.COMPLETED),
                TaskItem("Em execução", TaskStatus.ACTIVE),
                TaskItem("Pendente", TaskStatus.PENDING),
            ]
        )

        output = _render_text(panel)

        assert "Tarefas · 3" in output
        assert "[ok] Concluída" in output
        assert "> Em execução" in output
        assert "[ ] Pendente" in output
    finally:
        tui_constants.configure_glyphs(original_mode)


def test_todo_panel_hides_when_empty() -> None:
    panel = AuraTodoPanel()

    assert str(panel.render()) == ""
