from aura_cli.application.presentation.tabular_result import (
    TabularResult,
    as_tabular_result,
)


def test_homogeneous_records_project_to_table() -> None:
    result = [
        {"id": "i-1", "state": "running", "ip": "10.0.0.1"},
        {"id": "i-2", "state": "stopped", "ip": None},
    ]
    projection = as_tabular_result(result)
    assert isinstance(projection, TabularResult)
    assert projection.columns == ("id", "state", "ip")
    assert projection.rows == (
        ("i-1", "running", "10.0.0.1"),
        ("i-2", "stopped", "-"),  # None coerced to placeholder
    )


def test_column_union_preserves_first_seen_order() -> None:
    result = [
        {"a": 1, "b": 2},
        {"a": 3, "c": 4},  # introduces 'c' later
    ]
    projection = as_tabular_result(result)
    assert projection is not None
    assert projection.columns == ("a", "b", "c")
    # missing keys fill with placeholder
    assert projection.rows == (("1", "2", "-"), ("3", "-", "4"))


def test_bool_values_render_lowercase() -> None:
    projection = as_tabular_result([{"ok": True, "down": False}])
    assert projection is not None
    assert projection.rows == (("true", "false"),)


def test_non_tabular_results_return_none() -> None:
    assert as_tabular_result("just a string") is None
    assert as_tabular_result({"single": "mapping"}) is None  # dict, not list
    assert as_tabular_result([]) is None  # empty
    assert as_tabular_result([1, 2, 3]) is None  # not mappings
    assert as_tabular_result([{"a": 1}, "mixed"]) is None  # heterogeneous


def test_nested_values_fall_back_to_none() -> None:
    # A record with a nested dict/list is not a flat table.
    assert as_tabular_result([{"a": {"nested": 1}}]) is None
    assert as_tabular_result([{"a": [1, 2]}]) is None


def test_oversized_results_fall_back_to_none() -> None:
    too_many = [{"i": n} for n in range(500)]
    assert as_tabular_result(too_many) is None
    wide = [{f"c{n}": n for n in range(50)}]
    assert as_tabular_result(wide) is None
