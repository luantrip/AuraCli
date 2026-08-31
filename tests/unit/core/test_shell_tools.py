"""Tests for core/tools/shell.py — should_execute_directly, run_shell_command."""

from aura_cli.core.tools.shell import extract_shell_command, should_execute_directly


class TestShouldExecuteDirectly:
    def test_ls_command(self):
        assert should_execute_directly("ls -la") is True

    def test_git_command(self):
        assert should_execute_directly("git status") is True

    def test_python_command(self):
        assert should_execute_directly("python3 main.py") is True

    def test_slash_command_not_shell(self):
        assert should_execute_directly("/help") is False

    def test_regular_question_not_shell(self):
        assert should_execute_directly("What is Python?") is False

    def test_empty_string(self):
        assert should_execute_directly("") is False

    def test_cat_command(self):
        assert should_execute_directly("cat README.md") is True

    def test_grep_command(self):
        assert should_execute_directly("grep -r TODO .") is True

    def test_pip_command(self):
        assert should_execute_directly("pip install requests") is True


class TestExtractShellCommand:
    def test_returns_command_as_is(self):
        assert extract_shell_command("ls -la /tmp") == "ls -la /tmp"

    def test_strips_whitespace(self):
        assert extract_shell_command("  ls  ").strip() == "ls"


class TestRunShellCommand:
    """run_shell_command calls ask_confirmation — mock it to avoid stdin."""

    def test_simple_echo(self):
        from unittest.mock import patch

        from aura_cli.core.tools.shell import run_shell_command

        with patch(
            "aura_cli.cli.ui.components.confirmation.ask_confirmation",
            return_value=True,
        ):
            output = run_shell_command("echo hello")
        assert isinstance(output, str)

    def test_background_returns_string(self):
        from unittest.mock import patch

        from aura_cli.core.tools.shell import run_shell_command

        with patch(
            "aura_cli.cli.ui.components.confirmation.ask_confirmation",
            return_value=True,
        ):
            output = run_shell_command("sleep 0.01", background=True)
        assert isinstance(output, str)
