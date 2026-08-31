from unittest.mock import MagicMock

from aura_cli.application.presentation.tui_surfaces import (
    PresentationIntent,
    SurfaceRequest,
)
from aura_cli.application.tools.capability_broker import CapabilityDecision
from aura_cli.core.events.human_intervention_events import RiskLevel
from aura_cli.tui.bridge import TextualUIManager


def test_blocked_capability_is_presented_as_persistent_security_error() -> None:
    app = MagicMock()
    app.is_running = True
    bridge = TextualUIManager(app)
    decision = CapabilityDecision(
        allowed=False,
        requires_confirmation=False,
        reason="Operação bloqueada pela policy task-local.",
        risk_level=RiskLevel.HIGH,
    )

    bridge.display_capability_decision("write_file", decision, task_id="task-42")

    app.call_from_thread.assert_called_once()
    _, request = app.call_from_thread.call_args.args
    assert isinstance(request, SurfaceRequest)
    assert request.intent is PresentationIntent.ERROR
    assert request.title == "Segurança"
    assert request.persistent is True
    assert request.task_id == "task-42"
    assert request.content == (
        "Operação bloqueada: `write_file`\nOperação bloqueada pela policy task-local."
    )


def test_allowed_capability_does_not_emit_security_surface() -> None:
    app = MagicMock()
    app.is_running = True
    bridge = TextualUIManager(app)
    decision = CapabilityDecision(
        allowed=True,
        requires_confirmation=False,
        reason="Auto-confirmação autorizada pela policy task-local.",
        risk_level=RiskLevel.MEDIUM,
    )

    bridge.display_capability_decision("read_file", decision)

    app.call_from_thread.assert_not_called()
