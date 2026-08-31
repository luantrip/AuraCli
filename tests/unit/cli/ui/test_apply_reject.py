"""Tests for apply_reject module.

Tests for ApplyRejectManager and related functions.
"""

from unittest.mock import patch

import pytest


class TestApplyState:
    """Tests for ApplyState enum."""

    def test_apply_state_values(self):
        """Test ApplyState enum has all expected values."""
        from aura_cli.cli.ui.apply_reject import ApplyState

        assert ApplyState.NOT_STARTED.value == "not-started"
        assert ApplyState.STREAMING.value == "streaming"
        assert ApplyState.DONE.value == "done"
        assert ApplyState.CLOSED.value == "closed"
        assert ApplyState.ERROR.value == "error"

    def test_apply_state_is_enum(self):
        """Test ApplyState is an Enum."""
        from enum import Enum

        from aura_cli.cli.ui.apply_reject import ApplyState

        assert issubclass(ApplyState, Enum)


class TestApplyRejectManager:
    """Tests for ApplyRejectManager class."""

    @pytest.fixture
    def manager(self):
        """Create fresh ApplyRejectManager instance."""
        from aura_cli.cli.ui.apply_reject import ApplyRejectManager

        return ApplyRejectManager()

    def test_manager_init(self, manager):
        """Test manager initialization."""
        assert manager.pending_changes == {}
        assert manager.applied_changes == {}
        assert manager.rejected_changes == {}
        assert manager.change_history == []

    def test_register_change(self, manager):
        """Test registering a change."""
        from aura_cli.cli.ui.apply_reject import ApplyState

        manager.register_change(
            change_id="change1",
            file_path="/path/to/file.py",
            old_content="old",
            new_content="new",
            description="Test change",
        )

        assert "change1" in manager.pending_changes
        change = manager.pending_changes["change1"]
        assert change["file_path"] == "/path/to/file.py"
        assert change["old_content"] == "old"
        assert change["new_content"] == "new"
        assert change["description"] == "Test change"
        assert change["state"] == ApplyState.NOT_STARTED

    def test_register_change_without_description(self, manager):
        """Test registering a change without description."""
        manager.register_change(
            change_id="change2",
            file_path="/path/to/file.py",
            old_content="old",
            new_content="new",
        )

        assert manager.pending_changes["change2"]["description"] is None

    def test_apply_change_not_found(self, manager):
        """Test applying non-existent change."""
        result = manager.apply_change("nonexistent")
        assert result is False

    def test_apply_change_success(self, manager, tmp_path):
        """Test successful change application."""
        test_file = tmp_path / "test.py"
        test_file.write_text("old content")

        manager.register_change(
            change_id="change1",
            file_path=str(test_file),
            old_content="old content",
            new_content="new content",
        )

        with patch("aura_cli.cli.ui.apply_reject.console"):
            result = manager.apply_change("change1")

        assert result is True
        assert test_file.read_text() == "new content"
        assert "change1" in manager.applied_changes
        assert "change1" not in manager.pending_changes
        assert len(manager.change_history) == 1
        assert manager.change_history[0]["action"] == "applied"

    def test_apply_change_creates_backup(self, manager, tmp_path):
        """Test that apply creates backup."""
        test_file = tmp_path / "test.py"
        test_file.write_text("original content")

        manager.register_change(
            change_id="change1",
            file_path=str(test_file),
            old_content="original content",
            new_content="new content",
        )

        with patch("aura_cli.cli.ui.apply_reject.console"):
            manager.apply_change("change1")

        backup_file = tmp_path / "test.py.aura_backup"
        assert backup_file.exists()
        assert backup_file.read_text() == "original content"

    def test_apply_change_creates_directory(self, manager, tmp_path):
        """Test that apply creates directory if needed."""
        new_dir = tmp_path / "subdir"
        test_file = new_dir / "test.py"

        manager.register_change(
            change_id="change1",
            file_path=str(test_file),
            old_content="",
            new_content="new content",
        )

        with patch("aura_cli.cli.ui.apply_reject.console"):
            result = manager.apply_change("change1")

        assert result is True
        assert test_file.exists()

    def test_reject_change_not_found(self, manager):
        """Test rejecting non-existent change."""
        result = manager.reject_change("nonexistent")
        assert result is False

    def test_reject_change_success(self, manager):
        """Test successful change rejection."""
        from aura_cli.cli.ui.apply_reject import ApplyState

        manager.register_change(
            change_id="change1",
            file_path="/path/to/file.py",
            old_content="old",
            new_content="new",
        )

        with patch("aura_cli.cli.ui.apply_reject.console"):
            result = manager.reject_change("change1")

        assert result is True
        assert "change1" in manager.rejected_changes
        assert "change1" not in manager.pending_changes
        assert manager.rejected_changes["change1"]["state"] == ApplyState.CLOSED
        assert len(manager.change_history) == 1
        assert manager.change_history[0]["action"] == "rejected"

    def test_get_change_pending(self, manager):
        """Test getting pending change."""
        manager.register_change("change1", "/file.py", "old", "new")

        result = manager.get_change("change1")

        assert result is not None
        assert result["file_path"] == "/file.py"

    def test_get_change_applied(self, manager, tmp_path):
        """Test getting applied change."""
        test_file = tmp_path / "test.py"
        test_file.write_text("old")

        manager.register_change("change1", str(test_file), "old", "new")

        with patch("aura_cli.cli.ui.apply_reject.console"):
            manager.apply_change("change1")

        result = manager.get_change("change1")
        assert result is not None

    def test_get_change_rejected(self, manager):
        """Test getting rejected change."""
        manager.register_change("change1", "/file.py", "old", "new")

        with patch("aura_cli.cli.ui.apply_reject.console"):
            manager.reject_change("change1")

        result = manager.get_change("change1")
        assert result is not None

    def test_get_change_not_found(self, manager):
        """Test getting non-existent change."""
        result = manager.get_change("nonexistent")
        assert result is None

    def test_render_change_preview_not_found(self, manager):
        """Test render_change_preview for non-existent change."""
        from rich.panel import Panel

        result = manager.render_change_preview("nonexistent")

        assert isinstance(result, Panel)

    def test_render_change_preview_success(self, manager):
        """Test render_change_preview for existing change."""
        from rich.panel import Panel

        manager.register_change(
            "change1", "/file.py", "def old(): pass", "def new(): pass"
        )

        result = manager.render_change_preview("change1")

        assert isinstance(result, Panel)

    def test_render_change_history_empty(self, manager):
        """Test render_change_history with empty history."""
        from rich.table import Table

        result = manager.render_change_history()

        assert isinstance(result, Table)

    def test_render_change_history_with_entries(self, manager):
        """Test render_change_history with entries."""
        from rich.table import Table

        manager.register_change("change1", "/file1.py", "old", "new")
        manager.register_change("change2", "/file2.py", "old", "new")

        with patch("aura_cli.cli.ui.apply_reject.console"):
            manager.reject_change("change1")

        result = manager.render_change_history(limit=5)

        assert isinstance(result, Table)


class TestGlobalManager:
    """Tests for global manager functions."""

    def test_get_apply_reject_manager(self):
        """Test getting global manager."""
        from aura_cli.cli.ui.apply_reject import (
            ApplyRejectManager,
            get_apply_reject_manager,
        )

        manager = get_apply_reject_manager()

        assert isinstance(manager, ApplyRejectManager)

    def test_get_apply_reject_manager_singleton(self):
        """Test global manager is singleton."""
        from aura_cli.cli.ui.apply_reject import get_apply_reject_manager

        manager1 = get_apply_reject_manager()
        manager2 = get_apply_reject_manager()

        assert manager1 is manager2


class TestDisplayApplyRejectActions:
    """Tests for display_apply_reject_actions function."""

    def test_display_actions_function_exists(self):
        """Test display_apply_reject_actions function exists."""
        from aura_cli.cli.ui.apply_reject import display_apply_reject_actions

        assert callable(display_apply_reject_actions)
