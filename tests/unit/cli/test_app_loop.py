"""Tests for AppLoop - Main application loop.

Tests verify proper initialization, command processing, and shutdown.
"""

import asyncio
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from aura_cli.cli.app_loop import AppLoop
from tests.runtime_helpers import make_runtime_services


class TestAppLoop:
    """Test suite for AppLoop."""

    def test_initialization(self):
        """Test AppLoop initialization."""
        # Setup mocks

        mock_ui = Mock()
        mock_stats = Mock()
        mock_console = Mock()
        mock_context = Mock()
        mock_tools = {}

        app_loop = AppLoop(
            ui=mock_ui,
            stats=mock_stats,
            console=mock_console,
            conversation_history=[],
            context_manager=mock_context,
            available_tools=mock_tools,
            initial_model="auto",
            project_root=Path.cwd(),
            runtime_services=make_runtime_services(Path.cwd()),
        )

        assert app_loop.ui == mock_ui
        assert app_loop.stats == mock_stats
        assert app_loop.console == mock_console
        assert app_loop.final_model == "auto"
        assert app_loop.agi_thread is None
        assert app_loop.ops_thread is None

    @patch("aura_cli.cli.app_loop.set_allowed_base_dir")
    def test_workspace_root_is_canonical_and_sets_path_boundary(
        self, mock_set_allowed_base_dir, tmp_path
    ):
        workspace = tmp_path / "workspace"
        workspace.mkdir()
        runtime = make_runtime_services(workspace)

        app_loop = AppLoop(
            ui=Mock(),
            stats=Mock(),
            console=Mock(),
            conversation_history=[],
            context_manager=Mock(),
            available_tools={},
            initial_model="auto",
            project_root=workspace / ".",
            runtime_services=runtime,
        )

        assert app_loop.project_root == workspace.resolve()
        mock_set_allowed_base_dir.assert_called_once_with(str(workspace.resolve()))

    def test_set_shutdown_event(self):
        """Test setting shutdown event."""
        import threading

        # Setup mocks

        app_loop = AppLoop(
            ui=Mock(),
            stats=Mock(),
            console=Mock(),
            conversation_history=[],
            context_manager=Mock(),
            available_tools={},
            initial_model="auto",
            project_root=Path.cwd(),
            runtime_services=make_runtime_services(Path.cwd()),
        )

        event = threading.Event()
        app_loop.set_shutdown_event(event)

        assert app_loop.shutdown_event == event

    @patch("aura_cli.cli.session_lifecycle.get_background_process_supervisor")
    @patch("aura_cli.cli.session_lifecycle.get_thread_manager")
    def test_shutdown_cancels_registered_backgrounds(
        self, mock_thread_manager, mock_background_supervisor
    ):
        mock_manager = Mock()
        mock_manager.stop_all.return_value = {"test_thread": True}
        mock_thread_manager.return_value = mock_manager
        background = Mock()
        background.cancel_all.return_value = [Mock(pid=77, status="cancelled")]
        mock_background_supervisor.return_value = background

        app_loop = AppLoop(
            ui=Mock(),
            stats=Mock(),
            console=Mock(),
            conversation_history=[],
            context_manager=Mock(),
            available_tools={},
            initial_model="auto",
            project_root=Path.cwd(),
            runtime_services=make_runtime_services(Path.cwd()),
        )

        result = app_loop.shutdown(timeout=10.0)

        assert result is True
        background.cancel_all.assert_called_once_with()

    @patch("aura_cli.cli.session_lifecycle.get_background_process_supervisor")
    @patch("aura_cli.cli.session_lifecycle.get_thread_manager")
    def test_shutdown_accepts_already_terminal_backgrounds(
        self, mock_thread_manager, mock_background_supervisor
    ):
        mock_manager = Mock()
        mock_manager.stop_all.return_value = {}
        mock_thread_manager.return_value = mock_manager
        background = Mock()
        background.cancel_all.return_value = [
            Mock(pid=1, status="completed"),
            Mock(pid=2, status="failed"),
        ]
        mock_background_supervisor.return_value = background

        app_loop = AppLoop(
            ui=Mock(),
            stats=Mock(),
            console=Mock(),
            conversation_history=[],
            context_manager=Mock(),
            available_tools={},
            initial_model="auto",
            project_root=Path.cwd(),
            runtime_services=make_runtime_services(Path.cwd()),
        )

        assert app_loop.shutdown(timeout=1.0) is True

    @patch("aura_cli.cli.session_lifecycle.get_thread_manager")
    def test_shutdown(self, mock_thread_manager):
        """Test graceful shutdown."""
        # Setup mocks

        # Setup mocks

        mock_manager = Mock()
        # stop_all returns dict with thread names and success status
        # All threads must return True for shutdown to succeed
        mock_manager.stop_all.return_value = {
            "test_thread": True,
            "agi_thread": True,
            "ops_thread": True,
        }
        mock_thread_manager.return_value = mock_manager

        app_loop = AppLoop(
            ui=Mock(),
            stats=Mock(),
            console=Mock(),
            conversation_history=[],
            context_manager=Mock(),
            available_tools={},
            initial_model="auto",
            project_root=Path.cwd(),
            runtime_services=make_runtime_services(Path.cwd()),
        )

        # Set shutdown event
        import threading

        app_loop.shutdown_event = threading.Event()

        # Mock legacy threads (not alive, so they won't block)
        mock_agi_thread = Mock()
        mock_agi_thread.name = "agi_thread"
        mock_agi_thread.is_alive.return_value = False  # Thread already stopped
        app_loop.agi_thread = mock_agi_thread

        mock_ops_thread = Mock()
        mock_ops_thread.name = "ops_thread"
        mock_ops_thread.is_alive.return_value = False  # Thread already stopped
        app_loop.ops_thread = mock_ops_thread

        result = app_loop.shutdown(timeout=10.0)

        assert result is True
        mock_manager.stop_all.assert_called()

    @patch("aura_cli.cli.command_handler.route_command")
    @patch("aura_cli.cli.llm_handler.process_function_calls_loop")
    @patch("aura_cli.cli.command_handler.asyncio.run")
    def test_process_command_single_shot(
        self, mock_asyncio_run, mock_process_function, mock_route
    ):
        """Test processing single command."""
        # Mock route_command to return llm_query
        mock_route.return_value = (True, "llm_query", None, None, None)
        # Mock process_function_calls_loop to avoid LLM calls
        mock_process_function.return_value = ("response", Mock())
        # Mock asyncio.run to avoid actual async execution
        mock_asyncio_run.return_value = None

        # Setup mocks

        # Create proper mock for stats with iterable lists
        mock_stats = Mock()
        mock_stats.get_files_changed.return_value = False
        mock_stats._files_created_list = []
        mock_stats._files_edited_list = []
        mock_stats._files_read_list = []
        mock_stats.set_status = Mock()

        app_loop = AppLoop(
            ui=Mock(),
            stats=mock_stats,
            console=Mock(),
            conversation_history=[],
            context_manager=Mock(),
            available_tools={},
            initial_model="auto",
            project_root=Path.cwd(),
            runtime_services=make_runtime_services(Path.cwd()),
        )

        result = app_loop.process_command_single_shot("test command")

        assert result is True
        mock_route.assert_called_once()

    @patch("aura_cli.cli.command_handler.route_command")
    def test_process_command_exit(self, mock_route):
        """Test processing command that exits."""
        # Setup mocks

        mock_route.return_value = (False, None, None, None, None)

        app_loop = AppLoop(
            ui=Mock(),
            stats=Mock(),
            console=Mock(),
            conversation_history=[],
            context_manager=Mock(),
            available_tools={},
            initial_model="auto",
            project_root=Path.cwd(),
            runtime_services=make_runtime_services(Path.cwd()),
        )

        result = app_loop.process_command_single_shot("/exit")

        assert result is False

    def test_shutdown_with_event(self):
        """Test shutdown sets event."""
        import threading

        # Setup mocks

        app_loop = AppLoop(
            ui=Mock(),
            stats=Mock(),
            console=Mock(),
            conversation_history=[],
            context_manager=Mock(),
            available_tools={},
            initial_model="auto",
            project_root=Path.cwd(),
            runtime_services=make_runtime_services(Path.cwd()),
        )

        event = threading.Event()
        app_loop.set_shutdown_event(event)

        with patch("aura_cli.cli.session_lifecycle.get_thread_manager") as mock_tm:
            mock_manager = Mock()
            mock_manager.stop_all.return_value = {"test_thread": True}
            mock_tm.return_value = mock_manager

            app_loop.shutdown()

            assert event.is_set()

    @patch("aura_cli.cli.session_lifecycle.notebook_service")
    def test_save_context_to_notebook_preserves_base_system_messages(
        self, mock_notebook_service, tmp_path
    ):
        """Notebook compaction must preserve the base system prompts."""
        page = tmp_path / "notebook" / "page-1"
        page.parent.mkdir()
        page.write_text("saved context", encoding="utf-8")
        mock_notebook_service.create_snapshot.return_value = str(page)

        history = [
            {"role": "system", "content": "base system"},
            {"role": "system", "content": "runtime note"},
            {"role": "user", "content": "hello"},
            {"role": "assistant", "content": "world"},
        ]
        stats = Mock()
        app_loop = AppLoop(
            ui=Mock(),
            stats=stats,
            console=Mock(),
            conversation_history=history,
            context_manager=Mock(),
            available_tools={},
            initial_model="auto",
            project_root=Path.cwd(),
            runtime_services=make_runtime_services(Path.cwd()),
        )

        app_loop._save_context_to_notebook()

        assert app_loop.conversation_history[0]["content"] == "base system"
        assert app_loop.conversation_history[1]["content"] == "runtime note"
        assert "caderno de memória" in app_loop.conversation_history[2]["content"]
        stats.increment_notebook_snapshots.assert_called_once()

    def test_conversation_with_consciousness_skills_returns_copy_without_skills(self):
        """The LLM payload builder should never return the live history list."""

        history = [
            {"role": "system", "content": "base system"},
            {"role": "user", "content": "hello"},
        ]
        app_loop = AppLoop(
            ui=Mock(),
            stats=Mock(),
            console=Mock(),
            conversation_history=history,
            context_manager=Mock(),
            available_tools={},
            initial_model="auto",
            project_root=Path.cwd(),
            runtime_services=make_runtime_services(Path.cwd()),
        )

        with patch(
            "aura_cli.core.personas.integrations.get_consciousness_manager"
        ) as mock_manager:
            mock_manager.return_value.get_skills_section.return_value = ""
            result = app_loop._conversation_with_consciousness_skills("hello")

        assert result == history
        assert result is not app_loop.conversation_history

    @patch("aura_cli.cli.llm_handler.process_function_calls_loop")
    @patch("aura_cli.cli.ui.presenter.AppPresenter.display_llm_response")
    @patch("aura_cli.cli.ui.presenter.AppPresenter.display_status_footer")
    def test_process_llm_query_keeps_original_user_message_in_history(
        self, mock_footer, mock_display, mock_process_loop
    ):
        """Prompt expansion should happen only in the transient LLM payload."""
        mock_process_loop.return_value = ("done", Mock())

        stats = Mock()
        stats._pending_context = "FILE CONTEXT"
        stats._pending_context_files = 1
        stats.tokens_used = 0
        from rich.console import Console as RichConsole

        console = RichConsole(quiet=True)
        console.status = Mock()
        console.status.return_value.__enter__ = Mock(return_value=None)
        console.status.return_value.__exit__ = Mock(return_value=None)
        app_loop = AppLoop(
            ui=Mock(),
            stats=stats,
            console=console,
            conversation_history=[
                {"role": "system", "content": "base system"},
                {"role": "system", "content": "runtime note"},
            ],
            context_manager=Mock(),
            available_tools={},
            initial_model="auto",
            project_root=Path.cwd(),
            runtime_services=make_runtime_services(Path.cwd()),
        )
        app_loop.constitution = "Always test"

        asyncio.run(app_loop._process_llm_query("Build login"))

        assert app_loop.conversation_history[-2]["role"] == "user"
        assert app_loop.conversation_history[-2]["content"] == "Build login"

        sent_history = mock_process_loop.call_args.kwargs["conversation_history"]
        assert sent_history[-1]["content"] != "Build login"
        assert "Always test" in sent_history[-1]["content"]
        assert "FILE CONTEXT" in sent_history[-1]["content"]
        assert stats._pending_context is None
        assert stats._pending_context_files == 0

    @patch("aura_cli.cli.llm_handler.process_function_calls_loop")
    def test_process_llm_query_keeps_pending_context_on_failure(
        self, mock_process_loop
    ):
        """Pending file context should survive a failed LLM roundtrip."""
        mock_process_loop.side_effect = RuntimeError("network down")

        stats = Mock()
        stats._pending_context = "FILE CONTEXT"
        stats._pending_context_files = 2
        stats.tokens_used = 0
        console = Mock()
        console.status.return_value.__enter__ = Mock(return_value=None)
        console.status.return_value.__exit__ = Mock(return_value=None)
        app_loop = AppLoop(
            ui=Mock(),
            stats=stats,
            console=console,
            conversation_history=[
                {"role": "system", "content": "base system"},
            ],
            context_manager=Mock(),
            available_tools={},
            initial_model="auto",
            project_root=Path.cwd(),
            runtime_services=make_runtime_services(Path.cwd()),
        )

        with pytest.raises(RuntimeError):
            asyncio.run(app_loop._process_llm_query("Build login"))

        assert stats._pending_context == "FILE CONTEXT"
        assert stats._pending_context_files == 2
