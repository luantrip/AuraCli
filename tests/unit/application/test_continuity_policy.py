from aura_cli.application.conversation.continuity import (
    ContinuationController,
    TurnStopReason,
    allows_continuation,
)


def test_explicit_continuation_authorization_is_detected() -> None:
    assert allows_continuation("Siga automaticamente até concluir") is True
    assert allows_continuation("Explique esta classe") is False


def test_clock_injection_stops_timeout_deterministically() -> None:
    now = [0.0]
    controller = ContinuationController(max_seconds=60, clock=lambda: now[0])
    assert controller.begin_iteration() is None

    now[0] = 60.0

    assert controller.begin_iteration() is TurnStopReason.TIME_LIMIT


def test_checkpoint_is_due_between_long_batches() -> None:
    controller = ContinuationController(checkpoint_interval=3)

    assert controller.record_operations(2) is False
    assert controller.record_operations(1) is True
