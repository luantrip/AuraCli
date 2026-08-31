"""Tests for task_board module.

Tests for TaskBoard component.
"""

from unittest.mock import MagicMock, patch

import pytest


class TestTaskBoard:
    """Tests for TaskBoard class."""

    @pytest.fixture
    def mock_tracker(self):
        """Create mock TodoTracker."""
        tracker = MagicMock()
        tracker.get_all_tasks.return_value = []
        tracker.get_current_task.return_value = None
        tracker.get_stats.return_value = {"total": 0, "done": 0, "pending": 0}
        tracker.refresh.return_value = None
        tracker.scope = MagicMock(name="TestProject")
        return tracker

    def test_task_board_creation(self, mock_tracker):
        """Test TaskBoard can be created."""
        from aura_cli.cli.ui.components.task_board import TaskBoard

        board = TaskBoard(tracker=mock_tracker)

        assert board is not None
        assert board.tracker is mock_tracker

    def test_task_board_default_tracker(self):
        """Test TaskBoard uses default tracker."""
        from aura_cli.cli.ui.components.task_board import TaskBoard

        with patch(
            "aura_cli.cli.ui.components.task_board.get_todo_tracker"
        ) as mock_get:
            mock_get.return_value = MagicMock()

            TaskBoard()

            mock_get.assert_called_once()

    def test_categorize_tasks_empty(self, mock_tracker):
        """Test categorizing empty task list."""
        from aura_cli.cli.ui.components.task_board import TaskBoard

        board = TaskBoard(tracker=mock_tracker)

        categories = board._categorize_tasks()

        assert "todo" in categories
        assert "doing" in categories
        assert "done" in categories
        assert "priority" in categories
        assert len(categories["todo"]) == 0
        assert len(categories["doing"]) == 0
        assert len(categories["done"]) == 0

    def test_categorize_tasks_with_tasks(self, mock_tracker):
        """Test categorizing tasks with items."""
        from aura_cli.cli.ui.components.task_board import TaskBoard

        # Create mock tasks
        done_task = MagicMock(is_done=True, is_pending=False, text="Done task")
        pending_task = MagicMock(is_done=False, is_pending=True, text="Pending task")

        mock_tracker.get_all_tasks.return_value = [done_task, pending_task]

        board = TaskBoard(tracker=mock_tracker)
        categories = board._categorize_tasks()

        assert len(categories["done"]) == 1
        assert done_task in categories["done"]

    def test_create_progress_bar(self, mock_tracker):
        """Test creating progress bar."""
        from aura_cli.cli.ui.components.task_board import TaskBoard

        mock_tracker.get_stats.return_value = {"total": 10, "done": 5, "pending": 5}

        board = TaskBoard(tracker=mock_tracker)
        progress = board._create_progress_bar()

        assert progress is not None

    def test_create_progress_bar_empty(self, mock_tracker):
        """Test creating progress bar with no tasks."""
        from aura_cli.cli.ui.components.task_board import TaskBoard

        mock_tracker.get_stats.return_value = {"total": 0, "done": 0, "pending": 0}

        board = TaskBoard(tracker=mock_tracker)
        progress = board._create_progress_bar()

        assert progress is not None

    def test_create_column(self, mock_tracker):
        """Test creating a column."""
        from rich.table import Table

        from aura_cli.cli.ui.components.task_board import TaskBoard

        task = MagicMock(is_done=False, is_pending=True, text="Test task")

        board = TaskBoard(tracker=mock_tracker)
        column = board._create_column("To Do", "📌", [task], 1)

        assert isinstance(column, Table)

    def test_create_column_empty(self, mock_tracker):
        """Test creating empty column."""
        from rich.table import Table

        from aura_cli.cli.ui.components.task_board import TaskBoard

        board = TaskBoard(tracker=mock_tracker)
        column = board._create_column("To Do", "📌", [], 0)

        assert isinstance(column, Table)

    def test_create_column_long_task(self, mock_tracker):
        """Test creating column with long task text."""
        from aura_cli.cli.ui.components.task_board import TaskBoard

        long_text = "This is a very long task description that should be truncated"
        task = MagicMock(is_done=False, is_pending=True, text=long_text)

        board = TaskBoard(tracker=mock_tracker)
        column = board._create_column("To Do", "📌", [task], 1)

        assert column is not None

    def test_create_next_task_hint_none(self, mock_tracker):
        """Test creating hint when no current task."""
        from aura_cli.cli.ui.components.task_board import TaskBoard

        mock_tracker.get_current_task.return_value = None

        board = TaskBoard(tracker=mock_tracker)
        hint = board._create_next_task_hint()

        assert hint is None

    def test_create_next_task_hint_with_task(self, mock_tracker):
        """Test creating hint with current task."""
        from rich.text import Text

        from aura_cli.cli.ui.components.task_board import TaskBoard

        current_task = MagicMock(text="Current task")
        mock_tracker.get_current_task.return_value = current_task

        board = TaskBoard(tracker=mock_tracker)
        hint = board._create_next_task_hint()

        assert isinstance(hint, Text)

    def test_render(self, mock_tracker):
        """Test rendering complete board."""
        from rich.console import Group

        from aura_cli.cli.ui.components.task_board import TaskBoard

        board = TaskBoard(tracker=mock_tracker)
        result = board.render()

        assert isinstance(result, Group)


class TestDisplayTaskBoard:
    """Tests for display_task_board function."""

    def test_display_task_board(self):
        """Test display_task_board function."""
        from aura_cli.cli.ui.components.task_board import display_task_board

        mock_tracker = MagicMock()
        mock_tracker.get_all_tasks.return_value = []
        mock_tracker.get_current_task.return_value = None
        mock_tracker.get_stats.return_value = {"total": 0, "done": 0, "pending": 0}
        mock_tracker.refresh.return_value = None
        mock_tracker.scope = MagicMock(name="Test")

        with patch("aura_cli.cli.ui.display_facade.get_console") as mock_get_console:
            mock_console = MagicMock()
            mock_get_console.return_value = mock_console
            display_task_board(tracker=mock_tracker)

            assert mock_console.print.called
