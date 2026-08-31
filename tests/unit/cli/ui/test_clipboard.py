"""Tests for clipboard module.

Tests for clipboard functionality.
"""

from unittest.mock import MagicMock, patch


class TestCopyToClipboard:
    """Tests for copy_to_clipboard function."""

    def test_copy_to_clipboard_darwin(self):
        """Test clipboard copy on macOS."""
        from aura_cli.cli.ui.clipboard import copy_to_clipboard

        with patch("aura_cli.cli.ui.clipboard.platform.system", return_value="Darwin"):
            with patch("aura_cli.cli.ui.clipboard.subprocess.Popen") as mock_popen:
                mock_process = MagicMock()
                mock_process.returncode = 0
                mock_process.communicate.return_value = (b"", b"")
                mock_popen.return_value = mock_process

                result = copy_to_clipboard("test text")

                assert result is True
                mock_popen.assert_called_once()
                args = mock_popen.call_args[0][0]
                assert args == ["pbcopy"]

    def test_copy_to_clipboard_darwin_failure(self):
        """Test clipboard copy failure on macOS."""
        from aura_cli.cli.ui.clipboard import copy_to_clipboard

        with patch("aura_cli.cli.ui.clipboard.platform.system", return_value="Darwin"):
            with patch("aura_cli.cli.ui.clipboard.subprocess.Popen") as mock_popen:
                mock_process = MagicMock()
                mock_process.returncode = 1
                mock_process.communicate.return_value = (b"", b"error")
                mock_popen.return_value = mock_process

                result = copy_to_clipboard("test text")

                assert result is False

    def test_copy_to_clipboard_linux_xclip(self):
        """Test clipboard copy on Linux with xclip."""
        from aura_cli.cli.ui.clipboard import copy_to_clipboard

        with patch("aura_cli.cli.ui.clipboard.platform.system", return_value="Linux"):
            with patch("aura_cli.cli.ui.clipboard.subprocess.Popen") as mock_popen:
                mock_process = MagicMock()
                mock_process.returncode = 0
                mock_process.communicate.return_value = (b"", b"")
                mock_popen.return_value = mock_process

                result = copy_to_clipboard("test text")

                assert result is True

    def test_copy_to_clipboard_linux_fallback_xsel(self):
        """Test clipboard copy on Linux falls back to xsel."""
        from aura_cli.cli.ui.clipboard import copy_to_clipboard

        with patch("aura_cli.cli.ui.clipboard.platform.system", return_value="Linux"):
            with patch("aura_cli.cli.ui.clipboard.subprocess.Popen") as mock_popen:
                # First call (xclip) fails
                def side_effect(*args, **kwargs):
                    if args[0][0] == "xclip":
                        raise FileNotFoundError()
                    mock_process = MagicMock()
                    mock_process.returncode = 0
                    mock_process.communicate.return_value = (b"", b"")
                    return mock_process

                mock_popen.side_effect = side_effect

                result = copy_to_clipboard("test text")

                assert result is True

    def test_copy_to_clipboard_windows(self):
        """Test clipboard copy on Windows."""
        from aura_cli.cli.ui.clipboard import copy_to_clipboard

        with patch("aura_cli.cli.ui.clipboard.platform.system", return_value="Windows"):
            with patch("aura_cli.cli.ui.clipboard.subprocess.Popen") as mock_popen:
                mock_process = MagicMock()
                mock_process.returncode = 0
                mock_process.communicate.return_value = (b"", b"")
                mock_popen.return_value = mock_process

                result = copy_to_clipboard("test text")

                assert result is True
                args = mock_popen.call_args[0][0]
                assert args == ["clip"]

    def test_copy_to_clipboard_unknown_system(self):
        """Test clipboard copy on unknown system."""
        from aura_cli.cli.ui.clipboard import copy_to_clipboard

        with patch("aura_cli.cli.ui.clipboard.platform.system", return_value="Unknown"):
            result = copy_to_clipboard("test text")

            assert result is False

    def test_copy_to_clipboard_exception(self):
        """Test clipboard copy handles exceptions."""
        from aura_cli.cli.ui.clipboard import copy_to_clipboard

        with patch(
            "aura_cli.cli.ui.clipboard.subprocess.Popen", side_effect=Exception("error")
        ):
            with patch(
                "aura_cli.cli.ui.clipboard.platform.system", return_value="Darwin"
            ):
                result = copy_to_clipboard("test text")

                assert result is False


class TestDisplayCopyFeedback:
    """Tests for display_copy_feedback function."""

    def test_display_copy_feedback_success(self):
        """Test displaying success feedback."""
        from aura_cli.cli.ui.clipboard import display_copy_feedback

        with patch("aura_cli.cli.ui.clipboard.console") as mock_console:
            display_copy_feedback(True, "code")

            mock_console.print.assert_called_once()

    def test_display_copy_feedback_failure(self):
        """Test displaying failure feedback."""
        from aura_cli.cli.ui.clipboard import display_copy_feedback

        with patch("aura_cli.cli.ui.clipboard.console") as mock_console:
            display_copy_feedback(False, "code")

            mock_console.print.assert_called_once()


class TestCopyCode:
    """Tests for copy_code function."""

    def test_copy_code_success(self):
        """Test copying code successfully."""
        from aura_cli.cli.ui.clipboard import copy_code

        with patch("aura_cli.cli.ui.clipboard.copy_to_clipboard", return_value=True):
            with patch("aura_cli.cli.ui.clipboard.display_copy_feedback"):
                result = copy_code("def hello(): pass")

                assert result is True

    def test_copy_code_with_language(self):
        """Test copying code with language specified."""
        from aura_cli.cli.ui.clipboard import copy_code

        with patch("aura_cli.cli.ui.clipboard.copy_to_clipboard", return_value=True):
            with patch(
                "aura_cli.cli.ui.clipboard.display_copy_feedback"
            ) as mock_feedback:
                copy_code("def hello(): pass", language="python")

                mock_feedback.assert_called_once()
                # Check that language was passed
                args = mock_feedback.call_args[0]
                assert "python" in args[1]

    def test_copy_code_failure(self):
        """Test copying code failure."""
        from aura_cli.cli.ui.clipboard import copy_code

        with patch("aura_cli.cli.ui.clipboard.copy_to_clipboard", return_value=False):
            with patch("aura_cli.cli.ui.clipboard.display_copy_feedback"):
                result = copy_code("def hello(): pass")

                assert result is False


class TestCopyCommand:
    """Tests for copy_command function."""

    def test_copy_command_success(self):
        """Test copying command successfully."""
        from aura_cli.cli.ui.clipboard import copy_command

        with patch("aura_cli.cli.ui.clipboard.copy_to_clipboard", return_value=True):
            with patch(
                "aura_cli.cli.ui.clipboard.display_copy_feedback"
            ) as mock_feedback:
                result = copy_command("ls -la")

                assert result is True
                mock_feedback.assert_called_with(True, "command")


class TestCopyText:
    """Tests for copy_text function."""

    def test_copy_text_success(self):
        """Test copying text successfully."""
        from aura_cli.cli.ui.clipboard import copy_text

        with patch("aura_cli.cli.ui.clipboard.copy_to_clipboard", return_value=True):
            with patch(
                "aura_cli.cli.ui.clipboard.display_copy_feedback"
            ) as mock_feedback:
                result = copy_text("Hello world")

                assert result is True
                mock_feedback.assert_called_with(True, "text")

    def test_copy_text_custom_label(self):
        """Test copying text with custom label."""
        from aura_cli.cli.ui.clipboard import copy_text

        with patch("aura_cli.cli.ui.clipboard.copy_to_clipboard", return_value=True):
            with patch(
                "aura_cli.cli.ui.clipboard.display_copy_feedback"
            ) as mock_feedback:
                result = copy_text("output data", label="output")

                assert result is True
                mock_feedback.assert_called_with(True, "output")
