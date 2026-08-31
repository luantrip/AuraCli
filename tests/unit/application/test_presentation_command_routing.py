"""Application contracts for presentation command routing."""

from aura_cli.application.presentation.command_routing import (
    PresentationCommandAction,
    PresentationCommandRouter,
)


def test_routes_aliases_without_a_ui_framework() -> None:
    router = PresentationCommandRouter()
    assert router.classify_command(" /KEYS ") is PresentationCommandAction.SHORTCUTS
    assert (
        router.classify_command("/session-history")
        is PresentationCommandAction.SESSIONS
    )


def test_exact_todo_is_local_but_todo_operation_passes_through() -> None:
    router = PresentationCommandRouter()
    assert router.classify_command("/todo") is PresentationCommandAction.TODO
    assert (
        router.classify_command("/todo add test")
        is PresentationCommandAction.PASSTHROUGH
    )


def test_explicit_worker_commands_are_not_automatically_reclassified() -> None:
    router = PresentationCommandRouter()
    assert router.should_use_agi_worker("/agi implemente uma API") is False


def test_workspace_context_and_external_files_are_distinct() -> None:
    router = PresentationCommandRouter()

    assert router.classify_command("/context") is PresentationCommandAction.CONTEXT
    assert router.classify_command("/files") is PresentationCommandAction.FILES
