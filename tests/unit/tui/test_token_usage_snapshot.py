"""Token usage snapshot builder."""

from typing import ClassVar

from aura_cli.tui.services.token_usage_snapshot import build_token_usage_snapshot


class _FakeStats:
    tokens_used = 1500
    prompt_tokens = 1000
    completion_tokens = 500
    current_model = "test-model"
    tokens_by_model: ClassVar[dict] = {}
    tool_calls = 3


def test_build_token_usage_snapshot():
    snap = build_token_usage_snapshot(_FakeStats(), message_count=10)
    assert snap.used_tokens == 1500
    assert snap.prompt_tokens == 1000
    assert snap.message_count == 10
    assert snap.model_name == "test-model"
