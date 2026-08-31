"""Custom exception hierarchy for Aura CLI.

Provides specific exception types for better error handling and recovery.
"""

from typing import Optional


class AuraCLIError(Exception):
    """Base exception for all Aura CLI errors."""


class ConfigurationError(AuraCLIError):
    """Raised when there's a configuration problem."""


class ToolExecutionError(AuraCLIError):
    """Raised when a tool execution fails."""

    def __init__(
        self, tool_name: str, message: str, original_error: Optional[Exception] = None
    ):
        """Initialize the widget."""
        super().__init__(f"Tool '{tool_name}' failed: {message}")
        self.tool_name = tool_name
        self.original_error = original_error


class WorkerError(AuraCLIError):
    """Raised when a worker thread encounters an error."""

    def __init__(
        self, worker_name: str, message: str, original_error: Optional[Exception] = None
    ):
        """Initialize the instance."""
        super().__init__(f"Worker '{worker_name}' error: {message}")
        self.worker_name = worker_name
        self.original_error = original_error


class LLMError(AuraCLIError):
    """Raised when LLM operations fail."""

    def __init__(
        self,
        message: str,
        model: Optional[str] = None,
        original_error: Optional[Exception] = None,
    ):
        """Initialize the instance."""
        super().__init__(f"LLM error: {message}")
        self.model = model
        self.original_error = original_error


class RateLimitError(LLMError):
    """Raised when API rate limit is exceeded."""

    def __init__(
        self,
        message: str = "Limite de taxa excedido",
        model: Optional[str] = None,
        retry_after: Optional[int] = None,
        original_error: Optional[Exception] = None,
    ):
        """Initialize the instance."""
        super().__init__(message, model, original_error)
        self.retry_after = retry_after  # Seconds to wait before retry


class UIError(AuraCLIError):
    """Raised when UI operations fail."""


class ThreadError(AuraCLIError):
    """Raised when thread operations fail."""

    def __init__(
        self, thread_name: str, message: str, original_error: Optional[Exception] = None
    ):
        """Initialize the instance."""
        super().__init__(f"Thread '{thread_name}' error: {message}")
        self.thread_name = thread_name
        self.original_error = original_error


class ValidationError(AuraCLIError):
    """Raised when validation fails."""


class FileOperationError(AuraCLIError):
    """Raised when file operations fail."""

    def __init__(
        self,
        operation: str,
        file_path: str,
        message: str,
        original_error: Optional[Exception] = None,
    ):
        """Initialize the instance."""
        super().__init__(f"File {operation} failed for '{file_path}': {message}")
        self.operation = operation
        self.file_path = file_path
        self.original_error = original_error


class CommandError(AuraCLIError):
    """Raised when command processing fails."""

    def __init__(
        self, command: str, message: str, original_error: Optional[Exception] = None
    ):
        """Initialize the widget."""
        super().__init__(f"Command '{command}' failed: {message}")
        self.command = command
        self.original_error = original_error
