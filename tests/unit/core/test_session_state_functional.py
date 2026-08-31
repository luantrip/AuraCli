"""Functional tests for session state module.

Tests for actual functionality of session state management.
"""

from unittest.mock import MagicMock, patch


class TestSessionState:
    """Tests for SessionState dataclass."""

    def test_session_state_creation(self):
        """Test creating SessionState."""
        from aura_cli.core.sessions.session_state import SessionState

        state = SessionState(session_id="test-123")

        assert state.session_id == "test-123"
        assert state.constitution is None
        assert state.active_mode == "normal"
        assert isinstance(state.learned_rules, list)

    def test_session_state_with_constitution(self):
        """Test SessionState with constitution."""
        from aura_cli.core.sessions.session_state import SessionState

        state = SessionState(session_id="test-123", constitution="Project rules here")

        assert state.has_constitution() is True
        assert state.constitution == "Project rules here"


    def test_session_state_to_dict(self):
        """Test SessionState serialization."""
        from aura_cli.core.sessions.session_state import SessionState

        state = SessionState(
            session_id="test-123",
            constitution="Some rules",
            project_stage="mvp",
            active_mode="agi",
        )

        data = state.to_dict()

        assert data["session_id"] == "test-123"
        assert data["has_constitution"] is True
        assert data["project_stage"] == "mvp"
        assert data["active_mode"] == "agi"

    def test_session_state_validate_prompt_no_validator(self):
        """Test prompt validation without validator."""
        from aura_cli.core.sessions.session_state import SessionState

        state = SessionState(session_id="test")

        is_valid, violations, sanitized = state.validate_prompt("Test prompt")

        assert is_valid is True
        assert violations == []
        assert sanitized is None


class TestSessionStateManager:
    """Tests for SessionStateManager class."""

    def test_get_instance_singleton(self):
        """Test that get_instance returns singleton."""
        from aura_cli.core.sessions.session_state import SessionStateManager

        # Reset singleton for test
        SessionStateManager._instance = None

        manager1 = SessionStateManager.get_instance()
        manager2 = SessionStateManager.get_instance()

        assert manager1 is manager2

    def test_initialize_creates_state(self, tmp_path):
        """Test initialize creates session state."""
        from aura_cli.core.sessions.session_state import SessionStateManager

        # Reset singleton
        SessionStateManager._instance = None

        manager = SessionStateManager.get_instance()

        # Mock memory service
        with patch(
            "aura_cli.core.sessions.session_state.get_memory_service"
        ) as mock_mem:
            mock_mem.return_value = MagicMock(
                get_constitution=MagicMock(return_value=None),
                get_learned_rules=MagicMock(return_value=[]),
            )

            state = manager.initialize(tmp_path)

            assert state is not None
            assert state.session_id.startswith("session_")
            assert manager.is_initialized() is True


    def test_set_active_mode_valid(self, tmp_path):
        """Test setting valid active mode."""
        from aura_cli.core.sessions.session_state import SessionStateManager

        # Reset singleton
        SessionStateManager._instance = None

        manager = SessionStateManager.get_instance()

        with patch(
            "aura_cli.core.sessions.session_state.get_memory_service"
        ) as mock_mem:
            mock_mem.return_value = MagicMock(
                get_constitution=MagicMock(return_value=None),
                get_learned_rules=MagicMock(return_value=[]),
            )

            manager.initialize(tmp_path)
            manager.set_active_mode("agi")

            assert manager.get_active_mode() == "agi"
            assert manager.is_agi_mode() is True
            assert manager.is_ops_mode() is False


    def test_set_active_mode_invalid(self, tmp_path):
        """Test setting invalid active mode."""
        from aura_cli.core.sessions.session_state import SessionStateManager

        # Reset singleton
        SessionStateManager._instance = None

        manager = SessionStateManager.get_instance()

        with patch(
            "aura_cli.core.sessions.session_state.get_memory_service"
        ) as mock_mem:
            mock_mem.return_value = MagicMock(
                get_constitution=MagicMock(return_value=None),
                get_learned_rules=MagicMock(return_value=[]),
            )

            manager.initialize(tmp_path)
            manager.set_active_mode("invalid_mode")

            # Should remain normal
            assert manager.get_active_mode() == "normal"

    def test_update_constitution(self, tmp_path):
        """Test updating constitution."""
        from aura_cli.core.sessions.session_state import SessionStateManager

        # Reset singleton
        SessionStateManager._instance = None

        manager = SessionStateManager.get_instance()

        mock_mem_service = MagicMock(
            get_constitution=MagicMock(return_value=None),
            get_learned_rules=MagicMock(return_value=[]),
            save_constitution=MagicMock(return_value=True),
        )

        with patch(
            "aura_cli.core.sessions.session_state.get_memory_service"
        ) as mock_mem:
            mock_mem.return_value = mock_mem_service

            manager.initialize(tmp_path)
            result = manager.update_constitution("New constitution content")

            assert result is True
            mock_mem_service.save_constitution.assert_called_once_with(
                "New constitution content"
            )


    def test_add_context_file(self, tmp_path):
        """Test adding context file."""
        from aura_cli.core.sessions.session_state import SessionStateManager

        # Reset singleton
        SessionStateManager._instance = None

        manager = SessionStateManager.get_instance()

        with patch(
            "aura_cli.core.sessions.session_state.get_memory_service"
        ) as mock_mem:
            mock_mem.return_value = MagicMock(
                get_constitution=MagicMock(return_value=None),
                get_learned_rules=MagicMock(return_value=[]),
            )

            manager.initialize(tmp_path)
            manager.add_context_file("src/main.py")

            files = manager.get_context_files()
            assert "src/main.py" in files


    def test_extract_project_stage_mvp(self, tmp_path):
        """Test extracting MVP project stage."""
        from aura_cli.core.sessions.session_state import SessionStateManager

        # Reset singleton
        SessionStateManager._instance = None

        manager = SessionStateManager.get_instance()

        constitution = "Este projeto está na fase MVP. Priorize velocidade."
        stage = manager._extract_project_stage(constitution)

        assert stage is not None
        assert "mvp" in stage.lower()

    def test_extract_project_stage_production(self, tmp_path):
        """Test extracting production project stage."""
        from aura_cli.core.sessions.session_state import SessionStateManager

        # Reset singleton
        SessionStateManager._instance = None

        manager = SessionStateManager.get_instance()

        constitution = "Este projeto está em produção estável. Priorize estabilidade."
        stage = manager._extract_project_stage(constitution)

        assert stage is not None
        assert "produção" in stage.lower()


class TestModuleFunctions:
    """Tests for module-level functions."""


