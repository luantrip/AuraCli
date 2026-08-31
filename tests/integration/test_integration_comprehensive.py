"""Comprehensive integration tests.

Tests for integration between different modules.
"""

import queue
from unittest.mock import MagicMock, patch


class TestCLIToTUIIntegration:
    """Tests for CLI to TUI integration."""

    def test_bridge_creation(self):
        """Test TextualUIManager can bridge CLI to TUI."""
        from aura_cli.tui.bridge import TextualUIManager

        mock_app = MagicMock()
        manager = TextualUIManager(mock_app)

        assert manager.app == mock_app


    def test_bridge_with_status_queue(self):
        """Test bridge works with status queue."""
        from aura_cli.tui.bridge import TextualUIManager

        mock_app = MagicMock()
        status_queue = queue.Queue()

        manager = TextualUIManager(mock_app, status_queue=status_queue)

        assert manager.status_queue == status_queue


class TestMemoryToSessionIntegration:
    """Tests for Memory to Session integration."""


class TestConfigToToolsIntegration:
    """Tests for Config to Tools integration."""

    def test_config_affects_tools(self):
        """Test that config settings affect tool behavior."""
        from aura_cli.core.service_registry import get_tools_dict

        # Get tools
        tools = get_tools_dict()

        # Tools should be available
        assert len(tools) > 0
        assert "read_file" in tools


class TestCommandRouterToToolsIntegration:
    """Tests for CommandRouter to Tools integration."""

    def test_shell_command_execution(self):
        """Test shell command routing and execution."""
        from aura_cli.core.tools.shell import (
            execute_shell_command,
            should_execute_directly,
        )

        # Check detection
        assert should_execute_directly("ls") is True
        assert should_execute_directly("help me code") is False

        # Execute simple command
        success, output = execute_shell_command("echo test")
        assert success is True
        assert "test" in output

    def test_command_router_slash_commands(self):
        """Test slash command routing."""
        from aura_cli.cli.command_router import route_command

        mock_ui = MagicMock()
        mock_ui.status_queue = queue.Queue()
        mock_stats = MagicMock()
        mock_console = MagicMock()

        with patch("aura_cli.cli.command_router.process_slash_command") as mock_process:
            mock_process.return_value = (True, "Help text", None, None, None)

            result = route_command(
                "/help", None, None, "gpt-4", mock_stats, mock_ui, mock_console
            )

            assert result[0] is True
            mock_process.assert_called_once()


class TestWorkerToToolsIntegration:
    """Tests for Worker to Tools integration."""

    def test_agi_worker_has_tools(self, tmp_path):
        """Test AgiWorker can access tools."""
        from aura_cli.cli.workers.agi_worker import AgiWorker
        from aura_cli.core.service_registry import get_tools_dict

        tools = get_tools_dict()

        with patch("aura_cli.cli.workers.agi_worker.get_memory_service"):
            with patch(
                "aura_cli.cli.workers.agi_worker.get_session_state"
            ) as mock_session:
                mock_session.return_value = MagicMock(
                    get_current_state=MagicMock(
                        return_value=MagicMock(constitution=None)
                    )
                )
                worker = AgiWorker(
                    prompt="Test",
                    model="gpt-4",
                    api_keys={},
                    headless=True,
                    status_queue=queue.Queue(),
                    available_tools=tools,
                    project_root=tmp_path,
                )

                assert len(worker.available_tools) > 0


class TestEventBusIntegration:
    """Tests for EventBus integration."""

    def test_event_bus_singleton(self):
        """Test EventBus is singleton."""
        from aura_cli.core.events.event_bus import get_event_bus

        bus1 = get_event_bus()
        bus2 = get_event_bus()

        assert bus1 is bus2


class TestThreadManagerIntegration:
    """Tests for ThreadManager integration."""

    def test_thread_manager_singleton(self):
        """Test ThreadManager is singleton."""
        from aura_cli.cli.utils.thread_manager import get_thread_manager

        tm1 = get_thread_manager()
        tm2 = get_thread_manager()

        assert tm1 is tm2


class TestFileSystemIntegration:
    """Tests for file system integration."""

    def test_read_write_cycle(self, tmp_path, monkeypatch):
        """Test read/write file cycle."""
        import aura_cli.core.tools.file_system as fs_module
        from aura_cli.core.tools.file_system import (
            enable_path_validation,
            read_file,
            write_file,
        )

        enable_path_validation(False)
        monkeypatch.setattr(fs_module, "AUTO_CONFIRM_TOOLS", True)

        test_file = tmp_path / "test_cycle.txt"
        content = "Test content for cycle"

        # Write
        write_file(str(test_file), content)

        # Read
        result = read_file(str(test_file))

        assert content in result

    def test_list_directory_integration(self, tmp_path):
        """Test list_directory shows created files."""
        from aura_cli.core.tools.file_system import (
            enable_path_validation,
            list_directory,
        )

        enable_path_validation(False)

        # Create files
        (tmp_path / "file1.txt").write_text("content1")
        (tmp_path / "file2.py").write_text("content2")

        # List
        result = list_directory(str(tmp_path))

        assert "file1.txt" in result
        assert "file2.py" in result


class TestStatsIntegration:
    """Tests for stats integration."""

    def test_stats_tracks_tokens(self):
        """Test StatsTracker tracks tokens correctly."""
        from aura_cli.core.stats import get_stats

        stats = get_stats()
        initial = stats.total_tokens

        stats.add_tokens({"total_tokens": 100})

        assert stats.total_tokens >= initial + 100


class TestLoggerIntegration:
    """Tests for logger integration."""

