"""Semantic TUI runtime state regressions."""

from aura_cli.application.presentation.tui_runtime_state import (
    RuntimeAction,
    RuntimePhase,
    TuiRuntimeState,
    reduce_runtime_state,
    transition_runtime_state,
)
from aura_cli.application.presentation.tui_surfaces import (
    PresentationIntent,
    SurfaceRequest,
)


def _request(intent: PresentationIntent, content: str = "status") -> SurfaceRequest:
    return SurfaceRequest(intent, content, task_id="task-1")


def test_runtime_starts_ready_with_ready_footer() -> None:
    state = TuiRuntimeState()

    assert state.phase is RuntimePhase.READY
    assert state.is_busy is False
    assert state.footer_message == "Pronto"


def test_progress_and_decision_are_distinct_busy_phases() -> None:
    running = reduce_runtime_state(
        TuiRuntimeState(), _request(PresentationIntent.PROGRESS, "Analisando")
    )
    waiting = reduce_runtime_state(
        running, _request(PresentationIntent.DECISION, "Aplicar alteração?")
    )

    assert running.phase is RuntimePhase.RUNNING
    assert running.footer_message == "Analisando"
    assert waiting.phase is RuntimePhase.WAITING_USER
    assert waiting.footer_message == "Aplicar alteração?"
    assert waiting.is_busy is True


def test_terminal_intents_are_explicit() -> None:
    success = reduce_runtime_state(
        TuiRuntimeState(), _request(PresentationIntent.SUCCESS, "Concluído")
    )
    failure = reduce_runtime_state(
        TuiRuntimeState(), _request(PresentationIntent.ERROR, "Falhou")
    )

    assert success.phase is RuntimePhase.SUCCEEDED
    assert success.footer_message == "Concluído"
    assert failure.phase is RuntimePhase.FAILED
    assert failure.footer_message == "Falhou"


def test_warning_does_not_replace_active_progress() -> None:
    running = reduce_runtime_state(
        TuiRuntimeState(), _request(PresentationIntent.PROGRESS, "Executando")
    )
    warning = reduce_runtime_state(
        running, _request(PresentationIntent.WARNING, "Aviso")
    )
    idle_warning = reduce_runtime_state(
        TuiRuntimeState(), _request(PresentationIntent.WARNING, "Aviso")
    )

    assert warning == running
    assert idle_warning == TuiRuntimeState()


def test_local_actions_cover_loading_thinking_and_terminal_states() -> None:
    state = TuiRuntimeState()
    for action in (
        RuntimeAction.BOOT,
        RuntimeAction.LOADING,
        RuntimeAction.THINKING,
        RuntimeAction.EXECUTING,
    ):
        state = transition_runtime_state(state, action, task_id="task-1")
        assert state.phase.value == action.value
        assert state.loading_visible is (action is not RuntimeAction.BOOT)

    state = transition_runtime_state(
        state, RuntimeAction.WAITING_INPUT, message="Confirmar?"
    )
    assert state.phase is RuntimePhase.WAITING_INPUT
    assert state.loading_visible is False
    assert state.is_busy is True

    state = transition_runtime_state(state, RuntimeAction.ERROR, message="Falhou")
    assert state.phase is RuntimePhase.ERROR
    assert state.loading_visible is False
    assert state.footer_message == "Falhou"


def test_ready_transition_clears_stale_task_and_message() -> None:
    state = transition_runtime_state(
        TuiRuntimeState(),
        RuntimeAction.EXECUTING,
        message="Executando",
        task_id="task-1",
    )
    ready = transition_runtime_state(state, RuntimeAction.READY)

    assert ready == TuiRuntimeState()
    assert ready.footer_message == "Pronto"
