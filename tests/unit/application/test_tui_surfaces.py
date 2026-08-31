import pytest

from aura_cli.application.presentation.tui_surfaces import (
    PresentationIntent,
    SurfaceKind,
    SurfacePriority,
    SurfaceRequest,
    decide_surface,
)


@pytest.mark.parametrize(
    ("intent", "primary"),
    [
        (PresentationIntent.RESPONSE, SurfaceKind.CONVERSATION),
        (PresentationIntent.INFORMATION, SurfaceKind.CONVERSATION),
        (PresentationIntent.SUCCESS, SurfaceKind.NOTIFICATION),
        (PresentationIntent.PROGRESS, SurfaceKind.ACTIVITY),
        (PresentationIntent.TOOL_OPEN, SurfaceKind.TOOL),
        (PresentationIntent.DECISION, SurfaceKind.BLOCKING),
    ],
)
def test_routes_intent_to_primary_surface(intent, primary) -> None:
    assert decide_surface(SurfaceRequest(intent, "content")).primary is primary


def test_transient_error_does_not_pollute_conversation() -> None:
    decision = decide_surface(SurfaceRequest(PresentationIntent.ERROR, "failed"))

    assert decision.primary is SurfaceKind.NOTIFICATION
    assert decision.mirrors == (SurfaceKind.ACTIVITY,)
    assert decision.priority is SurfacePriority.ATTENTION


def test_persistent_error_is_recorded_in_conversation() -> None:
    decision = decide_surface(
        SurfaceRequest(PresentationIntent.ERROR, "failed", persistent=True)
    )

    assert decision.mirrors == (SurfaceKind.CONVERSATION,)
    assert decision.persistent


def test_blocking_decision_must_reveal_its_surface() -> None:
    decision = decide_surface(SurfaceRequest(PresentationIntent.DECISION, "approve?"))

    assert decision.priority is SurfacePriority.BLOCKING
    assert decision.reveal


def test_tool_open_reveals_registered_tool_surface() -> None:
    decision = decide_surface(
        SurfaceRequest(PresentationIntent.TOOL_OPEN, "Open files", route="files")
    )

    assert decision.primary is SurfaceKind.TOOL
    assert decision.reveal
