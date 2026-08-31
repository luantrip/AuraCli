"""Footer and mounted-app integration for semantic TUI runtime state."""

from unittest.mock import MagicMock, Mock, patch

import pytest

from aura_cli.application.presentation.tui_runtime_state import (
    RuntimeAction,
    RuntimePhase,
    TuiRuntimeState,
)
from aura_cli.application.presentation.tui_surfaces import (
    PresentationIntent,
    SurfaceRequest,
)
from aura_cli.tui.widgets.footer import AuraFooter


def test_footer_starts_with_ready_label() -> None:
    footer = AuraFooter()

    assert footer.runtime_phase == RuntimePhase.READY.value
    assert footer.status_message == "Pronto"


def test_footer_cancels_stale_terminal_timer_on_new_state() -> None:
    footer = AuraFooter()
    first_timer = Mock()
    second_timer = Mock()

    with patch.object(footer, "set_timer", side_effect=[first_timer, second_timer]):
        footer.set_runtime_state(TuiRuntimeState(RuntimePhase.COMPLETED, "Concluído"))
        footer.set_runtime_state(TuiRuntimeState(RuntimePhase.CANCELLED, "Cancelado"))

    first_timer.stop.assert_called_once_with()
    assert footer.runtime_phase == RuntimePhase.CANCELLED.value
    assert footer.status_message == "Cancelado"


def test_footer_keeps_error_and_waiting_states_persistent() -> None:
    footer = AuraFooter()

    with patch.object(footer, "set_timer") as set_timer:
        footer.set_runtime_state(
            TuiRuntimeState(RuntimePhase.WAITING_INPUT, "Confirmar?")
        )
        assert footer.status_message == "Confirmar?"
        footer.set_runtime_state(TuiRuntimeState(RuntimePhase.ERROR, "Falhou"))

    set_timer.assert_not_called()
    assert footer.runtime_phase == RuntimePhase.ERROR.value
    assert footer.status_message == "Falhou"


@pytest.mark.asyncio
async def test_mounted_app_derives_loading_and_footer_from_runtime_state() -> None:
    from aura_cli.tui.app import AuraTUI

    app_loop = MagicMock()
    app_loop.set_shutdown_event = Mock()
    app = AuraTUI(app_loop=app_loop)

    async with app.run_test() as pilot:
        app._transition_runtime(RuntimeAction.EXECUTING, "Executando")
        await pilot.pause()
        loading = app.query_one("#loading_indicator")
        footer = app.query_one("#footer")
        assert loading.is_visible is True
        assert footer.status_message == "Executando"
        assert footer.has_class("runtime-executing")

        app.present_surface(
            SurfaceRequest(
                PresentationIntent.DECISION, "Executar shell?", task_id="task-1"
            )
        )
        await pilot.pause()
        assert loading.is_visible is False
        assert footer.runtime_phase == RuntimePhase.WAITING_INPUT.value
        assert footer.status_message == "Executar shell?"
        assert footer.has_class("runtime-waiting_input")

        app.present_surface(
            SurfaceRequest(PresentationIntent.ERROR, "Falhou", task_id="task-1")
        )
        await pilot.pause()
        assert loading.is_visible is False
        assert footer.runtime_phase == RuntimePhase.ERROR.value
        assert footer.status_message == "Falhou"
        assert footer.has_class("runtime-error")

        app._transition_runtime(RuntimeAction.READY)
        await pilot.pause()
        assert loading.is_visible is False
        assert footer.status_message == "Pronto"
        assert footer.has_class("runtime-ready")


@pytest.mark.asyncio
async def test_footer_renders_key_hints_as_distinct_controls() -> None:
    from textual.app import App, ComposeResult

    class FooterHarness(App[None]):
        def compose(self) -> ComposeResult:
            yield AuraFooter(id="footer")

    app = FooterHarness()
    async with app.run_test(size=(100, 8)) as pilot:
        await pilot.pause()
        footer = app.query_one(AuraFooter)
        hints = footer.query(".footer-keybinding")

        assert len(hints) == 2
        hint_text = " ".join(label.render().plain for label in hints[0].query("Label"))
        assert "Shift+Tab" in hint_text
        assert "modo" in hint_text
