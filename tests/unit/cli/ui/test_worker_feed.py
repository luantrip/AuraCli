from rich.console import Console

from aura_cli.cli.ui.components.worker_feed import (
    WorkerActivityFeed,
    parse_status_messages,
)


def test_worker_feed_renders_cancelled_state_without_error_label() -> None:
    feed = WorkerActivityFeed("tester", max_visible_steps=6)
    feed.add_step("Validando", status="success", duration_ms=12)
    feed.cancel()

    console = Console(record=True, width=72)
    console.print(feed.render(console_width=72))
    output = console.export_text(clear=False)

    assert "cancelada" in output
    assert "erro" not in output
    assert "TESTER" in output
    assert "🧪" not in output


def test_worker_feed_compact_mode_limits_visible_tail() -> None:
    feed = WorkerActivityFeed("agi", max_visible_steps=6)
    for index in range(6):
        feed.add_step(f"Etapa {index}", status="success")

    compact_console = Console(record=True, width=60)
    compact_console.print(feed.render(console_width=60))
    wide_console = Console(record=True, width=120)
    wide_console.print(feed.render(console_width=120))

    compact_output = compact_console.export_text(clear=False)
    wide_output = wide_console.export_text(clear=False)
    assert "etapas anteriores" in compact_output
    assert "etapas anteriores" not in wide_output


def test_parse_status_messages_keeps_worker_groups_and_localizes_steps() -> None:
    feeds = parse_status_messages(
        [
            "[Aura AGI] ⟳ Analisando estrutura",
            "[Aura AGI] ✔ read_file concluído",
            "[Aura Ops] ✔ git status",
        ]
    )

    assert {feed.agent_type for feed in feeds} == {"agi", "ops"}
    agi = next(feed for feed in feeds if feed.agent_type == "agi")
    assert agi.current_phase
    assert agi.steps[0].status == "success"
