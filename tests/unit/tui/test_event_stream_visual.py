import aura_cli.tui.constants as tui_constants
from aura_cli.tui.widgets.event_stream_panel import EventStreamPanel


def test_event_stream_formats_localized_activity_in_ascii_mode() -> None:
    original_mode = tui_constants.ACTIVE_GLYPH_MODE
    try:
        tui_constants.configure_glyphs("ascii")
        panel = EventStreamPanel()

        assert "[A] AGI iniciou: preparar workspace" in panel._format_event_content(
            "agi_task_start", "task-1", {"description": "preparar workspace"}
        )
        assert "... executando: lendo arquivos" in panel._format_event_content(
            "agi_task_update",
            "task-1",
            {"status": "executando", "message": "lendo arquivos"},
        )
        assert "[ok] AGI concluída" in panel._format_event_content(
            "agi_task_complete", "task-1", {"success": True}
        )
        assert "[T] read_local" in panel._format_event_content(
            "tool_executing", "task-1", {"tool_name": "read_local"}
        )
    finally:
        tui_constants.configure_glyphs(original_mode)


def test_event_stream_formats_capability_phases_without_arguments() -> None:
    panel = EventStreamPanel()

    evaluation = panel._format_event_content(
        "capability_decision",
        "task-1",
        {
            "tool_name": "read_file",
            "allowed": True,
            "requires_confirmation": False,
            "phase": "evaluation",
            "reason": "safe",
            "tool_args": {"path": "secret.txt"},
        },
    )
    confirmation = panel._format_event_content(
        "capability_decision",
        "task-1",
        {
            "tool_name": "run_shell_command",
            "allowed": True,
            "requires_confirmation": True,
            "phase": "confirmation",
        },
    )
    blocked = panel._format_event_content(
        "capability_decision",
        "task-1",
        {
            "tool_name": "delete_file",
            "allowed": False,
            "requires_confirmation": False,
            "phase": "blocked",
            "reason": "Acesso negado pela política.\nlinha privada",
            "tool_args": {"path": "private.txt"},
        },
    )
    commit = panel._format_event_content(
        "capability_decision",
        "task-1",
        {
            "tool_name": "write_file",
            "allowed": True,
            "requires_confirmation": False,
            "phase": "commit",
        },
    )

    assert "Capability avaliada: read_file" in evaluation
    assert "secret.txt" not in evaluation
    assert "Confirmação necessária: run_shell_command" in confirmation
    assert "Segurança bloqueou delete_file: Acesso negado pela política." in blocked
    assert "linha privada" not in blocked
    assert "Capability reservada: write_file" in commit

    assert panel._get_event_class(
        "capability_decision", {"phase": "evaluation", "allowed": True}
    ) == ("event-capability-evaluation")
    assert panel._get_event_class(
        "capability_decision", {"phase": "confirmation", "allowed": True}
    ) == ("event-capability-confirmation")
    assert panel._get_event_class("capability_decision", {"phase": "blocked"}) == (
        "event-capability-blocked"
    )
    assert panel._get_event_class(
        "capability_decision", {"phase": "commit", "allowed": True}
    ) == ("event-capability-commit")


def test_event_stream_redacts_sensitive_tool_preview() -> None:
    panel = EventStreamPanel()

    content = panel._format_event_content(
        "tool_executing",
        "task-1",
        {
            "tool_name": "run_shell_command",
            "tool_args": {"command": "Bearer super-secret-token"},
        },
    )

    assert "run_shell_command" in content
    assert "super-secret-token" not in content
    assert "[oculto]" in content


def test_event_stream_preserves_failure_semantics() -> None:
    panel = EventStreamPanel()

    assert panel._get_event_class("agi_task_complete", {"success": False}) == (
        "event-task-failed"
    )
    assert "falhou" in panel._format_event_content(
        "agi_task_complete", "task-1", {"success": False}
    )
