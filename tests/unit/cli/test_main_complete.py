"""Comprehensive tests for main.py - All functions covered.

Tests verify:
- chat: Direct chat command
- agi: AGI agent command
- settings: Settings command
- start_interactive_session: Interactive session startup
- main: Main entry point
"""

import json
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
import typer

from aura_cli.cli.main import (
    _main_callback,
    _wait_for_worker_with_deadline,
    agi,
    chat,
    settings,
    start_interactive_session,
)
from aura_cli.cli.utils.worker_readiness import ReadinessReport, WorkerReadinessError


class _FinishedWorker:
    task_id = "ops-2"

    def wait_terminal(self, timeout: float) -> dict:
        return {"status": "completed"}


class _LiveThread:
    def __init__(self, alive: bool = True) -> None:
        self.alive = alive
        self.join_timeouts: list[float] = []

    def is_alive(self) -> bool:
        return self.alive

    def join(self, timeout: float) -> None:
        self.join_timeouts.append(timeout)


class TestWorkerDeadline:
    def test_live_worker_is_cancelled_and_returns_timeout(self) -> None:
        worker = Mock(task_id="ops-1")
        thread = _LiveThread()

        result = _wait_for_worker_with_deadline(
            worker,
            thread,
            timeout=0.0,
            cancel_grace=0.0,
        )

        worker.cancel.assert_called_once()
        assert result["status"] == "timeout"
        assert result["error_code"] == "worker_wait_timeout"
        assert len(thread.join_timeouts) == 1

    def test_finished_worker_returns_terminal_result(self) -> None:
        worker = _FinishedWorker()
        thread = _LiveThread(alive=False)

        result = _wait_for_worker_with_deadline(worker, thread, timeout=1.0)

        assert result == {"status": "completed"}

    def test_worker_terminalizes_during_cancel_grace(self) -> None:
        worker = Mock(task_id="ops-3")
        worker.terminal = {"status": "timeout", "error_code": "worker_wait_timeout"}
        worker.cancel.side_effect = lambda reason: None
        worker.get_result.side_effect = lambda timeout: worker.terminal
        thread = _LiveThread(alive=True)
        thread.join = Mock(side_effect=lambda timeout: setattr(thread, "alive", False))

        result = _wait_for_worker_with_deadline(
            worker,
            thread,
            timeout=0.0,
            cancel_grace=0.0,
        )

        assert result is worker.terminal
        worker.get_result.assert_called_once_with(timeout=0.0)


class TestChat:
    """Test suite for chat command."""

    @patch("aura_cli.cli.main.RuntimeServices.initialize")
    @patch("aura_cli.cli.main.AppLoop")
    @patch("aura_cli.cli.main.initialize_conversation_history")
    @patch("aura_cli.cli.main.get_tools_dict")
    @patch("aura_cli.cli.main.get_event_bus")
    @patch("aura_cli.cli.main.get_stats")
    @patch("aura_cli.cli.main.UIManager")
    @patch("aura_cli.cli.main.Console")
    def test_chat_with_message(
        self,
        mock_console,
        mock_ui,
        mock_stats,
        mock_event,
        mock_tools,
        mock_history,
        mock_app_loop,
        mock_runtime,
    ):
        """Test chat command with message."""
        mock_app_loop_instance = Mock()
        mock_app_loop.return_value = mock_app_loop_instance
        runtime_services = Mock(project_root=Path.cwd().resolve())
        mock_runtime.return_value = runtime_services

        chat(["test", "message"], model="gemini-2.5-flash")

        mock_app_loop_instance.process_command_single_shot.assert_called_once()
        assert mock_app_loop.call_args.kwargs["runtime_services"] is runtime_services

    @patch("aura_cli.cli.main.start_interactive_session")
    def test_chat_without_message(self, mock_start):
        """Test chat command without message (interactive mode)."""
        chat(None, model=None)

        mock_start.assert_called_once()


class TestAgi:
    """Test suite for agi command."""

    @patch("aura_cli.cli.utils.worker_factory.create_agi_worker_thread")
    @patch("aura_cli.cli.main.get_config_manager")
    @patch("aura_cli.cli.main.get_tools_dict")
    @patch("aura_cli.cli.main.get_stats")
    @patch("aura_cli.cli.main.UIManager")
    @patch("aura_cli.cli.main.Console")
    def test_agi_with_task(
        self,
        mock_console,
        mock_ui,
        mock_stats,
        mock_tools,
        mock_config,
        mock_create_worker,
    ):
        """Test agi command with task launches worker thread."""
        mock_thread = Mock()
        mock_thread.is_alive.return_value = False
        mock_thread.get_result.return_value = {"status": "completed"}
        mock_create_worker.return_value = (mock_thread, Mock())

        agi(
            project_root=None,
            task=["test", "task"],
            model="gemini-2.5-flash",
            output="text",
            quiet=False,
        )

        mock_create_worker.assert_called_once()

    @patch("aura_cli.cli.helpers.get_api_keys_dict", return_value={})
    @patch("aura_cli.cli.utils.worker_factory.create_agi_worker_thread")
    @patch("aura_cli.cli.main.get_config_manager")
    @patch("aura_cli.cli.main.get_stats")
    @patch("aura_cli.cli.main.UIManager")
    @patch("aura_cli.cli.main.Console")
    def test_agi_readiness_error_is_json_and_has_exit_code(
        self,
        _mock_console,
        _mock_ui,
        _mock_stats,
        _mock_config,
        mock_create_worker,
        _mock_keys,
        tmp_path,
        capsys,
    ):
        report = ReadinessReport(
            ready=False,
            code="configuration",
            message="OPENAI_API_KEY não configurada.",
            worker_type="agi",
            model="gpt-4",
            provider="gpt",
            credential_name="OPENAI_API_KEY",
            workspace=str(tmp_path),
        )
        mock_create_worker.side_effect = WorkerReadinessError(report)

        with pytest.raises(typer.Exit) as raised:
            agi(
                project_root=tmp_path,
                task=["test", "task"],
                model="gpt-4",
                output="json",
                quiet=True,
            )

        payload = json.loads(capsys.readouterr().out)
        assert raised.value.exit_code == 3
        assert payload["status"] == "error"
        assert payload["error_code"] == "configuration"
        assert "OPENAI_API_KEY" in payload["error"]
        mock_create_worker.assert_called_once()


class TestSettings:
    """Test suite for settings command."""

    @patch("aura_cli.cli.main.show_settings_menu")
    def test_settings_calls_menu(self, mock_menu):
        """Test that settings command calls menu."""
        settings()
        mock_menu.assert_called_once()


class TestStartInteractiveSession:
    """Test suite for start_interactive_session."""

    @patch("time.sleep")
    @patch("requests.get")
    @patch("subprocess.Popen")
    @patch("aura_cli.cli.main.RuntimeServices.initialize")
    @patch("aura_cli.cli.main.AppLoop")
    @patch("aura_cli.cli.main.initialize_conversation_history")
    @patch("aura_cli.cli.main.get_tools_dict")
    @patch("aura_cli.cli.main.get_event_bus")
    @patch("aura_cli.cli.main.get_stats")
    @patch("aura_cli.cli.main.UIManager")
    @patch("aura_cli.cli.main.Console")
    @patch("aura_cli.cli.main.display_aura_splash_screen")
    @patch("aura_cli.cli.main.check_api_keys")
    def test_start_interactive_session(
        self,
        mock_check_keys,
        mock_splash,
        mock_console,
        mock_ui,
        mock_stats,
        mock_event,
        mock_tools,
        mock_history,
        mock_app_loop,
        mock_runtime,
        mock_popen,
        mock_requests_get,
        mock_sleep,
    ):
        """Test starting interactive session."""
        mock_check_keys.return_value = True
        mock_app_loop_instance = Mock()
        mock_app_loop.return_value = mock_app_loop_instance
        mock_runtime.return_value = Mock(project_root=Path.cwd().resolve())

        # Mock subprocess to avoid actual process creation
        mock_process = Mock()
        mock_process.poll.return_value = None  # Process still running
        mock_process.pid = 12345
        mock_popen.return_value = mock_process

        # Mock requests to return healthy server immediately
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "ok"}
        mock_requests_get.return_value = mock_response

        start_interactive_session()

        mock_splash.assert_called_once()
        mock_app_loop_instance.run.assert_called_once()


class TestMain:
    """Test suite for main entry point."""

    @patch("aura_cli.cli.main.start_interactive_session")
    def test_main_entry_point(self, mock_start):
        """Test main entry point."""
        ctx = Mock()
        ctx.invoked_subcommand = None

        _main_callback(ctx)

        mock_start.assert_called_once()
