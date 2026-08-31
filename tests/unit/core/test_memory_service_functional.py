"""Functional tests for memory service module.

Tests for actual functionality of unified memory service.
"""

from datetime import datetime
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


class TestLearnedRule:
    """Tests for LearnedRule dataclass."""

    def test_learned_rule_creation(self):
        """Test creating LearnedRule."""
        from aura_cli.core.memory.memory_service import LearnedRule

        rule = LearnedRule(rule="Always write tests", context="coding")

        assert rule.rule == "Always write tests"
        assert rule.context == "coding"
        assert rule.source == "agi"

    def test_learned_rule_to_dict(self):
        """Test LearnedRule serialization."""
        from aura_cli.core.memory.memory_service import LearnedRule

        rule = LearnedRule(rule="Test rule", context="test context", source="manual")

        data = rule.to_dict()

        assert data["rule"] == "Test rule"
        assert data["context"] == "test context"
        assert data["source"] == "manual"
        assert "learned_at" in data

    def test_learned_rule_from_dict(self):
        """Test LearnedRule deserialization."""
        from aura_cli.core.memory.memory_service import LearnedRule

        data = {
            "rule": "Some rule",
            "context": "some context",
            "learned_at": "2024-01-01T00:00:00",
            "source": "ops",
        }

        rule = LearnedRule.from_dict(data)

        assert rule.rule == "Some rule"
        assert rule.context == "some context"
        assert rule.source == "ops"


class TestMemoryService:
    """Tests for MemoryService class."""

    @pytest.fixture
    def memory_service(self, tmp_path):
        """Create MemoryService instance for testing."""
        from aura_cli.core.memory.memory_service import MemoryService

        # Create necessary directories
        (tmp_path / ".aura" / "project_memories").mkdir(parents=True, exist_ok=True)

        with patch.dict("os.environ", {"AURA_HOME": str(tmp_path / ".aura")}):
            service = MemoryService(tmp_path / "project")
            return service

    def test_memory_service_creation(self, tmp_path):
        """Test creating MemoryService."""
        from aura_cli.core.memory.memory_service import MemoryService

        with patch.object(Path, "home", return_value=tmp_path):
            service = MemoryService(tmp_path / "project")

            assert service.project_root == (tmp_path / "project").resolve()
            assert service.memory_path.exists()

    def test_ensure_directories(self, memory_service):
        """Test that directories are created."""
        service = memory_service

        assert (service.memory_path / "notebook").exists()
        assert (service.memory_path / "scratchpad").exists()
        assert (service.memory_path / "sessions").exists()

    def test_get_constitution_empty(self, memory_service):
        """Test getting constitution when empty."""
        service = memory_service

        # Mock notebook_manager
        with patch.object(service, "_notebook_manager") as mock_nb:
            mock_nb.read_page.return_value = None
            service._notebook_manager = mock_nb

            service.get_constitution()
            # Should return None or empty for new project

    def test_save_constitution(self, memory_service):
        """Test saving constitution."""
        service = memory_service

        mock_nb = MagicMock()
        mock_nb.write_page.return_value = True
        service._notebook_manager = mock_nb

        result = service.save_constitution("Test constitution content")

        assert result is True
        mock_nb.write_page.assert_called_once()

    def test_has_constitution_false(self, memory_service):
        """Test has_constitution when empty."""
        service = memory_service

        mock_nb = MagicMock()
        mock_nb.read_page.return_value = None
        service._notebook_manager = mock_nb

        result = service.has_constitution()
        assert result is False

    def test_get_conventions(self, memory_service):
        """Test getting conventions."""
        service = memory_service

        mock_nb = MagicMock()
        mock_nb.read_page.return_value = "Code style guidelines"
        service._notebook_manager = mock_nb

        result = service.get_conventions()
        assert result == "Code style guidelines"

    def test_save_conventions(self, memory_service):
        """Test saving conventions."""
        service = memory_service

        mock_nb = MagicMock()
        mock_nb.write_page.return_value = True
        service._notebook_manager = mock_nb

        result = service.save_conventions("New conventions")

        assert result is True

    def test_get_learned_rules_empty(self, memory_service):
        """Test getting learned rules when empty."""
        service = memory_service

        # Ensure rules file has empty list
        rules_file = service.memory_path / "scratchpad" / "rules.json"
        rules_file.write_text('{"rules": []}')

        rules = service.get_learned_rules()
        assert rules == []

    def test_add_learned_rule(self, memory_service):
        """Test adding learned rule."""
        service = memory_service

        # Initialize empty rules
        rules_file = service.memory_path / "scratchpad" / "rules.json"
        rules_file.write_text('{"rules": []}')

        result = service.add_learned_rule(
            "Always validate input", context="security", source="agi"
        )

        assert result is True

        # Verify rule was saved
        rules = service.get_learned_rules()
        assert len(rules) == 1
        assert rules[0].rule == "Always validate input"

    def test_add_duplicate_rule(self, memory_service):
        """Test adding duplicate rule is rejected."""
        service = memory_service

        # Initialize empty rules
        rules_file = service.memory_path / "scratchpad" / "rules.json"
        rules_file.write_text('{"rules": []}')

        # Add first rule
        service.add_learned_rule("Rule 1")

        # Try adding duplicate
        result = service.add_learned_rule("Rule 1")

        assert result is False

    def test_clear_scratchpad(self, memory_service):
        """Test clearing scratchpad."""
        service = memory_service

        # Add some rules first
        rules_file = service.memory_path / "scratchpad" / "rules.json"
        rules_file.write_text(
            '{"rules": [{"rule": "test", "context": "", "learned_at": "2024-01-01", "source": "agi"}]}'
        )

        result = service.clear_scratchpad()

        assert result is True
        rules = service.get_learned_rules()
        assert rules == []

    def test_consolidate_rules(self, memory_service):
        """Test consolidating rules into constitution."""
        service = memory_service

        # Setup: add some rules
        rules_file = service.memory_path / "scratchpad" / "rules.json"
        rules_data = {
            "rules": [
                {
                    "rule": "Rule 1",
                    "context": "",
                    "learned_at": "2024-01-01",
                    "source": "agi",
                },
                {
                    "rule": "Rule 2",
                    "context": "",
                    "learned_at": "2024-01-01",
                    "source": "agi",
                },
            ]
        }
        rules_file.write_text(json.dumps(rules_data))

        # Mock notebook manager
        mock_nb = MagicMock()
        mock_nb.read_page.return_value = "Existing constitution"
        mock_nb.write_page.return_value = True
        service._notebook_manager = mock_nb

        result = service.consolidate_rules()

        assert result is True

    def test_validate_prompt(self, memory_service):
        """Test prompt validation."""
        service = memory_service

        # Without constitution
        is_valid, violations, _sanitized = service.validate_prompt("Test prompt")

        assert is_valid is True
        assert violations == []

    def test_get_memory_info(self, memory_service):
        """Test getting memory info."""
        service = memory_service

        mock_nb = MagicMock()
        mock_nb.read_page.return_value = None
        service._notebook_manager = mock_nb

        info = service.get_memory_info()

        assert "memory_path" in info
        assert "has_constitution" in info
        assert "learned_rules_count" in info

    def test_reset(self, memory_service):
        """Test resetting memory service."""
        service = memory_service

        service._constitution_cache = "cached"
        service._constitution_loaded = True

        service.reset()

        assert service._constitution_cache is None
        assert service._constitution_loaded is False

    def test_notebook_manager_property(self, memory_service):
        """Test notebook_manager lazy loading."""
        service = memory_service

        # First access creates manager
        manager1 = service.notebook_manager
        assert manager1 is not None

        # Second access returns same instance
        manager2 = service.notebook_manager
        assert manager1 is manager2

    def test_notebook_service_property(self, memory_service):
        """Test notebook_service lazy loading."""
        service = memory_service

        # First access creates service
        svc1 = service.notebook_service
        assert svc1 is not None

        # Second access returns same instance
        svc2 = service.notebook_service
        assert svc1 is svc2


class TestMemoryServiceFactory:
    """Tests for memory service factory functions."""

    def test_get_memory_service_singleton(self, tmp_path):
        """Test get_memory_service returns same instance for same project."""
        from aura_cli.core.memory.memory_service import get_memory_service

        with patch.object(Path, "home", return_value=tmp_path):
            project = tmp_path / "my_project"
            project.mkdir(exist_ok=True)

            svc1 = get_memory_service(project)
            svc2 = get_memory_service(project)

            assert svc1 is svc2

    def test_get_memory_service_different_projects(self, tmp_path):
        """Test get_memory_service returns different instances for different projects."""
        from aura_cli.core.memory.memory_service import get_memory_service

        with patch.object(Path, "home", return_value=tmp_path):
            project1 = tmp_path / "project1"
            project2 = tmp_path / "project2"
            project1.mkdir(exist_ok=True)
            project2.mkdir(exist_ok=True)

            svc1 = get_memory_service(project1)
            svc2 = get_memory_service(project2)

            assert svc1 is not svc2

    def test_reset_memory_service_specific(self, tmp_path):
        """Test reset_memory_service for specific project."""
        from aura_cli.core.memory.memory_service import (
            get_memory_service,
            reset_memory_service,
        )

        with patch.object(Path, "home", return_value=tmp_path):
            project = tmp_path / "my_project"
            project.mkdir(exist_ok=True)

            svc = get_memory_service(project)
            assert svc is not None

            reset_memory_service(project)

            # New instance should be created after reset
            svc2 = get_memory_service(project)
            assert svc is not svc2

    def test_reset_memory_service_all(self, tmp_path):
        """Test reset_memory_service clears all instances."""
        from aura_cli.core.memory.memory_service import (
            get_memory_service,
            reset_memory_service,
        )

        with patch.object(Path, "home", return_value=tmp_path):
            project1 = tmp_path / "project1"
            project2 = tmp_path / "project2"
            project1.mkdir(exist_ok=True)
            project2.mkdir(exist_ok=True)

            svc1 = get_memory_service(project1)
            svc2 = get_memory_service(project2)

            assert svc1 is not svc2

            # Reset all
            reset_memory_service()

            # New instances should be created
            svc1_new = get_memory_service(project1)
            assert svc1 is not svc1_new


class TestQuerySnapshots:
    """Tests for snapshot querying."""

    def test_query_snapshots_empty(self, tmp_path):
        """Test querying snapshots when none exist."""
        from aura_cli.core.memory.memory_service import MemoryService

        with patch.object(Path, "home", return_value=tmp_path):
            results = MemoryService.query_snapshots()
            assert results == []

    def test_query_snapshots_with_date_filter(self, tmp_path):
        """Test querying snapshots with date filter."""
        from aura_cli.core.memory.memory_service import MemoryService

        # Create directory structure
        central_root = tmp_path / ".aura" / "project_memories"
        project_dir = central_root / "abc123"
        sessions_dir = project_dir / "sessions"
        sessions_dir.mkdir(parents=True, exist_ok=True)

        # Create a session directory with valid date format
        session_dir = sessions_dir / "20240115_120000"
        session_dir.mkdir()

        with patch.dict("os.environ", {"AURA_HOME": str(tmp_path / ".aura")}):
            start_date = datetime(2024, 1, 1)
            end_date = datetime(2024, 12, 31)

            results = MemoryService.query_snapshots(
                start_date=start_date, end_date=end_date
            )

            assert len(results) == 1
            assert results[0]["project_id"] == "abc123"
