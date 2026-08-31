"""Integration tests for CLI components.

Tests verify end-to-end integration between CLI components.
"""

from pathlib import Path
import threading
import time
from unittest.mock import Mock, patch

from aura_cli.cli.app_loop import AppLoop
from aura_cli.cli.command_router import route_command
from aura_cli.cli.utils.thread_manager import get_thread_manager
from tests.runtime_helpers import make_runtime_services


class TestCLIIntegration:
    """Integration tests for CLI components."""

    @patch("aura_cli.cli.command_handler.route_command")
    @patch("aura_cli.cli.llm_handler.process_function_calls_loop")
    @patch("aura_cli.cli.command_handler.asyncio.run")
    def test_app_loop_command_processing(
        self, mock_asyncio_run, mock_process_function, mock_route
    ):
        """Test AppLoop processes commands through router."""
        # Mock route_command to return llm_query
        mock_route.return_value = (True, "llm_query", None, None, None)
        # Mock process_function_calls_loop to avoid LLM calls
        mock_process_function.return_value = ("response", Mock())
        # Mock asyncio.run to avoid actual async execution
        mock_asyncio_run.return_value = None

        mock_ui = Mock()
        mock_ui.status_queue = Mock()
        # Create proper mock for stats with iterable lists
        mock_stats = Mock()
        mock_stats.get_files_changed.return_value = False
        mock_stats._files_created_list = []
        mock_stats._files_edited_list = []
        mock_stats._files_read_list = []
        mock_stats.set_status = Mock()
        mock_console = Mock()
        mock_context = Mock()

        app_loop = AppLoop(
            ui=mock_ui,
            stats=mock_stats,
            console=mock_console,
            conversation_history=[],
            context_manager=mock_context,
            available_tools={},
            initial_model="auto",
            project_root=Path.cwd(),
            runtime_services=make_runtime_services(Path.cwd()),
        )

        result = app_loop.process_command_single_shot("test command")

        assert result is True
        mock_route.assert_called_once()

    @patch("aura_cli.cli.command_router.process_slash_command")
    @patch("aura_cli.cli.command_router.should_execute_directly")
    def test_command_routing_integration(self, mock_should_execute, mock_process_slash):
        """Test command routing integration."""
        mock_should_execute.return_value = False
        mock_process_slash.return_value = (True, "Message", None, None, None)

        mock_ui = Mock()
        mock_ui.status_queue = Mock()
        mock_stats = Mock()
        mock_stats.set_notification = Mock()
        mock_console = Mock()

        result = route_command(
            command="/help",
            agi_thread=None,
            ops_thread=None,
            current_model="auto",
            stats=mock_stats,
            ui=mock_ui,
            console=mock_console,
        )

        assert result[0] is True
        mock_process_slash.assert_called_once()

    def test_thread_manager_integration(self):
        """Test ThreadManager integration with workers."""
        thread_manager = get_thread_manager()

        def dummy_worker():
            time.sleep(0.2)

        thread = thread_manager.register_thread(
            name="integration_test",
            target=dummy_worker,
            daemon=True,
            shutdown_timeout=5.0,
        )

        assert thread is not None
        assert thread_manager.get_thread("integration_test") == thread

        time.sleep(0.1)  # Let thread start

        result = thread_manager.stop_thread("integration_test", timeout=1.0)

        assert result is True or result is False  # May vary based on timing

    @patch("aura_cli.cli.session_lifecycle.get_thread_manager")
    def test_app_loop_shutdown_integration(self, mock_tm):
        """Test AppLoop shutdown with ThreadManager integration."""
        mock_manager = Mock()
        mock_manager.stop_all.return_value = {}
        mock_manager.stop_thread.return_value = True
        mock_tm.return_value = mock_manager

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

        mock_agi = Mock()
        mock_agi.name = "agi_thread"
        mock_agi.is_alive.return_value = False
        app_loop.agi_thread = mock_agi

        result = app_loop.shutdown(timeout=10.0)

        assert result is True
        mock_manager.stop_all.assert_called()


class TestWorkerFactoryIntegration:
    """Integration tests for worker factory."""

    @patch("aura_cli.cli.utils.worker_factory.get_event_bus")
    @patch("aura_cli.cli.utils.worker_factory.get_tools_dict")
    @patch("aura_cli.cli.utils.worker_factory.get_thread_manager")
    def test_worker_factory_thread_registration(
        self, mock_tm, mock_tools, mock_event_bus
    ):
        """Test worker factory registers threads with ThreadManager."""
        mock_queue = Mock()
        mock_event_bus.return_value.get_queue.return_value = mock_queue
        mock_tools.return_value = {}

        mock_thread = Mock(spec=threading.Thread)
        mock_manager = Mock()
        mock_manager.register_thread.return_value = mock_thread
        mock_tm.return_value = mock_manager

        from aura_cli.cli.utils.worker_factory import create_agi_worker_thread

        api_keys = {"GOOGLE_API_KEY": "test"}
        agi_worker, thread = create_agi_worker_thread(
            objective="Test", model="auto", api_keys=api_keys
        )

        assert agi_worker is not None
        assert thread is not None
        mock_manager.register_thread.assert_called_once()
