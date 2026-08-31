"""Tests for shell.py - Shell command utilities."""

import subprocess
from unittest.mock import Mock, patch

from aura_cli.core.tools.shell import (
    BLOCKED_COMMANDS,
    COMMON_SHELL_COMMANDS,
    DANGEROUS_PATTERNS,
    _is_safe_command,
    _sanitize_command,
    execute_shell_command,
    extract_shell_command,
    is_shell_command,
    run_shell_command,
    should_execute_directly,
)


class TestSanitizeCommand:
    """Test suite for _sanitize_command."""

    def test_sanitize_normal_command(self):
        """Test sanitizing normal command."""
        result = _sanitize_command("ls -la")
        assert result == "ls -la"

    def test_sanitize_removes_null_bytes(self):
        """Test sanitizing removes null bytes."""
        result = _sanitize_command("ls\x00-la")
        assert "\x00" not in result

    def test_sanitize_removes_non_printable(self):
        """Test sanitizing removes non-printable characters."""
        result = _sanitize_command("ls\x01-la")
        assert "\x01" not in result

    def test_sanitize_preserves_newlines_tabs(self):
        """Test sanitizing preserves newlines and tabs."""
        result = _sanitize_command("ls\n-la\t")
        assert "\n" in result or "\t" in result

    def test_sanitize_strips_whitespace(self):
        """Test sanitizing strips whitespace."""
        result = _sanitize_command("  ls -la  ")
        assert result == "ls -la"


class TestIsSafeCommand:
    """Test suite for _is_safe_command."""

    def test_safe_simple_command(self):
        """Test simple safe command."""
        assert _is_safe_command("ls -la") is True

    def test_safe_command_with_path(self):
        """Test safe command with path."""
        assert _is_safe_command("/usr/bin/ls -la") is True

    def test_blocked_command(self):
        """Test blocked command."""
        assert _is_safe_command("dd if=/dev/zero") is False

    def test_dangerous_pattern_command_substitution(self):
        """Test dangerous command substitution pattern."""
        assert _is_safe_command("ls $(rm -rf /)") is False

    def test_dangerous_pattern_backtick(self):
        """Test dangerous backtick pattern."""
        assert _is_safe_command("ls `rm -rf /`") is False

    def test_dangerous_pattern_pipe_to_shell(self):
        """Test dangerous pipe to shell pattern."""
        assert _is_safe_command("ls | sh") is False

    def test_dangerous_pattern_eval(self):
        """Test dangerous eval pattern."""
        assert _is_safe_command("eval ls") is False

    def test_empty_command(self):
        """Test empty command."""
        assert _is_safe_command("") is False

    def test_command_with_quotes(self):
        """Test command with quotes."""
        assert _is_safe_command('ls "test file"') is True

    def test_command_with_single_quotes(self):
        """Test command with single quotes."""
        assert _is_safe_command("ls 'test file'") is True

    def test_unclosed_quotes(self):
        """Test command with unclosed quotes."""
        assert _is_safe_command('ls "test') is False

    def test_command_with_semicolon(self):
        """Test command with semicolon."""
        assert _is_safe_command("ls; rm") is False

    def test_command_with_ampersand(self):
        """Test command with ampersand."""
        # Single & is blocked (background execution/injection risk if not handled)
        assert _is_safe_command("ls & rm") is False

    def test_command_with_dollar_sign(self):
        """Test command with dollar sign."""
        assert _is_safe_command("ls $VAR") is False

    def test_command_with_newline(self):
        """Test command with newline."""
        assert _is_safe_command("ls\nrm") is False


class TestIsShellCommand:
    """Test suite for is_shell_command."""

    def test_is_shell_command_ls(self):
        """Test detecting ls command."""
        assert is_shell_command("ls") is True

    def test_is_shell_command_with_args(self):
        """Test detecting shell command with args."""
        assert is_shell_command("ls -la") is True

    def test_is_shell_command_with_bang(self):
        """Test detecting shell command with bang."""
        assert is_shell_command("!ls") is True

    def test_is_not_shell_command(self):
        """Test detecting non-shell command."""
        assert is_shell_command("Hello world") is False

    def test_is_shell_command_empty(self):
        """Test detecting empty string."""
        assert is_shell_command("") is False

    def test_is_shell_command_common_commands(self):
        """Test detecting common shell commands."""
        for cmd in ["pwd", "cd", "echo", "cat", "grep"]:
            assert is_shell_command(cmd) is True

    def test_is_shell_command_case_insensitive(self):
        """Test detecting shell command case insensitive."""
        assert is_shell_command("LS") is True


class TestExtractShellCommand:
    """Test suite for extract_shell_command."""

    def test_extract_simple_command(self):
        """Test extracting simple command."""
        result = extract_shell_command("ls -la")
        assert result == "ls -la"

    def test_extract_command_with_bang(self):
        """Test extracting command with bang."""
        result = extract_shell_command("!ls -la")
        assert result == "ls -la"

    def test_extract_command_from_text(self):
        """Test extracting command from text."""
        result = extract_shell_command("Please run ls -la")
        # Should extract the command part
        assert "ls" in result.lower()

    def test_extract_command_whitespace(self):
        """Test extracting command with whitespace."""
        result = extract_shell_command("  ls -la  ")
        assert "ls" in result


class TestExecuteShellCommand:
    """Test suite for execute_shell_command."""

    @patch("aura_cli.core.tools.shell.subprocess.run")
    def test_execute_safe_command(self, mock_subprocess):
        """Test executing safe command."""
        mock_subprocess.return_value = Mock(returncode=0, stdout="output", stderr="")

        success, result = execute_shell_command("ls -la")

        assert success is True
        assert "output" in result
        mock_subprocess.assert_called_once()

    @patch("aura_cli.core.tools.shell.subprocess.run")
    def test_execute_command_with_stderr(self, mock_subprocess):
        """Test executing command with stderr."""
        mock_subprocess.return_value = Mock(
            returncode=0, stdout="output", stderr="warning"
        )

        success, result = execute_shell_command("ls")

        assert success is True
        assert "warning" in result

    @patch("aura_cli.core.tools.shell.subprocess.run")
    def test_execute_command_timeout(self, mock_subprocess):
        """Test executing command with timeout."""
        mock_subprocess.side_effect = subprocess.TimeoutExpired("ls", 5)

        success, result = execute_shell_command("sleep 10", timeout=5)

        assert success is False
        assert "timeout" in result.lower()

    @patch("aura_cli.core.tools.shell.subprocess.run")
    def test_execute_command_not_found(self, mock_subprocess):
        """Test executing command not found."""
        mock_subprocess.side_effect = FileNotFoundError()

        success, result = execute_shell_command("nonexistent_command")

        assert success is False
        assert "não encontrado" in result.lower() or "not found" in result.lower()

    @patch("aura_cli.core.tools.shell.subprocess.run")
    def test_execute_command_permission_error(self, mock_subprocess):
        """Test executing command with permission error."""
        mock_subprocess.side_effect = PermissionError()

        success, result = execute_shell_command("restricted_command")

        assert success is False
        assert "permissão" in result.lower() or "permission" in result.lower()

    @patch("aura_cli.core.tools.shell.subprocess.run")
    def test_execute_command_empty_output(self, mock_subprocess):
        """Test executing command with empty output."""
        mock_subprocess.return_value = Mock(returncode=0, stdout="", stderr="")

        success, result = execute_shell_command("touch file")

        assert success is True
        assert (
            "sucesso" in result.lower()
            or "success" in result.lower()
            or "executado" in result.lower()
        )


class TestRunShellCommand:
    """Test suite for run_shell_command."""

    @patch("aura_cli.cli.ui.components.confirmation.ask_confirmation")
    @patch("aura_cli.core.tools.shell._is_safe_command")
    @patch("aura_cli.core.tools.shell.subprocess.run")
    @patch("aura_cli.core.tools.shell.get_stats")
    @patch("aura_cli.cli.ui.loading_states.show_tool_loading")
    @patch("aura_cli.core.ui.display_tool_call")
    def test_run_safe_command_confirmed(
        self,
        mock_display,
        mock_loading,
        mock_stats,
        mock_subprocess,
        mock_is_safe,
        mock_confirm,
    ):
        """Test running safe command when confirmed."""
        mock_is_safe.return_value = True
        mock_confirm.return_value = True
        mock_subprocess.return_value = Mock(returncode=0, stdout="output", stderr="")
        mock_stats_instance = Mock()
        mock_stats_instance.skip_confirmations = False
        mock_stats.return_value = mock_stats_instance
        mock_loading_instance = Mock()
        mock_loading.return_value = mock_loading_instance

        result = run_shell_command("ls -la")

        assert "output" in result or result == ""
        mock_subprocess.assert_called_once()

    @patch("aura_cli.cli.ui.components.confirmation.ask_confirmation")
    @patch("aura_cli.core.tools.shell.get_stats")
    @patch("aura_cli.core.ui.display_tool_call")
    def test_run_command_cancelled(self, mock_display, mock_stats, mock_confirm):
        """Test running command when cancelled."""
        mock_confirm.return_value = False
        mock_stats_instance = Mock()
        mock_stats_instance.skip_confirmations = False
        mock_stats.return_value = mock_stats_instance

        result = run_shell_command("ls")

        assert (
            "cancelado" in result.lower()
            or "cancelada" in result.lower()
            or "canceled" in result.lower()
        )

    @patch("aura_cli.core.tools.shell._is_safe_command")
    @patch("aura_cli.core.tools.shell.get_stats")
    @patch("aura_cli.cli.ui.loading_states.show_tool_loading")
    @patch("aura_cli.core.ui.display_tool_call")
    @patch("builtins.print")
    @patch("rich.console.Console")
    def test_run_unsafe_command(
        self,
        mock_console_class,
        mock_print,
        mock_display,
        mock_loading,
        mock_stats,
        mock_is_safe,
    ):
        """Test running unsafe command."""
        mock_is_safe.return_value = False
        mock_stats_instance = Mock()
        mock_stats_instance.skip_confirmations = True
        mock_stats.return_value = mock_stats_instance
        mock_loading_instance = Mock()
        mock_loading.return_value = mock_loading_instance
        mock_console = Mock()
        mock_console_class.return_value = mock_console

        result = run_shell_command("rm -rf /")

        assert (
            "bloqueado" in result.lower()
            or "blocked" in result.lower()
            or "perigosos" in result.lower()
        )


class TestShouldExecuteDirectly:
    """Test suite for should_execute_directly."""

    def test_should_execute_with_bang(self):
        """Test should execute with bang prefix."""
        assert should_execute_directly("!ls") is True

    def test_should_execute_shell_command(self):
        """Test should execute shell command."""
        assert should_execute_directly("ls -la") is True

    def test_should_not_execute_question(self):
        """Test should not execute question."""
        assert should_execute_directly("ls?") is False

    def test_should_not_execute_text(self):
        """Test should not execute regular text."""
        assert should_execute_directly("Hello world") is False


class TestConstants:
    """Test suite for constants."""

    def test_common_shell_commands_not_empty(self):
        """Test COMMON_SHELL_COMMANDS is not empty."""
        assert len(COMMON_SHELL_COMMANDS) > 0

    def test_blocked_commands_not_empty(self):
        """Test BLOCKED_COMMANDS is not empty."""
        assert len(BLOCKED_COMMANDS) > 0

    def test_dangerous_patterns_not_empty(self):
        """Test DANGEROUS_PATTERNS is not empty."""
        assert len(DANGEROUS_PATTERNS) > 0

    def test_common_commands_contains_basics(self):
        """Test COMMON_SHELL_COMMANDS contains basic commands."""
        assert "ls" in COMMON_SHELL_COMMANDS
        assert "pwd" in COMMON_SHELL_COMMANDS
        assert "cd" in COMMON_SHELL_COMMANDS

    def test_blocked_commands_contains_dangerous(self):
        """Test BLOCKED_COMMANDS contains dangerous commands."""
        assert "dd" in BLOCKED_COMMANDS
        assert "shutdown" in BLOCKED_COMMANDS
