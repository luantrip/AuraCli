"""Tests for management commands module.

Tests for /session, /workflow, /cache command handlers.
"""

from unittest.mock import MagicMock, patch


class TestHandleSession:
    """Tests for handle_session function."""

    def test_session_no_args_shows_help(self):
        """Test session with no args shows help."""
        from aura_cli.cli.commands.management import handle_session

        with patch("aura_cli.cli.commands.management.Console") as mock_console:
            result = handle_session("")

            assert result is None
            mock_console.return_value.print.assert_called()

    def test_session_info_no_state(self):
        """Test session info when no active session."""
        from aura_cli.cli.commands.management import handle_session

        with patch("aura_cli.cli.commands.management.Console"):
            with patch(
                "aura_cli.core.sessions.session_state.get_session_state"
            ) as mock_state:
                mock_state.return_value.get_current_state.return_value = None

                result = handle_session("info")

                assert result is not None
                assert (
                    "nenhuma" in result.lower()
                    or "no active session" in result.lower()
                    or "warning" in result.lower()
                )

    def test_session_info_with_state(self):
        """Test session info with active session."""
        from aura_cli.cli.commands.management import handle_session

        mock_state = MagicMock()
        mock_state.session_id = "test_123"
        mock_state.created_at = "2024-01-01"
        mock_state.history = ["msg1", "msg2"]
        mock_state.active_mode = "normal"

        with patch("aura_cli.cli.commands.management.Console"):
            with patch(
                "aura_cli.core.sessions.session_state.get_session_state"
            ) as mock_get:
                mock_get.return_value.get_current_state.return_value = mock_state

                result = handle_session("info")

                assert result is None  # Prints panel, returns None

    def test_session_list(self):
        """Test session list command."""
        from aura_cli.cli.commands.management import handle_session

        with patch("aura_cli.cli.commands.management.Console"):
            result = handle_session("list")

            assert result is None  # Prints table, returns None

    def test_session_save_no_name(self):
        """Test session save without name."""
        from aura_cli.cli.commands.management import handle_session

        with patch("aura_cli.cli.commands.management.Console"):
            result = handle_session("save")

            assert result is not None
            assert (
                "obrigatório" in result.lower()
                or "required" in result.lower()
                or "erro" in result.lower()
                or "error" in result.lower()
                or "uso" in result.lower()
                or "usage" in result.lower()
            )

    def test_session_save_with_name(self):
        """Test session save without app_loop reports missing context."""
        from aura_cli.cli.commands.management import handle_session

        with patch("aura_cli.cli.commands.management.Console"):
            result = handle_session("save my_session")

            assert result is not None
            # Without app_loop the handler returns an internal error
            assert "erro" in result.lower() or "error" in result.lower()

    def test_session_load_no_name(self):
        """Test session load without name returns usage error."""
        from aura_cli.cli.commands.management import handle_session

        with patch("aura_cli.cli.commands.management.Console"):
            result = handle_session("load")

            assert result is not None
            assert (
                "uso" in result.lower()
                or "usage" in result.lower()
                or "erro" in result.lower()
                or "error" in result.lower()
            )

    def test_session_load_with_name(self):
        """Test session load without app_loop reports missing context."""
        from aura_cli.cli.commands.management import handle_session

        with patch("aura_cli.cli.commands.management.Console"):
            result = handle_session("load my_session")

            assert result is not None
            # Without app_loop the handler returns an internal error
            assert "erro" in result.lower() or "error" in result.lower()

    def test_session_unknown_command(self):
        """Test session with unknown command."""
        from aura_cli.cli.commands.management import handle_session

        with patch("aura_cli.cli.commands.management.Console"):
            result = handle_session("unknown")

            assert result is not None
            assert "unknown" in result.lower()

    def test_session_save_with_app_loop(self, tmp_path):
        """Test session save with real app_loop mock persists conversation history."""
        from aura_cli.cli.commands.management import handle_session

        mock_app_loop = type(
            "AppLoop",
            (),
            {
                "conversation_history": [
                    {"role": "user", "content": "hello"},
                    {"role": "assistant", "content": "hi"},
                ],
                "final_model": "gemini/gemini-2.5-flash",
            },
        )()

        mock_session = type(
            "Session",
            (),
            {
                "id": "abc12345",
                "name": "test_project",
                "conversation_history": [],
                "model": "",
            },
        )()

        mock_manager = type(
            "SM",
            (),
            {
                "create_session": lambda self, name: mock_session,
                "save_session": lambda self, s: None,
            },
        )()

        with patch("aura_cli.cli.commands.management.Console"):
            with patch(
                "aura_cli.core.sessions.session_manager.get_session_manager",
                return_value=mock_manager,
            ):
                result = handle_session("save test_project", app_loop=mock_app_loop)

        assert result is not None
        assert (
            "abc12345" in result
            or "salva" in result.lower()
            or "sucesso" in result.lower()
        )

    def test_session_load_with_app_loop(self):
        """Test session load with real app_loop mock restores conversation history."""
        from aura_cli.cli.commands.management import handle_session

        mock_app_loop = type(
            "AppLoop",
            (),
            {
                "conversation_history": [],
                "final_model": "",
            },
        )()

        mock_session = type(
            "Session",
            (),
            {
                "id": "abc12345",
                "name": "saved",
                "conversation_history": [
                    {"role": "user", "content": "prev message"},
                ],
                "model": "gemini/gemini-2.5-flash",
            },
        )()

        mock_manager = type(
            "SM",
            (),
            {
                "load_session": lambda self, sid: mock_session,
                "list_sessions": lambda self: [mock_session],
            },
        )()

        with patch("aura_cli.cli.commands.management.Console"):
            with patch(
                "aura_cli.core.sessions.session_manager.get_session_manager",
                return_value=mock_manager,
            ):
                result = handle_session("load abc12345", app_loop=mock_app_loop)

        assert result is not None
        assert "abc12345" in result or "carregada" in result.lower()
        assert len(mock_app_loop.conversation_history) == 1

    def test_resume_alias_loads_session_reference(self):
        """The concise resume command delegates to session loading."""
        from aura_cli.cli.commands.management import handle_resume

        mock_app_loop = type(
            "AppLoop",
            (),
            {
                "conversation_history": [],
                "final_model": "",
            },
        )()
        mock_session = type(
            "Session",
            (),
            {
                "id": "resume123",
                "name": "restored",
                "conversation_history": [{"role": "user", "content": "continue"}],
                "model": "gpt-test",
            },
        )()
        mock_manager = type(
            "SM",
            (),
            {
                "load_session": lambda self, sid: mock_session
                if sid == "resume123"
                else None,
                "list_sessions": lambda self: [mock_session],
            },
        )()

        with patch("aura_cli.cli.commands.management.Console"):
            with patch(
                "aura_cli.core.sessions.session_manager.get_session_manager",
                return_value=mock_manager,
            ):
                result = handle_resume("resume123", app_loop=mock_app_loop)

        assert result is not None
        assert "restored" in result
        assert mock_app_loop.conversation_history == mock_session.conversation_history


class TestHandleWorkflow:
    """Tests for handle_workflow function."""

    def test_workflow_no_args_shows_help(self):
        """Test workflow with no args shows help."""
        from aura_cli.cli.commands.management import handle_workflow

        with patch("aura_cli.cli.commands.management.Console") as mock_console:
            with patch("aura_cli.cli.commands.management.UIIcons") as mock_icons:
                mock_icons.WORKFLOW = "🔄"
                result = handle_workflow("")

                assert result is None
                mock_console.return_value.print.assert_called()

    def test_workflow_list(self):
        """Test workflow list command."""
        from aura_cli.cli.commands.management import handle_workflow

        with patch("aura_cli.cli.commands.management.Console"):
            result = handle_workflow("list")

            assert result is None

    def test_workflow_run_no_name(self):
        """Test workflow run without name."""
        from aura_cli.cli.commands.management import handle_workflow

        with patch("aura_cli.cli.commands.management.Console"):
            result = handle_workflow("run")

            assert result is not None
            assert (
                "obrigatório" in result.lower()
                or "required" in result.lower()
                or "erro" in result.lower()
                or "error" in result.lower()
                or "uso" in result.lower()
                or "usage" in result.lower()
            )

    def test_workflow_run_with_name(self):
        """Test workflow run with name."""
        from aura_cli.cli.commands.management import handle_workflow

        with patch("aura_cli.cli.commands.management.Console"):
            with patch("aura_cli.cli.commands.management.UIStyles") as mock_styles:
                with patch("aura_cli.cli.commands.management.UIIcons") as mock_icons:
                    mock_styles.WORKING = "yellow"
                    mock_icons.WORKING = "⚙️"

                    result = handle_workflow("run my_workflow")

                    assert result is not None
                    assert "my_workflow" in result

    def test_workflow_unknown_command(self):
        """Test workflow with unknown command."""
        from aura_cli.cli.commands.management import handle_workflow

        with patch("aura_cli.cli.commands.management.Console"):
            result = handle_workflow("unknown")

            assert result is not None
            assert "unknown" in result.lower()


class TestHandleCache:
    """Tests for handle_cache function."""

    def test_cache_no_args_shows_help(self):
        """Test cache with no args shows help."""
        from aura_cli.cli.commands.management import handle_cache

        with patch("aura_cli.cli.commands.management.Console") as mock_console:
            result = handle_cache("")

            assert result is None
            mock_console.return_value.print.assert_called()

    def test_cache_stats(self):
        """Test cache stats command."""
        from aura_cli.cli.commands.management import handle_cache

        with patch("aura_cli.cli.commands.management.Console"):
            result = handle_cache("stats")

            assert result is None  # Prints panel, returns None

    def test_cache_clear(self):
        """Test cache clear command."""
        from aura_cli.cli.commands.management import handle_cache

        with patch("aura_cli.cli.commands.management.Console"):
            result = handle_cache("clear")

            assert result is not None
            assert (
                "limpo" in result.lower()
                or "cleared" in result.lower()
                or "success" in result.lower()
            )

    def test_cache_unknown_command(self):
        """Test cache with unknown command."""
        from aura_cli.cli.commands.management import handle_cache

        with patch("aura_cli.cli.commands.management.Console"):
            result = handle_cache("unknown")

            assert result is not None
            assert "unknown" in result.lower()
