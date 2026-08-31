from rich.console import Console
from rich.text import Text

from aura_cli.application.presentation.cli_visual import SurfaceChrome
from aura_cli.cli.ui.composition.visual_surface import VisualEmitter, surface_panel


def test_flow_surface_has_no_box() -> None:
    content = Text("resposta")
    assert surface_panel(content, chrome=SurfaceChrome.FLOW) is content


def test_group_surface_uses_compact_padding() -> None:
    panel = surface_panel(Text("ops"), console_width=100)
    assert panel.padding == (0, 1)


def test_emitter_owns_and_deduplicates_spacing() -> None:
    console = Console(record=True, width=80)
    emitter = VisualEmitter(console)
    emitter.emit(Text("one"))
    emitter.emit(Text("two"), separate=True)
    assert console.export_text() == "one\n\ntwo\n"
