"""Deep functional tests for core modules.

These tests exercise actual code paths to increase coverage.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch


class TestFileSystemToolsDeep:
    """Deep tests for file system tools."""

    def test_read_file_various_encodings(self, tmp_path):
        """Test reading files with various encodings."""
        from aura_cli.core.tools.file_system import enable_path_validation, read_file

        enable_path_validation(False)

        # UTF-8
        utf8_file = tmp_path / "utf8.txt"
        utf8_file.write_text("Hello 世界 🌍", encoding="utf-8")
        result = read_file(str(utf8_file))
        assert "Hello" in result


    def test_write_file_with_special_chars(self, tmp_path, monkeypatch):
        """Test writing file with special characters."""
        import aura_cli.core.tools.file_system as fs_module
        from aura_cli.core.tools.file_system import enable_path_validation, write_file

        enable_path_validation(False)
        monkeypatch.setattr(fs_module, "AUTO_CONFIRM_TOOLS", True)

        test_file = tmp_path / "special.txt"
        content = "Special chars: © ® ™ € £ ¥"
        write_file(str(test_file), content)

        assert test_file.read_text() == content

    def test_list_directory_with_hidden(self, tmp_path):
        """Test listing directory with hidden files."""
        from aura_cli.core.tools.file_system import (
            enable_path_validation,
            list_directory,
        )

        enable_path_validation(False)

        (tmp_path / ".hidden").write_text("hidden")
        (tmp_path / "visible.txt").write_text("visible")

        result = list_directory(str(tmp_path))
        assert "visible.txt" in result

    def test_list_directory_nested(self, tmp_path):
        """Test listing nested directories."""
        from aura_cli.core.tools.file_system import (
            enable_path_validation,
            list_directory,
        )

        enable_path_validation(False)

        (tmp_path / "a" / "b" / "c").mkdir(parents=True)
        (tmp_path / "a" / "file.txt").write_text("content")

        result = list_directory(str(tmp_path))
        assert "a" in result


class TestDevToolsDeep:
    """Deep tests for dev tools."""


class TestSessionStateDeep:
    """Deep tests for session state."""

    def test_session_state_full_lifecycle(self, tmp_path):
        """Test full session lifecycle."""
        from aura_cli.core.sessions.session_state import (
            SessionStateManager,
        )

        # Reset singleton
        SessionStateManager._instance = None
        manager = SessionStateManager.get_instance()

        with patch(
            "aura_cli.core.sessions.session_state.get_memory_service"
        ) as mock_mem:
            mock_mem.return_value = MagicMock(
                get_constitution=MagicMock(return_value="Test constitution"),
                get_learned_rules=MagicMock(return_value=[]),
                save_constitution=MagicMock(return_value=True),
                add_learned_rule=MagicMock(return_value=True),
            )

            # Initialize
            state = manager.initialize(tmp_path)
            assert state.session_id.startswith("session_")

            # Get constitution
            const = manager.get_constitution()
            assert const == "Test constitution"

            # Set mode
            manager.set_active_mode("agi")
            assert manager.is_agi_mode()

            # Add context file
            manager.add_context_file("test.py")
            files = manager.get_context_files()
            assert "test.py" in files

    def test_session_state_to_dict_complete(self):
        """Test SessionState to_dict with all fields."""
        from aura_cli.core.memory.memory_service import LearnedRule
        from aura_cli.core.sessions.session_state import SessionState

        rule = LearnedRule(rule="test rule", context="test", source="agi")

        state = SessionState(
            session_id="test-123",
            constitution="Test constitution content here",
            project_stage="mvp",
            learned_rules=[rule],
            context_files=["file1.py", "file2.py"],
            active_mode="agi",
        )

        data = state.to_dict()

        assert data["session_id"] == "test-123"
        assert data["has_constitution"] is True
        assert data["project_stage"] == "mvp"
        assert data["learned_rules_count"] == 1
        assert len(data["context_files"]) == 2
        assert data["active_mode"] == "agi"


class TestMemoryServiceDeep:
    """Deep tests for memory service."""

    def test_memory_service_learned_rules_lifecycle(self, tmp_path):
        """Test learned rules full lifecycle."""
        from aura_cli.core.memory.memory_service import MemoryService

        with patch.object(Path, "home", return_value=tmp_path):
            service = MemoryService(tmp_path / "project")

            # Add rules
            service.add_learned_rule("Rule 1", "context1", "agi")
            service.add_learned_rule("Rule 2", "context2", "ops")

            # Get rules
            rules = service.get_learned_rules()
            assert len(rules) == 2

            # Clear
            service.clear_scratchpad()
            rules = service.get_learned_rules()
            assert len(rules) == 0


class TestLearnedRuleDeep:
    """Deep tests for LearnedRule."""

    def test_learned_rule_serialization_roundtrip(self):
        """Test LearnedRule serialization roundtrip."""
        from aura_cli.core.memory.memory_service import LearnedRule

        original = LearnedRule(
            rule="Always write tests", context="coding session", source="manual"
        )

        # To dict
        data = original.to_dict()

        # From dict
        restored = LearnedRule.from_dict(data)

        assert restored.rule == original.rule
        assert restored.context == original.context
        assert restored.source == original.source


class TestStatsTrackerDeep:
    """Deep tests for StatsTracker."""

    def test_stats_token_tracking(self):
        """Test token tracking functionality."""
        from aura_cli.core.stats import get_stats

        stats = get_stats()
        initial = stats.total_tokens

        # Add tokens multiple times
        stats.add_tokens(
            {"total_tokens": 100, "prompt_tokens": 60, "completion_tokens": 40}
        )
        stats.add_tokens(
            {"total_tokens": 50, "prompt_tokens": 30, "completion_tokens": 20}
        )

        assert stats.total_tokens >= initial + 150

    def test_stats_skip_confirmations_toggle(self):
        """Test skip confirmations toggle."""
        from aura_cli.core.stats import get_stats

        stats = get_stats()

        # Get initial state
        initial = stats.skip_confirmations

        # Toggle
        stats.toggle_skip_confirmations()
        assert stats.skip_confirmations != initial

        # Toggle back
        stats.toggle_skip_confirmations()
        assert stats.skip_confirmations == initial


class TestConfigManagerDeep:
    """Deep tests for ConfigManager."""


class TestExceptionsDeep:
    """Deep tests for exceptions."""

    def test_rate_limit_error_full(self):
        """Test RateLimitError with all fields."""
        from aura_cli.cli.utils.exceptions import RateLimitError

        error = RateLimitError(
            message="Rate limit exceeded for gpt-4",
            model="gpt-4-turbo",
            retry_after=120,
        )

        assert error.model == "gpt-4-turbo"
        assert error.retry_after == 120
        assert "gpt-4" in str(error)


class TestHelpersDeep:
    """Deep tests for CLI helpers."""

    def test_parse_agi_command_variations(self):
        """Test parsing various /agi command formats."""
        from aura_cli.cli.helpers import parse_agi_command

        # With objective
        assert parse_agi_command("/agi create API") == "create API"

        # With extra spaces
        result = parse_agi_command("/agi   build a website   ")
        assert "build a website" in result.strip()

        # Empty
        result = parse_agi_command("/agi")
        assert len(result) > 0  # Default objective

    def test_parse_ops_command_variations(self):
        """Test parsing various /ops command formats."""
        from aura_cli.cli.helpers import parse_ops_command

        # Git mode
        mode, _task = parse_ops_command("/ops git status")
        assert mode == "git"

        # Docker mode
        mode, _task = parse_ops_command("/ops docker ps -a")
        assert mode == "docker"

        # General mode
        mode, _task = parse_ops_command("/ops analyze system")
        assert mode == "general"

    def test_initialize_conversation_history_structure(self):
        """Test conversation history structure."""
        from aura_cli.cli.helpers import initialize_conversation_history

        history = initialize_conversation_history()

        assert len(history) == 1
        assert history[0]["role"] == "system"
        assert (
            "ferramentas" in history[0]["content"].lower()
            or "tools" in history[0]["content"].lower()
        )


class TestCommandRouterDeep:
    """Deep tests for command router."""

    def test_route_various_commands(self):
        """Test routing various command types."""
        from unittest.mock import MagicMock

        from aura_cli.cli.command_router import route_command

        mock_ui = MagicMock()
        mock_ui.status_queue = MagicMock()
        mock_stats = MagicMock()
        mock_console = MagicMock()

        # Test LLM query (non-command text)
        with patch(
            "aura_cli.cli.command_router.should_execute_directly", return_value=False
        ):
            result = route_command(
                "What is Python?",
                None,
                None,
                "gpt-4",
                mock_stats,
                mock_ui,
                mock_console,
            )
            assert result[1] == "llm_query"


class TestThemesDeep:
    """Deep tests for themes."""

    def test_all_themes_have_required_colors(self):
        """Test all themes have required colors."""
        from aura_cli.tui.styles.themes import NEBULA_DARK, NEBULA_LIGHT

        required_attrs = ["background", "foreground", "primary", "secondary"]

        for theme in [NEBULA_DARK, NEBULA_LIGHT]:
            for attr in required_attrs:
                assert hasattr(theme.colors, attr), f"Theme {theme.name} missing {attr}"

    def test_theme_css_generation(self):
        """Test CSS generation from theme."""
        from aura_cli.tui.styles.themes import NEBULA_DARK

        css = NEBULA_DARK.to_css_variables()

        assert ":root" in css
        assert "--" in css or "$" in css  # CSS variable syntax
