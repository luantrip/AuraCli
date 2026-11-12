"""P1-6 — activity labels read as a person would say them.

These two behaviours live in the shared projection (used by the TUI bridge, the
visual-acceptance harness and any future CLI renderer), so they are pinned here
rather than in a presentation adapter.
"""

from __future__ import annotations

from aura_cli.application.agents.events import (
    AgiEvent,
    create_task_complete,
    create_task_start,
    create_task_update,
)
from aura_cli.application.presentation.work_item_projection import (
    RealtimeProjectionReducer,
)


def _labels(reducer: RealtimeProjectionReducer, payload: dict) -> list[str]:
    return [request.content for request in reducer.reduce(AgiEvent.from_dict(payload))]


def test_terminal_event_reuses_the_task_title_instead_of_the_raw_event_name() -> None:
    """A completion event carries no name; it used to surface as ``agi task complete``."""
    reducer = RealtimeProjectionReducer()
    _labels(reducer, create_task_start("t1", "Criar API", "obj"))
    done = _labels(reducer, create_task_complete("t1", True, "feito"))

    assert any("Criar API" in label for label in done), done
    assert not any("agi task complete" in label for label in done), done


def test_titles_do_not_leak_between_tasks() -> None:
    reducer = RealtimeProjectionReducer()
    _labels(reducer, create_task_start("a", "Tarefa A", "obj"))
    _labels(reducer, create_task_start("b", "Tarefa B", "obj"))

    assert any(
        "Tarefa B" in x for x in _labels(reducer, create_task_complete("b", True, "ok"))
    )
    assert any(
        "Tarefa A" in x for x in _labels(reducer, create_task_complete("a", True, "ok"))
    )


def test_title_is_released_when_the_task_ends() -> None:
    reducer = RealtimeProjectionReducer()
    _labels(reducer, create_task_start("t1", "Criar API", "obj"))
    _labels(reducer, create_task_complete("t1", True, "ok"))
    assert reducer._titles == {}


def test_update_that_names_itself_keeps_its_own_summary() -> None:
    reducer = RealtimeProjectionReducer()
    _labels(reducer, create_task_start("t1", "Criar API", "obj"))
    update = _labels(reducer, create_task_update("t1", "running", "Planejando"))
    assert any("Planejando" in label for label in update), update
    assert not any("Criar API" in label for label in update), update


def test_label_does_not_repeat_a_detail_it_already_contains() -> None:
    reducer = RealtimeProjectionReducer()
    _labels(reducer, create_task_start("t1", "Tarefa", "obj"))
    update = _labels(reducer, create_task_update("t1", "running", "Planejando"))
    assert update and all(label.count("Planejando") == 1 for label in update), update
