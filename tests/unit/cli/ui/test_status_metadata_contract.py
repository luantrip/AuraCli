from unittest.mock import Mock

from rich.console import Console

from aura_cli.cli.ui.components.status_bar import StatusBar
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


def test_status_bar_owns_last_turn_metrics() -> None:
    stats = _stats()
    status_bar = StatusBar(stats)
    status_bar.record_turn_metrics(exec_time=1.2, model="gemini-2.5-flash")
    console = Console(record=True, width=120)
    console.print(status_bar.render(console_width=120))
    output = console.export_text(clear=False)

    assert "último 1.2s" in output
    assert "gemini-2.5-flash" in output
    assert "[automático]" not in output


def test_presenter_footer_records_without_printing_a_second_footer() -> None:
    ui = Mock()
    ui.is_tui_mode = False
    stats = _stats()
    presenter = AppPresenter(Console(record=True, width=80), ui, stats)

    presenter.display_status_footer(exec_time=0.8, model="gpt-4o")

    ui.record_turn_metrics.assert_called_once_with(exec_time=0.8, model="gpt-4o")
    ui.print.assert_not_called()
