"""Comprehensive tests for shell module.

Tests for shell command detection, extraction, and execution.
"""

import subprocess
from unittest.mock import MagicMock, patch

from aura_cli.core.utils.safe_subprocess import SubprocessResult


class TestSanitizeCommand:
    """Tests for _sanitize_command function."""

    def test_sanitize_removes_null_bytes(self):
        """Test _sanitize_command removes null bytes."""
        from aura_cli.core.tools.shell import _sanitize_command

        result = _sanitize_command("ls\x00-la")

        assert "\x00" not in result

    def test_sanitize_removes_non_printable(self):
        """Test _sanitize_command removes non-printable chars."""
        from aura_cli.core.tools.shell import _sanitize_command

        result = _sanitize_command("ls\x01\x02-la")

        assert "\x01" not in result
        assert "\x02" not in result

    def test_sanitize_keeps_printable(self):
        """Test _sanitize_command keeps printable chars."""
        from aura_cli.core.tools.shell import _sanitize_command

        result = _sanitize_command("ls -la")

        assert result == "ls -la"

    def test_sanitize_strips_whitespace(self):
        """Test _sanitize_command strips whitespace."""
        from aura_cli.core.tools.shell import _sanitize_command

        result = _sanitize_command("  ls -la  ")

        assert result == "ls -la"


class TestIsSafeCommand:
    """Tests for _is_safe_command function."""


class TestIsShellCommand:
    """Tests for is_shell_command function."""


class TestExtractShellCommand:
    """Tests for extract_shell_command function."""

    def test_extract_simple(self):
        """Test extract_shell_command with simple command."""
        from aura_cli.core.tools.shell import extract_shell_command

        result = extract_shell_command("ls -la")

        assert result == "ls -la"

    def test_extract_with_bang(self):
        """Test extract_shell_command removes ! prefix."""
        from aura_cli.core.tools.shell import extract_shell_command

        result = extract_shell_command("!echo hello")

        assert result == "echo hello"

    def test_extract_strips_whitespace(self):
        """Test extract_shell_command strips whitespace."""
        from aura_cli.core.tools.shell import extract_shell_command

        result = extract_shell_command("  ls -la  ")

        assert result == "ls -la"

    def test_extract_bang_with_space(self):
        """Test extract_shell_command handles ! with space."""
        from aura_cli.core.tools.shell import extract_shell_command

        result = extract_shell_command("! echo hello")

        assert result == "echo hello"


class TestShellExecutionStatus:
    """Tests for the single shell-enable authority."""

    @patch("aura_cli.core.config.get_config_manager")
    def test_enabled_only_for_explicit_true(self, mock_get_config):
        from aura_cli.core.tools.shell import shell_execution_status

        mock_get_config.return_value.get.return_value = True

        assert shell_execution_status() == (True, "")

    @patch("aura_cli.core.config.get_config_manager")
    def test_disabled_returns_explanatory_reason(self, mock_get_config):
        from aura_cli.core.tools.shell import shell_execution_status

        mock_get_config.return_value.get.return_value = False

        enabled, reason = shell_execution_status()

        assert enabled is False
        assert "desabilitada" in reason

    @patch(
        "aura_cli.core.config.get_config_manager",
        side_effect=RuntimeError("config unavailable"),
    )
    def test_config_error_is_fail_closed(self, _mock_get_config):
        from aura_cli.core.tools.shell import shell_execution_status

        enabled, reason = shell_execution_status()

        assert enabled is False
        assert "configuração indisponível" in reason
        assert "RuntimeError" in reason


class TestExecuteShellCommand:
    """Tests for execute_shell_command function."""

    @patch("aura_cli.core.tools.file_system.get_allowed_base_dir")
    @patch("aura_cli.core.tools.shell._run_supervised")
    def test_execute_uses_canonical_workspace_cwd(
        self, mock_run, mock_get_allowed_base_dir
    ):
        from aura_cli.core.tools.shell import execute_shell_command

        mock_get_allowed_base_dir.return_value = __import__("pathlib").Path(
            "/tmp/canonical-workspace"
        )
        mock_run.return_value = SubprocessResult(
            timeout=False, exit_code=0, stdout="output", stderr=""
        )

        success, _output = execute_shell_command("echo hello")

        assert success is True
        assert mock_run.call_args.kwargs["cwd"] == "/tmp/canonical-workspace"

    @patch("aura_cli.core.tools.shell._run_supervised")
    def test_execute_success(self, mock_run):
        """Test execute_shell_command with successful command."""
        from aura_cli.core.tools.shell import execute_shell_command

        mock_run.return_value = SubprocessResult(
            timeout=False, exit_code=0, stdout="output", stderr=""
        )

        success, output = execute_shell_command("echo hello")

        assert success is True
        assert "output" in output

    @patch("aura_cli.core.tools.shell._run_supervised")
    def test_execute_with_stderr(self, mock_run):
        """Test execute_shell_command with stderr."""
        from aura_cli.core.tools.shell import execute_shell_command

        mock_run.return_value = SubprocessResult(
            timeout=False, exit_code=0, stdout="output", stderr="warning"
        )

        success, output = execute_shell_command("ls")

        assert success is True
        assert "warning" in output

    @patch("aura_cli.core.tools.shell._run_supervised")
    def test_execute_timeout(self, mock_run):
        """Test execute_shell_command with timeout."""
        from aura_cli.core.tools.shell import execute_shell_command

        mock_run.side_effect = subprocess.TimeoutExpired("cmd", 30)

        success, output = execute_shell_command("sleep 100")

        assert success is False
        assert "Timeout" in output or "timeout" in output.lower()

    @patch("aura_cli.core.tools.shell._run_supervised")
    def test_execute_not_found(self, mock_run):
        """Test execute_shell_command with command not found."""
        from aura_cli.core.tools.shell import execute_shell_command

        mock_run.side_effect = FileNotFoundError()

        success, output = execute_shell_command("nonexistent_cmd")

        assert success is False
        assert "não encontrado" in output.lower() or "not found" in output.lower()

    @patch("aura_cli.core.tools.shell._run_supervised")
    def test_execute_permission_error(self, mock_run):
        """Test execute_shell_command with permission error."""
        from aura_cli.core.tools.shell import execute_shell_command

        mock_run.side_effect = PermissionError()

        success, output = execute_shell_command("restricted_cmd")

        assert success is False
        assert "permissão" in output.lower() or "permission" in output.lower()

    def test_execute_unsafe_command(self):
        """Test execute_shell_command rejects unsafe commands."""
        from aura_cli.core.tools.shell import execute_shell_command

        success, output = execute_shell_command("echo $(whoami)")

        assert success is False
        assert "bloqueado" in output.lower() or "segurança" in output.lower()

    @patch("aura_cli.core.tools.shell._run_supervised")
    def test_execute_clear(self, mock_run):
        """Test execute_shell_command handles clear command."""
        from aura_cli.core.tools.shell import execute_shell_command

        mock_run.return_value = SubprocessResult(
            timeout=False, exit_code=0, stdout="", stderr=""
        )

        success, output = execute_shell_command("clear")

        assert success is True
        assert output == "__CLEAR_SCREEN__"

    @patch("aura_cli.core.tools.shell._run_supervised")
    def test_execute_no_output(self, mock_run):
        """Test execute_shell_command with no output."""
        from aura_cli.core.tools.shell import execute_shell_command

        mock_run.return_value = SubprocessResult(
            timeout=False, exit_code=0, stdout="", stderr=""
        )

        success, output = execute_shell_command("touch file.txt")

        assert success is True
        assert "success" in output.lower()


class TestShouldExecuteDirectly:
    """Tests for should_execute_directly function."""


class TestBackgroundShellCommand:
    """Tests for background shell integration with the supervisor."""

    @patch("aura_cli.core.utils.background_process.get_background_process_supervisor")
    def test_start_background_registers_owner_and_pid(self, mock_get_supervisor):
        from aura_cli.core.tools.shell import _start_background_command
        from aura_cli.core.utils.background_process import BackgroundProcessRecord

        supervisor = MagicMock()
        supervisor.start.return_value = BackgroundProcessRecord(
            pid=4242,
            command=("echo", "hello"),
            owner_task="task-42",
            started_at=1.0,
        )
        mock_get_supervisor.return_value = supervisor
        console = MagicMock()

        result = _start_background_command("echo hello", console, owner_task="task-42")

        assert result.background is True
        assert result.process_id == 4242
        assert result.exit_code is None
        supervisor.start.assert_called_once_with(
            ["echo", "hello"], owner_task="task-42", cwd=__import__("os").getcwd()
        )

    @patch("aura_cli.core.utils.background_process.get_background_process_supervisor")
    def test_start_background_reports_missing_command(self, mock_get_supervisor):
        from aura_cli.core.tools.shell import _start_background_command

        supervisor = MagicMock()
        supervisor.start.side_effect = FileNotFoundError
        mock_get_supervisor.return_value = supervisor

        result = _start_background_command("missing-tool", MagicMock())

        assert result.background is True
        assert result.exit_code == 127
        assert "not found" in result.lower()


class TestRunShellCommand:
    """Tests for run_shell_command function."""

    def test_run_shell_command_function_exists(self):
        """Test run_shell_command function exists."""
        from aura_cli.core.tools.shell import run_shell_command

        assert callable(run_shell_command)


class TestCommonShellCommands:
    """Tests for COMMON_SHELL_COMMANDS constant."""

    def test_common_commands_contains_ls(self):
        """Test COMMON_SHELL_COMMANDS contains ls."""
        from aura_cli.core.tools.shell import COMMON_SHELL_COMMANDS

        assert "ls" in COMMON_SHELL_COMMANDS

    def test_common_commands_contains_git(self):
        """Test COMMON_SHELL_COMMANDS contains git."""
        from aura_cli.core.tools.shell import COMMON_SHELL_COMMANDS

        assert "git" in COMMON_SHELL_COMMANDS

    def test_common_commands_contains_python(self):
        """Test COMMON_SHELL_COMMANDS contains python."""
        from aura_cli.core.tools.shell import COMMON_SHELL_COMMANDS

        assert "python" in COMMON_SHELL_COMMANDS


class TestBlockedCommands:
    """Tests for BLOCKED_COMMANDS constant."""

    def test_blocked_contains_shutdown(self):
        """Test BLOCKED_COMMANDS contains shutdown."""
        from aura_cli.core.tools.shell import BLOCKED_COMMANDS

        assert "shutdown" in BLOCKED_COMMANDS

    def test_blocked_contains_dd(self):
        """Test BLOCKED_COMMANDS contains dd."""
        from aura_cli.core.tools.shell import BLOCKED_COMMANDS

        assert "dd" in BLOCKED_COMMANDS
