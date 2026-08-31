"""Functional tests for core modules.

Tests for actual functionality of core modules.
"""


class TestFileSystemOperations:
    """Tests for file system operations."""

    def test_read_file_content(self, temp_dir):
        """Test reading file content."""
        from aura_cli.core.tools.file_system import enable_path_validation, read_file

        enable_path_validation(False)

        test_file = temp_dir / "test.txt"
        test_file.write_text("Hello, World!")

        result = read_file(str(test_file))
        assert "Hello" in result

    def test_read_file_nonexistent(self):
        """Test reading nonexistent file."""
        from aura_cli.core.tools.file_system import enable_path_validation, read_file

        enable_path_validation(False)

        result = read_file("/nonexistent/file.txt")
        assert "não encontrado" in result.lower() or "erro" in result.lower()

    def test_list_directory_exists(self, temp_dir):
        """Test listing directory."""
        from aura_cli.core.tools.file_system import (
            enable_path_validation,
            list_directory,
        )

        enable_path_validation(False)

        (temp_dir / "file1.txt").write_text("content")
        result = list_directory(str(temp_dir))
        assert result is not None

    def test_write_file_content(self, temp_dir, monkeypatch):
        """Test writing file content."""
        import aura_cli.core.tools.file_system as fs_module
        from aura_cli.core.tools.file_system import enable_path_validation, write_file

        enable_path_validation(False)

        # Enable auto-confirm for tests
        monkeypatch.setattr(fs_module, "AUTO_CONFIRM_TOOLS", True)

        test_file = temp_dir / "new.txt"
        write_file(str(test_file), "New content")
        assert test_file.read_text() == "New content"


class TestDevToolsOperations:
    """Tests for dev tools operations."""

    def test_validate_syntax_python_valid(self):
        """Test Python syntax validation."""
        from aura_cli.core.tools.dev_tools import validate_syntax

        result = validate_syntax("def f(): pass", "python")
        assert result is not None

    def test_validate_syntax_json_valid(self):
        """Test JSON syntax validation."""
        from aura_cli.core.tools.dev_tools import validate_syntax

        result = validate_syntax('{"key": "value"}', "json")
        assert result is not None


class TestSessionState:
    """Tests for session state."""

    def test_session_state_creation(self):
        """Test SessionState creation."""
        from aura_cli.core.sessions.session_state import SessionState

        state = SessionState(session_id="test-123")
        assert state.session_id == "test-123"

    def test_session_state_mode(self):
        """Test SessionState mode."""
        from aura_cli.core.sessions.session_state import SessionState

        state = SessionState(session_id="test")
        assert state.active_mode == "normal"

    def test_session_state_constitution(self):
        """Test SessionState constitution."""
        from aura_cli.core.sessions.session_state import SessionState

        state = SessionState(session_id="test")
        assert state.has_constitution() is False
        state.constitution = "Test"
        assert state.has_constitution() is True


class TestLearnedRule:
    """Tests for LearnedRule."""

    def test_learned_rule_creation(self):
        """Test LearnedRule creation."""
        from aura_cli.core.memory.memory_service import LearnedRule

        rule = LearnedRule(rule="Test rule", context="test")
        assert rule.rule == "Test rule"

    def test_learned_rule_to_dict(self):
        """Test LearnedRule serialization."""
        from aura_cli.core.memory.memory_service import LearnedRule

        rule = LearnedRule(rule="Test", context="ctx")
        data = rule.to_dict()
        assert "rule" in data


class TestSecretManager:
    """Tests for SecretManager."""

    def test_secret_manager_creation(self):
        """Test SecretManager creation."""
        from aura_cli.core.ops_tools.security.secret_manager import SecretManager

        manager = SecretManager(use_keyring=False)
        assert manager is not None

    def test_secret_manager_salt(self):
        """Test SecretManager salt generation."""
        from aura_cli.core.ops_tools.security.secret_manager import SecretManager

        manager = SecretManager(use_keyring=False)
        salt = manager._get_or_create_salt()
        assert isinstance(salt, bytes)
        assert len(salt) == 16


class TestDatabaseMigration:
    """Tests for DatabaseMigration."""

    def test_migration_status_enum(self):
        """Test MigrationStatus enum."""
        from aura_cli.core.ops_tools.database.database_migration import MigrationStatus

        assert MigrationStatus.PENDING.value == "pending"
        assert MigrationStatus.APPLIED.value == "applied"

    def test_migration_creation(self):
        """Test Migration dataclass."""
        from aura_cli.core.ops_tools.database.database_migration import (
            Migration,
            MigrationStatus,
        )

        migration = Migration(
            id="001",
            version="20240101",
            name="test",
            up_sql="CREATE TABLE t (id INT);",
            down_sql="DROP TABLE t;",
            status=MigrationStatus.PENDING,
        )
        assert migration.id == "001"


class TestDatabaseMetrics:
    """Tests for DatabaseMetrics."""

    def test_metrics_creation(self):
        """Test DatabaseMetrics creation."""
        from aura_cli.core.ops_tools.database.database_monitor import DatabaseMetrics

        metrics = DatabaseMetrics(db_name="test", connections=10)
        assert metrics.db_name == "test"


class TestFileDiff:
    """Tests for FileDiff."""

    def test_file_diff_has_changes(self):
        """Test FileDiff has_changes."""
        from aura_cli.core.context.sentinel_manager import FileDiff

        diff = FileDiff(added=["f.py"], modified=[], deleted=[], stats={})
        assert diff.has_changes is True

    def test_file_diff_no_changes(self):
        """Test FileDiff no changes."""
        from aura_cli.core.context.sentinel_manager import FileDiff

        diff = FileDiff(added=[], modified=[], deleted=[], stats={})
        assert diff.has_changes is False


class TestWorkflow:
    """Tests for Workflow."""

    def test_workflow_creation(self):
        """Test Workflow creation."""
        from aura_cli.adk.workflow import Workflow

        wf = Workflow(name="test", description="Test")
        assert wf.name == "test"

    def test_workflow_step_creation(self):
        """Test WorkflowStep creation."""
        from aura_cli.adk.workflow import WorkflowStep

        step = WorkflowStep(name="step1", task="Do task")
        assert step.name == "step1"


class TestRateLimitError:
    """Tests for RateLimitError."""

    def test_rate_limit_error(self):
        """Test RateLimitError creation."""
        from aura_cli.cli.utils.exceptions import RateLimitError

        error = RateLimitError(message="Limit", model="gpt-4", retry_after=60)
        assert error.model == "gpt-4"
        assert error.retry_after == 60


class TestMonitorConfig:
    """Tests for MonitorConfig."""

    def test_monitor_config_creation(self):
        """Test MonitorConfig creation."""
        from aura_cli.tui.tools.monitor import MonitorConfig

        config = MonitorConfig()
        assert hasattr(config, "color_mode")


class TestThemes:
    """Tests for themes."""

    def test_theme_colors_creation(self):
        """Test ThemeColors creation."""
        from aura_cli.tui.styles.themes import ThemeColors

        colors = ThemeColors()
        assert colors.background is not None

    def test_nebula_dark_theme(self):
        """Test NEBULA_DARK theme."""
        from aura_cli.tui.styles.themes import NEBULA_DARK

        assert NEBULA_DARK.name == "Nebula Dark"

    def test_theme_css_variables(self):
        """Test theme CSS variables generation."""
        from aura_cli.tui.styles.themes import NEBULA_DARK

        css = NEBULA_DARK.to_css_variables()
        assert ":root" in css


class TestStats:
    """Tests for stats."""

    def test_stats_singleton(self):
        """Test stats is singleton."""
        from aura_cli.core.stats import get_stats

        s1 = get_stats()
        s2 = get_stats()
        assert s1 is s2


class TestThreadManager:
    """Tests for ThreadManager."""

    def test_thread_manager_singleton(self):
        """Test ThreadManager is singleton."""
        from aura_cli.cli.utils.thread_manager import get_thread_manager

        tm1 = get_thread_manager()
        tm2 = get_thread_manager()
        assert tm1 is tm2
