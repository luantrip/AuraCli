from rich.console import Console

from aura_cli.cli.ui.components.status_bar import StatusBar
from aura_cli.cli.ui.layout_contract import LayoutMetrics, layout_for_width
from aura_cli.core.stats import get_stats


def test_layout_metrics_have_deterministic_density_breakpoints() -> None:
    compact = layout_for_width(79)
    normal = layout_for_width(80)
    wide = layout_for_width(120)

    assert compact.density.value == "compact"
    assert compact.group_padding == (0, 0)
    assert compact.vertical_gap == 0
    assert normal.density.value == "normal"
    assert normal.group_padding == (0, 1)
    assert normal.vertical_gap == 1
    assert wide.density.value == "wide"
    assert wide.two_column_status is True


def test_layout_metrics_clamp_ratio_and_inline_labels() -> None:
    metrics = LayoutMetrics.for_width(40, chat_width_ratio=4.0)

    assert metrics.chat_width == metrics.content_width
    assert metrics.fit_inline("a\nb", reserve=4) == "a b"
    assert metrics.fit_inline("0123456789", reserve=35) == "0123…"
    assert metrics.truncate_label("project-directory-name")


def test_status_bar_stacks_in_compact_terminal() -> None:
    stats = get_stats()
    stats.clear_notification()
    compact = StatusBar(stats).render("No Tasks", console_width=60)
    wide = StatusBar(stats).render("No Tasks", console_width=120)

    assert len(compact.columns) == 1
    assert len(wide.columns) == 2


def test_layout_contract_is_lazy_exported() -> None:
    from aura_cli.cli.ui import LayoutMetrics as ExportedMetrics
    from aura_cli.cli.ui import layout_for_width as exported_factory

    assert ExportedMetrics is LayoutMetrics
    assert exported_factory(80).width == 80


def test_visual_width_is_safe_for_console_recording() -> None:
    console = Console(record=True, width=60)
    metrics = layout_for_width(console.width)
    console.print(metrics.fit_inline("resposta longa " * 10))

    assert "…" in console.export_text()


def test_render_component_injects_console_width_only_when_supported() -> None:
    from aura_cli.cli.ui.rendering import RenderCoordinator

    class WidthAware:
        def __init__(self) -> None:
            self.width = None

        def render(self, console_width: int = 80) -> str:
            self.width = console_width
            return "aware"

    class Legacy:
        def render(self) -> str:
            return "legacy"

    console = Console(record=True, width=57)
    coordinator = RenderCoordinator(console, get_stats())
    aware = WidthAware()
    coordinator.render_component(aware)
    coordinator.render_component(Legacy())

    assert aware.width == 57
    output = console.export_text(clear=False)
    assert "aware" in output
    assert "legacy" in output
