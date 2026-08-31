"""Tests for CLI exception hierarchy.

Tests verify proper exception creation, attributes, and error messages.
"""

import pytest

from aura_cli.cli.utils.exceptions import (
    AuraCLIError,
    CommandError,
    ConfigurationError,
    FileOperationError,
    LLMError,
    ThreadError,
    ToolExecutionError,
    UIError,
    ValidationError,
    WorkerError,
)


class TestAuraCLIError:
    """Test suite for base AuraCLIError."""

    def test_base_exception(self):
        """Test base exception can be raised."""
        with pytest.raises(AuraCLIError):
            raise AuraCLIError("Base error")

    def test_base_exception_message(self):
        """Test base exception message."""
        exc = AuraCLIError("Test message")
        assert str(exc) == "Test message"


class TestToolExecutionError:
    """Test suite for ToolExecutionError."""

    def test_creation(self):
        """Test creating ToolExecutionError."""
        exc = ToolExecutionError(
            tool_name="read_file",
            message="File not found",
            original_error=FileNotFoundError("test.txt"),
        )
        assert exc.tool_name == "read_file"
        assert exc.original_error is not None
        assert "read_file" in str(exc)

    def test_without_original_error(self):
        """Test ToolExecutionError without original error."""
        exc = ToolExecutionError(tool_name="write_file", message="Permission denied")
        assert exc.tool_name == "write_file"
        assert exc.original_error is None


class TestWorkerError:
    """Test suite for WorkerError."""

    def test_creation(self):
        """Test creating WorkerError."""
        exc = WorkerError(
            worker_name="agi_worker",
            message="Thread failed",
            original_error=RuntimeError("Error"),
        )
        assert exc.worker_name == "agi_worker"
        assert exc.original_error is not None
        assert "agi_worker" in str(exc)


class TestLLMError:
    """Test suite for LLMError."""

    def test_creation(self):
        """Test creating LLMError."""
        exc = LLMError(
            message="Connection timeout",
            model="gemini/gemini-2.0-flash-exp",
            original_error=TimeoutError("Timeout"),
        )
        assert exc.model == "gemini/gemini-2.0-flash-exp"
        assert exc.original_error is not None

    def test_without_model(self):
        """Test LLMError without model."""
        exc = LLMError(message="Generic LLM error")
        assert exc.model is None


class TestFileOperationError:
    """Test suite for FileOperationError."""

    def test_creation(self):
        """Test creating FileOperationError."""
        exc = FileOperationError(
            operation="read",
            file_path="/path/to/file.txt",
            message="Permission denied",
            original_error=PermissionError("Access denied"),
        )
        assert exc.operation == "read"
        assert exc.file_path == "/path/to/file.txt"
        assert exc.original_error is not None
        assert "read" in str(exc)
        assert "/path/to/file.txt" in str(exc)


class TestCommandError:
    """Test suite for CommandError."""

    def test_creation(self):
        """Test creating CommandError."""
        exc = CommandError(
            command="/agi",
            message="Invalid objective",
            original_error=ValueError("Empty objective"),
        )
        assert exc.command == "/agi"
        assert exc.original_error is not None
        assert "/agi" in str(exc)


class TestThreadError:
    """Test suite for ThreadError."""

    def test_creation(self):
        """Test creating ThreadError."""
        exc = ThreadError(
            thread_name="worker_thread",
            message="Thread crashed",
            original_error=RuntimeError("Crash"),
        )
        assert exc.thread_name == "worker_thread"
        assert exc.original_error is not None
        assert "worker_thread" in str(exc)


class TestConfigurationError:
    """Test suite for ConfigurationError."""

    def test_creation(self):
        """Test creating ConfigurationError."""
        with pytest.raises(ConfigurationError):
            raise ConfigurationError("Invalid configuration")


class TestUIError:
    """Test suite for UIError."""

    def test_creation(self):
        """Test creating UIError."""
        with pytest.raises(UIError):
            raise UIError("UI operation failed")


class TestValidationError:
    """Test suite for ValidationError."""

    def test_creation(self):
        """Test creating ValidationError."""
        with pytest.raises(ValidationError):
            raise ValidationError("Validation failed")


class TestExceptionHierarchy:
    """Test exception hierarchy inheritance."""

    def test_all_exceptions_inherit_from_base(self):
        """Test that all exceptions inherit from AuraCLIError."""
        exceptions = [
            ConfigurationError,
            ToolExecutionError,
            WorkerError,
            LLMError,
            UIError,
            ThreadError,
            ValidationError,
            FileOperationError,
            CommandError,
        ]

        for exc_class in exceptions:
            assert issubclass(exc_class, AuraCLIError)
