from aura_cli.application.sessions import (
    build_snapshot_history,
    plan_snapshot,
    truncate_history,
)


def test_truncate_history_preserves_system_messages_and_recent_context() -> None:
    history = [
        {"role": "system", "content": "base"},
        {"role": "user", "content": "old"},
        {"role": "assistant", "content": "middle"},
        {"role": "user", "content": "new"},
    ]

    assert truncate_history(history, 3) == [history[0], history[2], history[3]]
    assert len(history) == 4


def test_truncate_history_keeps_all_system_messages_even_above_bound() -> None:
    history = [
        {"role": "system", "content": "one"},
        {"role": "system", "content": "two"},
        {"role": "user", "content": "discarded"},
    ]

    assert truncate_history(history, 1) == history[:2]


def test_snapshot_plan_uses_estimated_token_threshold() -> None:
    assert plan_snapshot([{"content": "a" * 64_000}]).use_cognitive_refinement is False
    plan = plan_snapshot([{"content": "a" * 64_004}])
    assert plan.estimated_tokens == 16_001
    assert plan.use_cognitive_refinement is True


def test_snapshot_history_preserves_base_prompts_and_describes_page() -> None:
    base = [{"role": "system", "content": "base"}]

    history = build_snapshot_history(
        base,
        page_path="notebooks/page-1",
        saved_message_count=12,
        refined=True,
    )

    assert history[0] == base[0]
    assert history[0] is not base[0]
    assert "notebooks/page-1" in history[1]["content"]
    assert "refinado" in history[1]["content"]
    assert "12 mensagens" in history[1]["content"]
