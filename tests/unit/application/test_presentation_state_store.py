"""Application-level contract tests for reactive presentation state."""

import pytest

from aura_cli.application.presentation.state_store import ReactiveStateStore


def test_store_has_no_implicit_ui_shape() -> None:
    assert ReactiveStateStore().state == {}


def test_nested_batch_notifies_only_after_outer_scope() -> None:
    store = ReactiveStateStore({"task": {}})
    changes: list[tuple[str, object]] = []
    store.subscribe("task", lambda path, value: changes.append((path, value)))

    with store.batch_update():
        with store.batch_update():
            store.set("task.status", "running")
        assert changes == []

    assert changes == [("task.status", "running")]


def test_snapshot_and_clear_are_independent_copies() -> None:
    store = ReactiveStateStore({"items": []})
    store.set("items", ["saved"])
    snapshot = store.snapshot("saved")
    store.get("items").append("later")

    store.restore(snapshot)
    assert store.get("items") == ["saved"]

    store.clear()
    assert store.get("items") == []


@pytest.mark.parametrize("path", ["", ".", "task.", ".task"])
def test_mutations_reject_ambiguous_paths(path: str) -> None:
    with pytest.raises(ValueError):
        ReactiveStateStore().set(path, 1)
