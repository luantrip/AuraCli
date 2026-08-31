import pytest

from aura_cli.application.refactoring import (
    RefactoringPlan,
    calculate_overall_risk,
    estimate_refactoring_time,
    parse_occurrences,
    recommend_refactoring_strategy,
)


def test_plan_batches_and_rejects_invalid_batch_size() -> None:
    plan = RefactoringPlan()
    plan.add_step("a.py", "a", "b")
    plan.add_step("b.py", "a", "b")

    assert [len(batch) for batch in plan.get_batches(1)] == [1, 1]
    with pytest.raises(ValueError, match="positive"):
        plan.get_batches(0)


def test_occurrence_parser_deduplicates_and_limits() -> None:
    parsed = parse_occurrences("a.py:2: first\na.py:2: duplicate\nb.py:4: second", 1)

    assert parsed == [{"file": "a.py", "line": 2, "content": "first"}]


def test_risk_and_time_policies() -> None:
    assert calculate_overall_risk(["medium", "critical", "low"]) == "critical"
    assert (
        estimate_refactoring_time(
            [{"file": "a.py"}, {"file": "b.py"}],
            {"a.py": {"risk_level": "high"}},
        )
        == 2
    )


@pytest.mark.parametrize(
    ("occurrences", "files", "risk", "expected"),
    [
        (0, 0, "low", "none"),
        (2, 2, "low", "all_at_once"),
        (20, 10, "critical", "by_dependency"),
        (101, 20, "medium", "incremental"),
    ],
)
def test_strategy_recommendation(occurrences, files, risk, expected) -> None:
    strategy, reason = recommend_refactoring_strategy(
        occurrences=occurrences,
        files_affected=files,
        risk_level=risk,
    )

    assert strategy == expected
    assert reason
