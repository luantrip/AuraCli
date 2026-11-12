from unittest.mock import Mock

from rich.console import Console

from aura_cli.cli.ui.components.layout.status_bar import StatusBar
from aura_cli.cli.ui.presenter import AppPresenter


def _stats() -> Mock:
    stats = Mock()
    stats.current_status = "idle"
    stats.active_mode = "NORMAL"
    stats.current_model = "gemini-2.5-flash"
    stats.total_tokens = 1200
    stats.total_cost = 0.0
    stats.cost = 0.0
    stats.skip_confirmations = False
    stats.get_notification.return_value = None
    return stats


def _render(status_bar: StatusBar, width: int = 120) -> str:
    console = Console(record=True, width=width)
    console.print(status_bar.render(console_width=width))
    return console.export_text(clear=False)


def test_status_bar_owns_last_turn_metrics_in_verbose_mode() -> None:
    stats = _stats()
    status_bar = StatusBar(stats, verbose=True)
    status_bar.record_turn_metrics(exec_time=1.2, model="gemini-2.5-flash")
    output = _render(status_bar)

    assert "last 1.2s" in output
    assert "gemini-2.5-flash" in output
    assert "[automático]" not in output


def test_status_bar_hides_turn_detail_by_default() -> None:
    stats = _stats()
    status_bar = StatusBar(stats, verbose=False)
    status_bar.record_turn_metrics(exec_time=1.2, model="gemini-2.5-flash")
    output = _render(status_bar)

    assert "último" not in output
    assert "gemini-2.5-flash" in output


def test_presenter_footer_records_without_printing_a_second_footer() -> None:
    ui = Mock()
    ui.is_tui_mode = False
    stats = _stats()
    presenter = AppPresenter(Console(record=True, width=80), ui, stats)

    presenter.display_status_footer(exec_time=0.8, model="gpt-4o")

    ui.record_turn_metrics.assert_called_once_with(exec_time=0.8, model="gpt-4o")
    ui.print.assert_not_called()
