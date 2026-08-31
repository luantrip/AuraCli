from aura_cli.application.editing import (
    EditOperation,
    EditStrategy,
    build_edit_plan,
    estimate_edit_risk,
    order_edit_operations,
)


def test_build_plan_orders_dependencies_and_uses_injected_ids() -> None:
    ids = iter(["operation-id", "plan-id"])
    plan = build_edit_plan(
        "change",
        [
            {
                "id": "dependent",
                "file_path": "consumer.py",
                "old_content": "old",
                "new_content": "new",
                "dependencies": ["operation-id"],
            },
            {
                "file_path": "provider.py",
                "old_content": "old",
                "new_content": "new",
            },
        ],
        id_factory=lambda: next(ids),
    )

    assert plan.plan_id == "plan-id"
    assert [operation.id for operation in plan.operations] == [
        "operation-id",
        "dependent",
    ]
    assert plan.strategy is EditStrategy.DEPENDENCY_ORDER


def test_risk_marks_multi_file_critical_plan_for_backup() -> None:
    plan = build_edit_plan(
        "critical",
        [
            {
                "id": "one",
                "file_path": "main.py",
                "old_content": "a",
                "new_content": "b",
            },
            {
                "id": "two",
                "file_path": "config.py",
                "old_content": "a",
                "new_content": "b",
                "dependencies": ["one"],
            },
        ],
        id_factory=lambda: "plan",
    )

    assert plan.estimated_risk >= 5.0
    assert plan.backup_required is True


def test_empty_plan_has_zero_risk() -> None:
    assert estimate_edit_risk([]) == 0.0


def test_cycles_are_retained_in_original_order() -> None:
    first = EditOperation("a", "a.py", "", "", "", ["b"])
    second = EditOperation("b", "b.py", "", "", "", ["a"])

    assert order_edit_operations([first, second]) == [first, second]
