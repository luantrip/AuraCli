"""Comprehensive tests for core modules.

Tests cover security, tools, services, and utility functions.
"""

class TestFileSystemSecurity:
    """Tests for file system security functions."""


    def test_sanitize_path_exists(self):
        """Test _sanitize_path function exists."""
        from aura_cli.core.tools.file_system import _sanitize_path

        assert callable(_sanitize_path)


    def test_is_path_safe_import(self):
        """Test is_path_safe function import."""
        from aura_cli.core.tools.file_system import is_path_safe

        assert callable(is_path_safe)


class TestSecretManager:
    """Tests for SecretManager."""


    def test_secret_manager_salt_method(self):
        """Test SecretManager has salt generation method."""
        from aura_cli.core.ops_tools.security.secret_manager import SecretManager

        manager = SecretManager(use_keyring=False)
        assert hasattr(manager, "_get_or_create_salt")


class TestEditExecutor:
    """Tests for EditExecutor with file locking."""


    def test_file_lock_function_import(self):
        """Test _get_file_lock function import."""
        from aura_cli.core.edit.edit_executor import _get_file_lock

        assert callable(_get_file_lock)

    def test_file_lock_same_path_returns_same_lock(self):
        """Test file lock creation returns same lock for same path."""
        from aura_cli.core.edit.edit_executor import _get_file_lock

        lock1 = _get_file_lock("/test/path.py")
        lock2 = _get_file_lock("/test/path.py")
        assert lock1 is lock2


class TestDatabaseMigration:
    """Tests for DatabaseMigration."""


    def test_migration_status_enum(self):
        """Test MigrationStatus enum."""
        from aura_cli.core.ops_tools.database.database_migration import MigrationStatus

        assert MigrationStatus.PENDING.value == "pending"
        assert MigrationStatus.APPLIED.value == "applied"

    def test_migration_dataclass(self):
        """Test Migration dataclass."""
        from aura_cli.core.ops_tools.database.database_migration import (
            Migration,
            MigrationStatus,
        )

        migration = Migration(
            id="001",
            version="20240101",
            name="test_migration",
            up_sql="CREATE TABLE test (id INT);",
            down_sql="DROP TABLE test;",
            status=MigrationStatus.PENDING,
        )
        assert migration.id == "001"
        assert migration.name == "test_migration"


class TestDatabaseMonitor:
    """Tests for DatabaseMonitor."""


    def test_database_metrics_dataclass(self):
        """Test DatabaseMetrics dataclass."""
        from aura_cli.core.ops_tools.database.database_monitor import DatabaseMetrics

        metrics = DatabaseMetrics(db_name="test_db", connections=10, active_queries=2)
        assert metrics.db_name == "test_db"
        assert metrics.connections == 10


class TestSentinelManager:
    """Tests for SentinelManager."""


class TestSessionState:
    """Tests for SessionState."""


    def test_session_state_creation(self):
        """Test SessionState dataclass."""
        from aura_cli.core.sessions.session_state import SessionState

        state = SessionState(session_id="test-123")
        assert state.session_id == "test-123"

    def test_session_state_has_active_mode(self):
        """Test SessionState has active_mode."""
        from aura_cli.core.sessions.session_state import SessionState

        state = SessionState(session_id="test")
        assert hasattr(state, "active_mode")


class TestMemoryService:
    """Tests for MemoryService."""


    def test_learned_rule_dataclass(self):
        """Test LearnedRule dataclass."""
        from aura_cli.core.memory.memory_service import LearnedRule

        rule = LearnedRule(rule="Test rule", context="test context", source="manual")
        assert rule.rule == "Test rule"

    def test_learned_rule_to_dict(self):
        """Test LearnedRule serialization."""
        from aura_cli.core.memory.memory_service import LearnedRule

        rule = LearnedRule(rule="Test", context="ctx")
        data = rule.to_dict()
        assert "rule" in data


class TestADKWorkflow:
    """Tests for ADK Workflow system."""


    def test_workflow_state_enum(self):
        """Test WorkflowState enum."""
        from aura_cli.adk.workflow import WorkflowState

        assert WorkflowState.PENDING.value == "pending"
        assert WorkflowState.RUNNING.value == "running"

    def test_step_state_enum(self):
        """Test StepState enum."""
        from aura_cli.adk.workflow import StepState

        assert StepState.PENDING.value == "pending"
        assert StepState.RUNNING.value == "running"

    def test_workflow_creation(self):
        """Test Workflow initialization."""
        from aura_cli.adk.workflow import Workflow

        workflow = Workflow("test_workflow", "Test description")
        assert workflow.name == "test_workflow"

    def test_workflow_step_creation(self):
        """Test WorkflowStep creation."""
        from aura_cli.adk.workflow import WorkflowStep

        step = WorkflowStep(name="test_step", task="Do something")
        assert step.name == "test_step"


class TestMonitorSession:
    """Tests for MonitorSession."""


    def test_monitor_config(self):
        """Test MonitorConfig dataclass."""
        from aura_cli.tui.tools.monitor import MonitorConfig

        config = MonitorConfig()
        assert hasattr(config, "color_mode")

    def test_monitor_content(self):
        """Test MonitorContent dataclass."""
        from aura_cli.tui.tools.monitor import ContentType, MonitorContent

        content = MonitorContent(
            url="https://example.com",
            content_type=ContentType.HTML,
            text="<html></html>",
        )
        assert content.url == "https://example.com"


class TestRateLimitError:
    """Tests for RateLimitError exception."""

    def test_rate_limit_error_creation(self):
        """Test RateLimitError creation."""
        from aura_cli.cli.utils.exceptions import RateLimitError

        error = RateLimitError(
            message="Rate limit exceeded", model="gpt-4", retry_after=60
        )
        assert error.model == "gpt-4"
        assert error.retry_after == 60


class TestWorkerFactory:
    """Tests for WorkerFactory functions."""


    def test_create_agi_worker_thread_import(self):
        """Test create_agi_worker_thread import."""
        from aura_cli.cli.utils.worker_factory import create_agi_worker_thread

        assert callable(create_agi_worker_thread)
