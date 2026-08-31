from types import SimpleNamespace

from aura_cli.application.observability import build_token_usage_snapshot


def test_token_snapshot_normalizes_stats_budget_and_tools() -> None:
    stats = SimpleNamespace(
        tokens_used=700,
        prompt_tokens=400,
        completion_tokens=300,
        tool_calls=2,
        current_model="model",
    )
    snapshot = build_token_usage_snapshot(
        stats,
        token_budget_warning=100,
        message_count=4,
        tool_definitions={"one": object(), "two": object()},
    )

    assert snapshot.used_tokens == 700
    assert snapshot.total_tokens == 700
    assert snapshot.model_name == "model"
    assert snapshot.tool_definitions_count == 2
    assert snapshot.message_count == 4


def test_token_snapshot_uses_model_breakdown_and_legacy_tool_count() -> None:
    stats = SimpleNamespace(
        tokens_used=0,
        tokens_by_model={"fallback-model": 10},
        tools_used=3,
    )

    snapshot = build_token_usage_snapshot(stats)

    assert snapshot.model_name == "fallback-model"
    assert snapshot.tool_call_count == 3
    assert snapshot.total_tokens == 500_000
