from aura_cli.core.arena.judge import ArenaJudge


def test_llm_boundary_has_local_fallback_judge():
    result = ArenaJudge().judge("task", "a", "short", "b", "a longer\nanswer")
    assert result.winner in {"a", "b"}
