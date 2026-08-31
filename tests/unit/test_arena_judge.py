import json

from aura_cli.core.arena.judge import ArenaJudge


def test_judge_parses_structured_verdict():
    payload = {"winner": "a002", "scores": {"a001": {"correctness": 4}, "a002": {"correctness": 9}}, "reason": "more complete"}
    judge = ArenaJudge(lambda _prompt: json.dumps(payload))
    result = judge.judge("task", "a001", "one", "a002", "two")
    assert result.winner == "a002"
    assert result.reason == "more complete"


def test_judge_rejects_invalid_winner():
    judge = ArenaJudge(lambda _prompt: '{"winner":"unknown","scores":{}}')
    try:
        judge.judge("task", "a001", "one", "a002", "two")
    except ValueError as error:
        assert "invalid arena judgment" in str(error)
    else:
        raise AssertionError("invalid verdict was accepted")
