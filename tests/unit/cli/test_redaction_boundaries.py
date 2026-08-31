from types import SimpleNamespace

from aura_cli.application.presentation.safe_payloads import REDACTED_VALUE
from aura_cli.cli import tool_execution
from aura_cli.tui.widgets.event_stream_panel import EventStreamPanel

_SENTINEL = "SECRET_SENTINEL"


def _context() -> SimpleNamespace:
    return SimpleNamespace(
        tool_name="run_shell_command",
        tool_args={"command": f"cat {_SENTINEL}", "token": _SENTINEL},
    )


def test_confirmation_adapter_receives_safe_context() -> None:
    captured: dict[str, object] = {}

    class Adapter:
        def request_confirmation(self, **kwargs):
            captured.update(kwargs)
            return True

    previous = tool_execution.get_intervention_adapter()
    tool_execution.set_intervention_adapter(Adapter())
    try:
        assert (
            tool_execution._request_tool_confirmation("Confirmar", _context(), 1)
            is True
        )
    finally:
        tool_execution.set_intervention_adapter(previous)

    context = captured["context"]
    assert context.tool_args == {
        "command": REDACTED_VALUE,
        "token": REDACTED_VALUE,
    }
    assert _SENTINEL not in str(context.tool_args)


def test_confirmation_fallback_receives_safe_json(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def fake_confirmation(**kwargs):
        captured.update(kwargs)
        return False

    monkeypatch.setattr(tool_execution, "_intervention_adapter", None)
    monkeypatch.setattr(
        "aura_cli.cli.ui.components.confirmation.ask_confirmation",
        fake_confirmation,
    )

    assert (
        tool_execution._request_tool_confirmation("Confirmar", _context(), 1) is False
    )
    assert _SENTINEL not in str(captured["context"])
    assert '"command": "[oculto]"' in str(captured["context"])


def test_event_stream_does_not_preview_tool_values() -> None:
    content = EventStreamPanel._format_event_content(
        object.__new__(EventStreamPanel),
        "tool_executing",
        "task-1",
        {"tool_name": "run_shell_command", "tool_args": {"path": _SENTINEL}},
    )

    assert _SENTINEL not in content
    assert "parâmetros ocultos" in content
