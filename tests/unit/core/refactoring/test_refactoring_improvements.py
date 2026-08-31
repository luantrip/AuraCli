"""
Tests for the refactoring improvements made in this session.

This test module validates the changes made to:
- SessionStateManager: Auto-consolidation feature
- TaskParameterNormalizer: Extended schemas and aliases
- TextualUIManager: ensure_initialized() and graceful prompt fallback
- UnifiedMemoryService: Convention saving

Author: Refactoring Session - December 3, 2025
"""

from pathlib import Path
import tempfile
from unittest.mock import MagicMock

import pytest


# Test SessionStateManager auto-consolidation
class TestSessionStateAutoConsolidation:
    """Tests for the auto-consolidation feature in SessionStateManager."""

    def test_auto_consolidation_settings_exist(self):
        """Test that auto-consolidation settings are available."""
        from aura_cli.core.sessions.session_state import SessionStateManager

        SessionStateManager()

        # Check class-level attributes exist
        assert hasattr(SessionStateManager, "AUTO_CONSOLIDATION_THRESHOLD")
        assert hasattr(SessionStateManager, "AUTO_CONSOLIDATION_ENABLED")

        # Check default values
        assert SessionStateManager.AUTO_CONSOLIDATION_THRESHOLD == 5
        assert SessionStateManager.AUTO_CONSOLIDATION_ENABLED is True

    def test_rules_counter_initialization(self):
        """Test that rules counter is initialized."""
        from aura_cli.core.sessions.session_state import SessionStateManager

        manager = SessionStateManager()

        assert hasattr(manager, "_rules_since_consolidation")
        assert manager._rules_since_consolidation == 0

    def test_get_rules_pending_consolidation(self):
        """Test the method to get pending rules count."""
        from aura_cli.core.sessions.session_state import SessionStateManager

        manager = SessionStateManager()
        manager._rules_since_consolidation = 3

        assert manager.get_rules_pending_consolidation() == 3

    def test_set_auto_consolidation(self):
        """Test configuring auto-consolidation settings."""
        from aura_cli.core.sessions.session_state import SessionStateManager

        manager = SessionStateManager()

        # Disable auto-consolidation
        manager.set_auto_consolidation(enabled=False)
        assert manager.AUTO_CONSOLIDATION_ENABLED is False

        # Re-enable with custom threshold
        manager.set_auto_consolidation(enabled=True, threshold=10)
        assert manager.AUTO_CONSOLIDATION_ENABLED is True
        assert manager.AUTO_CONSOLIDATION_THRESHOLD == 10


# Test TaskParameterNormalizer extended schemas
class TestTaskParameterNormalizerExtended:
    """Tests for the extended TaskParameterNormalizer schemas."""

    def test_file_operation_aliases(self):
        """Test that file operation aliases work correctly."""
        from aura_cli.core.agents.planning.task_parameter_normalizer import (
            TaskParameterNormalizer,
        )

        normalizer = TaskParameterNormalizer()

        # Test file_path alias for read_file
        params, _errors = normalizer.normalize(
            "read_file",
            {"file_path": "test.py"},  # Using alias
        )

        assert "path" in params
        assert params["path"].endswith("test.py")
        assert "file_path" not in params or params.get("file_path") == params.get(
            "path"
        )

    def test_edit_file_aliases(self):
        """Test edit_file with text aliases."""
        from aura_cli.core.agents.planning.task_parameter_normalizer import (
            TaskParameterNormalizer,
        )

        normalizer = TaskParameterNormalizer()

        # Test old_text/new_text aliases
        params, _errors = normalizer.normalize(
            "edit_file",
            {
                "path": "test.py",
                "old_text": "hello",  # alias for old_content
                "new_text": "world",  # alias for new_content
            },
        )

        assert "old_content" in params
        assert "new_content" in params
        assert params["old_content"] == "hello"
        assert params["new_content"] == "world"

    def test_find_in_files_aliases(self):
        """Test find_in_files with query alias."""
        from aura_cli.core.agents.planning.task_parameter_normalizer import (
            TaskParameterNormalizer,
        )

        normalizer = TaskParameterNormalizer()

        # Test query alias for pattern
        params, _errors = normalizer.normalize(
            "find_in_files",
            {"query": "TODO"},  # alias for pattern
        )

        assert "pattern" in params
        assert params["pattern"] == "TODO"

    def test_git_commit_alias(self):
        """Test git_commit with msg alias."""
        from aura_cli.core.agents.planning.task_parameter_normalizer import (
            TaskParameterNormalizer,
        )

        normalizer = TaskParameterNormalizer()

        params, _errors = normalizer.normalize(
            "git_commit",
            {"msg": "Initial commit"},  # alias for message
        )

        assert "message" in params
        assert params["message"] == "Initial commit"

    def test_new_task_types_exist(self):
        """Test that new task types are defined."""
        from aura_cli.core.agents.planning.task_parameter_normalizer import (
            TaskParameterNormalizer,
        )

        normalizer = TaskParameterNormalizer()

        # Check new task types exist
        new_types = [
            "copy_file",
            "move_file",
            "create_directory",
            "find_files",
            "lint_code",
            "run_script",
            "run_single_test",
            "git_add",
            "git_log",
            "git_branch",
            "git_checkout",
            "generate_docs",
            "save_to_memory",
            "search_memory",
        ]

        for task_type in new_types:
            assert normalizer.validate_task_type(task_type), (
                f"Task type {task_type} should exist"
            )

    def test_agent_specific_defaults(self):
        """Test agent-specific default values."""
        from aura_cli.core.agents.planning.task_parameter_normalizer import (
            TaskParameterNormalizer,
        )

        normalizer = TaskParameterNormalizer()

        # Test that agent_specific schema exists for review_agent
        schema = normalizer.get_schema("analyze_code")
        assert "agent_specific" in schema
        assert "review_agent" in schema["agent_specific"]

        # Test that review_agent has required file_path
        review_schema = schema["agent_specific"]["review_agent"]
        assert "file_path" in review_schema.get("required", [])

        # Test that agent mapping (path -> file_path) works
        params, _errors = normalizer.normalize(
            "analyze_code",
            {"path": "test.py"},
            agent_id="review_agent",
        )

        assert "file_path" in params, "file_path should be mapped from path"


# Test TextualUIManager improvements
class TestTextualUIManagerImprovements:
    """Tests for TextualUIManager improvements."""

    def test_init_pending_flag(self):
        """Test that _init_pending flag is set on initialization."""
        from aura_cli.tui.bridge import TextualUIManager

        mock_app = MagicMock()
        manager = TextualUIManager(mock_app)

        assert hasattr(manager, "_init_pending")
        assert manager._init_pending is True

    def test_is_initialized_before_init(self):
        """Test is_initialized returns False before initialization."""
        from aura_cli.tui.bridge import TextualUIManager

        mock_app = MagicMock()
        manager = TextualUIManager(mock_app)

        assert manager.is_initialized() is False

    def test_prompt_returns_empty_string(self):
        """Test that prompt() returns empty string instead of raising."""
        from aura_cli.tui.bridge import TextualUIManager

        mock_app = MagicMock()
        manager = TextualUIManager(mock_app)

        # Should not raise, should return empty string
        result = manager.prompt()
        assert result == ""

    def test_ensure_initialized_exists(self):
        """Test that ensure_initialized method exists."""
        from aura_cli.tui.bridge import TextualUIManager

        mock_app = MagicMock()
        manager = TextualUIManager(mock_app)

        assert hasattr(manager, "ensure_initialized")
        assert callable(manager.ensure_initialized)


# Test UnifiedMemoryService convention saving
class TestUnifiedMemoryServiceConventions:
    """Tests for UnifiedMemoryService convention features."""

    def test_save_conventions_method_exists(self):
        """Test that save_conventions method exists."""
        from aura_cli.core.memory.memory_service import MemoryService

        assert hasattr(MemoryService, "save_conventions")
        assert callable(MemoryService.save_conventions)

    def test_get_conventions_method_exists(self):
        """Test that get_conventions method exists."""
        from aura_cli.core.memory.memory_service import MemoryService

        assert hasattr(MemoryService, "get_conventions")
        assert callable(MemoryService.get_conventions)

    def test_convention_methods_integrated(self):
        """Test that conventions are integrated with notebook manager."""
        with tempfile.TemporaryDirectory() as tmpdir:
            from aura_cli.core.memory.memory_service import MemoryService

            service = MemoryService(Path(tmpdir))

            # Save conventions
            content = "# Test Conventions\n\nTest content"
            result = service.save_conventions(content)

            # Should succeed (file saved)
            assert result is True

            # Should be retrievable
            retrieved = service.get_conventions()
            assert retrieved is not None
            assert "Test Conventions" in retrieved


# Test integration of project_indexer with unified memory
class TestProjectIndexerUnifiedMemory:
    """Tests for project_indexer integration with unified memory."""

    def test_project_indexer_uses_unified_memory(self):
        """Test that project_indexer uses UnifiedMemoryService for conventions."""
        import inspect

        from aura_cli.core.context.project_indexer import handle_init_command

        # Check that the function source code mentions unified memory
        source = inspect.getsource(handle_init_command)

        # Should import and use unified memory (via factory or class)
        assert any(
            term in source
            for term in [
                "unified_memory",
                "UnifiedMemoryService",
                "get_memory_service",
                "ProjectContextManager",
                "ctx_manager",
            ]
        )


# Test AGI-TodoTracker integration
class TestAGITodoTrackerIntegration:
    """Tests for AGI plan synchronization with TodoTracker."""

    def test_add_agi_plan_method_exists(self):
        """Test that add_agi_plan method exists on TodoTracker."""
        from aura_cli.core.todo.todo_tracker import TodoTracker

        assert hasattr(TodoTracker, "add_agi_plan")
        assert callable(TodoTracker.add_agi_plan)

    def test_mark_task_by_text_method_exists(self):
        """Test that mark_task_by_text method exists on TodoTracker."""
        from aura_cli.core.todo.todo_tracker import TodoTracker

        assert hasattr(TodoTracker, "mark_task_by_text")
        assert callable(TodoTracker.mark_task_by_text)

    def test_get_agi_plan_tasks_method_exists(self):
        """Test that get_agi_plan_tasks method exists on TodoTracker."""
        from aura_cli.core.todo.todo_tracker import TodoTracker

        assert hasattr(TodoTracker, "get_agi_plan_tasks")
        assert callable(TodoTracker.get_agi_plan_tasks)

    def test_add_agi_plan_creates_tasks(self):
        """Test that add_agi_plan creates tasks in to-do.md."""
        with tempfile.TemporaryDirectory() as tmpdir:
            from aura_cli.core.todo.todo_tracker import TodoTracker

            tracker = TodoTracker(scope=tmpdir)

            tasks = [
                {"id": "t1", "description": "Analisar código", "type": "analyze_code"},
                {"id": "t2", "description": "Refatorar módulo", "type": "edit_file"},
            ]

            created_ids = tracker.add_agi_plan("Test Plan", tasks)

            assert len(created_ids) == 2

            # Verify tasks were created
            all_tasks = tracker.get_all_tasks()
            assert len(all_tasks) >= 2

    def test_get_agi_plan_tasks_filters_correctly(self):
        """Test that get_agi_plan_tasks returns only AGI tasks."""
        with tempfile.TemporaryDirectory() as tmpdir:
            from aura_cli.core.todo.todo_tracker import TodoTracker

            tracker = TodoTracker(scope=tmpdir)

            # Add AGI plan
            tasks = [
                {"id": "t1", "description": "AGI Task", "type": "analyze_code"},
            ]
            tracker.add_agi_plan("Test Plan", tasks)

            # Add regular task
            tracker.add_task("Regular task without type")

            # Get AGI tasks only
            agi_tasks = tracker.get_agi_plan_tasks()

            # Should have at least 1 AGI task
            assert len(agi_tasks) >= 1

            # AGI tasks should have [type] format
            for task in agi_tasks:
                assert task.text.startswith("[")

    def test_mark_task_by_text_marks_correct_task(self):
        """Test that mark_task_by_text marks the correct task."""
        with tempfile.TemporaryDirectory() as tmpdir:
            import aura_cli.core.todo.todo_tracker as _tt_mod
            from aura_cli.core.todo.todo_tracker import TodoTracker

            # Reset global singleton so previous tests don't leak state
            _tt_mod._global_tracker = None  # type: ignore[attr-defined]

            tracker = TodoTracker(scope=tmpdir)

            tasks = [
                {
                    "id": "t1",
                    "description": "Analisar código Python",
                    "type": "analyze_code",
                },
                {
                    "id": "t2",
                    "description": "Editar arquivo config",
                    "type": "edit_file",
                },
            ]
            tracker.add_agi_plan("Test Plan", tasks)

            # Mark task by partial text
            success, text = tracker.mark_task_by_text("analisar")

            assert success is True
            assert text is not None
            assert "analisar" in text.lower()

            # Verify stats
            stats = tracker.get_stats()
            assert stats["done"] >= 1

    def test_agi_worker_has_planner_with_sync_methods(self):
        """Test that AgiWorker exposes planner attribute (None until run())."""
        from aura_cli.cli.workers.agi_worker import AgiWorker
        from aura_cli.core.agi.planning import AgiPlanner

        worker = AgiWorker(
            prompt="test",
            model="auto",
            api_keys={},
            headless=True,
            use_advanced_features=True,
        )

        # planner is declared in __init__ (None) and populated in _initialize_advanced_components
        assert hasattr(worker, "planner"), (
            "AgiWorker must declare self.planner in __init__"
        )

        # Verify AgiPlanner has the expected sync methods
        assert hasattr(AgiPlanner, "sync_plan_to_todo"), (
            "AgiPlanner must have sync_plan_to_todo"
        )
        assert hasattr(AgiPlanner, "mark_todo_task_done"), (
            "AgiPlanner must have mark_todo_task_done"
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
