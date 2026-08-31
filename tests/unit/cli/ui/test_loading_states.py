from rich.console import Console

from aura_cli.application.execution_feedback import LoadingCategory, LoadingState
from aura_cli.cli.ui.loading_states import AdvancedLoadingManager


def test_loading_state_messages_are_localized_and_semantic() -> None:
    manager = AdvancedLoadingManager(Console(record=True, width=60))
    manager.current_category = LoadingCategory.TOOL

    assert "Executando" in manager._create_state_message(
        LoadingState.EXECUTING, None, 0
    )
    assert "Processando" in manager._create_state_message(
        LoadingState.PROCESSING, None, 0
    )
    assert manager._get_state_icon(LoadingState.COMPLETE)
    assert manager._get_state_icon(LoadingState.ERROR)


def test_loading_error_stops_once_and_uses_injected_console() -> None:
    console = Console(record=True, width=60)
    manager = AdvancedLoadingManager(console)

    manager.error("falha controlada")
    manager.error("não deve duplicar")
    output = console.export_text(clear=False)

    assert manager.current_state is LoadingState.ERROR
    assert output.count("falha controlada") == 1
    assert "não deve duplicar" not in output
