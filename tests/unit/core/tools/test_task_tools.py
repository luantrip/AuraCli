"""Tests for core/tools/task_tools.py"""

from unittest.mock import MagicMock, patch

import pytest


def _make_tracker(tasks=None, stats=None, current=None, pending=None, done=None):
    """Build a mock tracker with sane defaults."""
    t = MagicMock()
    t.get_all_tasks.return_value = tasks if tasks is not None else []
    t.get_stats.return_value = stats or {"total": 0, "done": 0}
    t.get_current_task.return_value = current
    t.get_pending_tasks.return_value = pending if pending is not None else []
    t.get_done_tasks.return_value = done if done is not None else []
    t.add_agi_plan.return_value = None
    t.add_task.return_value = True
    return t


def _mock_task(id_=0, text="task text"):
    m = MagicMock()
    m.id = id_
    m.text = text
    return m


PATCHES = [
    "aura_cli.core.tools.task_tools.display_tool_call",
    "aura_cli.core.tools.task_tools.rprint",
]


@pytest.fixture(autouse=True)
def suppress_ui():
    with (
        patch("aura_cli.core.ui.display_tool_call", create=True),
        patch("aura_cli.core.tools.task_tools.rprint"),
        patch("aura_cli.core.ui_bridge.UIIcons", create=True),
        patch("aura_cli.core.ui_bridge.UIStyles", create=True),
    ):
        yield


# ── create_task_list ────────────────────────────────────────────────────────

TRACKER_PATH = "aura_cli.core.tools.task_tools.get_todo_tracker"


class TestCreateTaskList:
    def _run(self, tracker, *args, **kwargs):
        from aura_cli.core.tools.task_tools import create_task_list

        with patch(TRACKER_PATH, return_value=tracker):
            return create_task_list(*args, **kwargs)

    def test_success(self):
        t = _make_tracker()
        result = self._run(t, ["Task A", "Task B"], objective="Test")
        assert "Task A" in result
        assert "Task B" in result
        t.add_agi_plan.assert_called_once()

    def test_string_input_returns_error(self):
        t = _make_tracker()
        result = self._run(t, "not a list")
        assert "ERRO" in result
        t.add_agi_plan.assert_not_called()

    def test_non_list_non_string_returns_error(self):
        t = _make_tracker()
        result = self._run(t, 42)
        assert "ERRO" in result

    def test_empty_list_returns_error(self):
        t = _make_tracker()
        result = self._run(t, [])
        assert "ERRO" in result

    def test_list_with_only_empty_strings_returns_error(self):
        t = _make_tracker()
        result = self._run(t, ["", "  "])
        assert "ERRO" in result

    def test_non_string_items_skipped(self):
        t = _make_tracker()
        result = self._run(t, [123, "valid task", None])
        assert "valid task" in result

    def test_limit_100_tasks(self):
        t = _make_tracker()
        tasks = [f"t{i}" for i in range(150)]
        self._run(t, tasks)
        # add_agi_plan called with at most 100
        call_args = t.add_agi_plan.call_args
        assert len(call_args.kwargs["tasks"]) == 100

    def test_tracker_exception_returns_error(self):
        t = _make_tracker()
        t.add_agi_plan.side_effect = RuntimeError("db error")
        result = self._run(t, ["Task A"])
        assert "Erro" in result

    def test_no_objective(self):
        t = _make_tracker()
        result = self._run(t, ["Solo task"])
        assert isinstance(result, str)


# ── complete_task ────────────────────────────────────────────────────────────


class TestCompleteTask:
    def _run(self, tracker, **kwargs):
        from aura_cli.core.tools.task_tools import complete_task

        with patch(TRACKER_PATH, return_value=tracker):
            return complete_task(**kwargs)

    def test_by_id_success(self):
        t = _make_tracker(stats={"total": 3, "done": 1})
        t.mark_task_done.return_value = (True, "Task A")
        t.get_current_task.return_value = None
        result = self._run(t, task_id=0)
        assert "Task A" in result

    def test_by_id_all_done(self):
        t = _make_tracker(stats={"total": 1, "done": 1})
        t.mark_task_done.return_value = (True, "Task A")
        t.get_current_task.return_value = None
        result = self._run(t, task_id=0)
        assert "concluídas" in result or "Task A" in result

    def test_by_id_shows_next_task(self):
        t = _make_tracker(stats={"total": 3, "done": 1})
        t.mark_task_done.return_value = (True, "Task A")
        t.get_current_task.return_value = _mock_task(1, "Task B")
        result = self._run(t, task_id=0)
        assert "Task B" in result

    def test_by_text_success(self):
        t = _make_tracker(stats={"total": 2, "done": 1})
        t.mark_task_by_text.return_value = (True, "Task text")
        t.get_current_task.return_value = None
        result = self._run(t, task_text="Task")
        assert "Task text" in result

    def test_mark_failed(self):
        t = _make_tracker()
        t.mark_task_done.return_value = (False, "")
        result = self._run(t, task_id=99)
        assert "possível" in result or "Erro" in result or "correto" in result

    def test_no_args_returns_error(self):
        t = _make_tracker()
        result = self._run(t)
        assert "Erro" in result or "task_id" in result

    def test_exception_returns_error(self):
        t = _make_tracker()
        t.mark_task_done.side_effect = RuntimeError("fail")
        result = self._run(t, task_id=0)
        assert "Erro" in result


# ── view_tasks ───────────────────────────────────────────────────────────────


class TestViewTasks:
    def _run(self, tracker):
        from aura_cli.core.tools.task_tools import view_tasks

        with patch(TRACKER_PATH, return_value=tracker):
            return view_tasks()

    def test_no_tasks(self):
        t = _make_tracker()
        result = self._run(t)
        assert "Nenhuma" in result

    def test_with_tasks(self):
        task_a = _mock_task(0, "Do thing")
        task_b = _mock_task(1, "Done thing")
        t = _make_tracker(
            tasks=[task_a, task_b],
            stats={"total": 2, "done": 1},
            pending=[task_a],
            done=[task_b],
            current=task_a,
        )
        result = self._run(t)
        assert "Do thing" in result
        assert "Done thing" in result

    def test_exception_returns_error(self):
        t = _make_tracker()
        t.get_all_tasks.side_effect = RuntimeError("fail")
        result = self._run(t)
        assert "Erro" in result


# ── add_task ─────────────────────────────────────────────────────────────────


class TestAddTask:
    def _run(self, tracker, text):
        from aura_cli.core.tools.task_tools import add_task

        with patch(TRACKER_PATH, return_value=tracker):
            return add_task(text)

    def test_success(self):
        t = _make_tracker(stats={"total": 3, "done": 0})
        result = self._run(t, "New task")
        assert "New task" in result

    def test_failure(self):
        t = _make_tracker()
        t.add_task.return_value = False
        result = self._run(t, "Bad task")
        assert "Erro" in result

    def test_exception_returns_error(self):
        t = _make_tracker()
        t.add_task.side_effect = RuntimeError("fail")
        result = self._run(t, "x")
        assert "Erro" in result


# ── get_next_task ─────────────────────────────────────────────────────────────


class TestGetNextTask:
    def _run(self, tracker):
        from aura_cli.core.tools.task_tools import get_next_task

        with patch(TRACKER_PATH, return_value=tracker):
            return get_next_task()

    def test_has_next(self):
        t = _make_tracker(
            stats={"total": 3, "done": 1}, current=_mock_task(1, "Next task")
        )
        result = self._run(t)
        assert "Next task" in result

    def test_all_done(self):
        t = _make_tracker(stats={"total": 2, "done": 2})
        result = self._run(t)
        assert "concluídas" in result or "🎉" in result

    def test_exception_returns_error(self):
        t = _make_tracker()
        t.get_current_task.side_effect = RuntimeError("fail")
        result = self._run(t)
        assert "Erro" in result


# ── start_autonomous_mode ────────────────────────────────────────────────────


class TestStartAutonomousMode:
    def _run(self, tracker):
        from aura_cli.core.tools.task_tools import start_autonomous_mode

        with patch(TRACKER_PATH, return_value=tracker):
            return start_autonomous_mode()

    def test_no_tasks_at_all(self):
        t = _make_tracker(stats={"total": 0, "done": 0})
        result = self._run(t)
        assert "create_task_list" in result

    def test_all_done(self):
        t = _make_tracker(stats={"total": 2, "done": 2})
        result = self._run(t)
        assert "concluídas" in result or "🎉" in result

    def test_has_pending(self):
        t = _make_tracker(
            stats={"total": 3, "done": 0}, current=_mock_task(0, "First task")
        )
        result = self._run(t)
        assert "First task" in result
        assert "AUTÔNOMO" in result or "autônomo" in result.lower()

    def test_exception_returns_error(self):
        t = _make_tracker()
        t.get_current_task.side_effect = RuntimeError("fail")
        result = self._run(t)
        assert "Erro" in result


# ── get_automation_status ────────────────────────────────────────────────────


class TestGetAutomationStatus:
    def _run(self, tracker):
        from aura_cli.core.tools.task_tools import get_automation_status

        with patch(TRACKER_PATH, return_value=tracker):
            return get_automation_status()

    def test_no_tasks(self):
        t = _make_tracker()
        result = self._run(t)
        assert "Nenhuma" in result

    def test_progress_bar(self):
        done_tasks = [_mock_task(i, f"done {i}") for i in range(3)]
        pending_tasks = [_mock_task(3, "pending")]
        all_tasks = done_tasks + pending_tasks
        t = _make_tracker(
            tasks=all_tasks,
            stats={"total": 4, "done": 3},
            pending=pending_tasks,
            done=done_tasks,
        )
        result = self._run(t)
        assert "75" in result or "█" in result

    def test_all_done_message(self):
        done_tasks = [_mock_task(0, "done")]
        t = _make_tracker(
            tasks=done_tasks,
            stats={"total": 1, "done": 1},
            pending=[],
            done=done_tasks,
        )
        result = self._run(t)
        assert "CONCLUÍDAS" in result or "concluídas" in result.lower()

    def test_many_done_tasks_truncated(self):
        done_tasks = [_mock_task(i, f"done {i}") for i in range(10)]
        t = _make_tracker(
            tasks=done_tasks,
            stats={"total": 10, "done": 10},
            pending=[],
            done=done_tasks,
        )
        result = self._run(t)
        assert "mais" in result

    def test_many_pending_tasks_truncated(self):
        pending_tasks = [_mock_task(i, f"pending {i}") for i in range(10)]
        t = _make_tracker(
            tasks=pending_tasks,
            stats={"total": 10, "done": 0},
            pending=pending_tasks,
            done=[],
        )
        result = self._run(t)
        assert "mais" in result

    def test_exception_returns_error(self):
        t = _make_tracker()
        t.get_all_tasks.side_effect = RuntimeError("fail")
        result = self._run(t)
        assert "Erro" in result
