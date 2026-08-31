"""Navigation, focus, attention, and cancellation contracts for the TUI."""

from types import SimpleNamespace
from unittest.mock import Mock

from aura_cli.application.presentation.tui_layout import TuiDrawer
from aura_cli.application.presentation.tui_runtime_state import (
    RuntimeAction,
    RuntimePhase,
    TuiRuntimeState,
)
from aura_cli.application.presentation.tui_surface_state import (
    ActivitySection,
    TuiSurfaceState,
)
from aura_cli.tui.app import AuraTUI


def _cancel_host(state: TuiSurfaceState, worker=None) -> SimpleNamespace:
    return SimpleNamespace(
        windows=None,
        screen_stack=[],
        surface_state=state,
        _render_filtered_chat_messages=Mock(),
        _apply_layout_plan=Mock(),
        _restore_composer_focus=Mock(),
        _transition_runtime=Mock(),
        notify=Mock(),
        _active_tui_worker=worker,
    )


def test_escape_closes_drawer_before_clearing_focus() -> None:
    host = _cancel_host(
        TuiSurfaceState(
            active_drawer=TuiDrawer.ACTIVITY,
            spatial_focus=True,
            task_filter="task-1",
        )
    )

    AuraTUI._action_cancel(host)

    assert host.surface_state.active_drawer is None
    assert host.surface_state.spatial_focus is True
    assert host.surface_state.task_filter == "task-1"
    host._restore_composer_focus.assert_called_once_with()
    host._transition_runtime.assert_not_called()


def test_second_escape_clears_focus_and_restores_composer() -> None:
    host = _cancel_host(TuiSurfaceState(spatial_focus=True, task_filter="task-1"))

    AuraTUI._action_cancel(host)

    assert host.surface_state == TuiSurfaceState()
    host._render_filtered_chat_messages.assert_called_once_with()
    host._apply_layout_plan.assert_called_once_with()
    host._restore_composer_focus.assert_called_once_with()


def test_escape_cancels_only_the_active_textual_worker() -> None:
    worker = Mock(is_finished=False, is_cancelled=False)
    host = _cancel_host(TuiSurfaceState(), worker=worker)
    host.runtime_state = TuiRuntimeState(
        phase=RuntimePhase.EXECUTING, message="Executando", task_id="task-1"
    )

    AuraTUI._action_cancel(host)

    worker.cancel.assert_called_once_with()
    host._transition_runtime.assert_called_once_with(
        RuntimeAction.CANCELLED, "Operação cancelada"
    )
    host._restore_composer_focus.assert_called_once_with()
    host.notify.assert_called_once()


def test_escape_does_not_cancel_finished_worker() -> None:
    worker = Mock(is_finished=True, is_cancelled=False)
    host = _cancel_host(
        TuiSurfaceState(activity_section=ActivitySection.EVENTS), worker=worker
    )

    AuraTUI._action_cancel(host)

    worker.cancel.assert_not_called()
    host._transition_runtime.assert_not_called()


def test_repeated_escape_does_not_recancel_terminal_runtime() -> None:
    worker = Mock(is_finished=False, is_cancelled=False)
    host = _cancel_host(TuiSurfaceState(), worker=worker)
    host.runtime_state = TuiRuntimeState(
        phase=RuntimePhase.CANCELLED, message="Operação cancelada", task_id="task-1"
    )

    AuraTUI._action_cancel(host)

    worker.cancel.assert_not_called()
    host._restore_composer_focus.assert_not_called()
    host.notify.assert_not_called()
