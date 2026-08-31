"""
Custom Exceptions for Aura CLI.

This module provides a hierarchy of custom exceptions for better error handling
and more specific error messages throughout the application.

Exception Hierarchy:
    AuraError (base)
    ├── ConfigurationError
    ├── LLMError
    │   ├── RateLimitError (already exists)
    │   ├── APIKeyError
    │   └── ModelNotFoundError
    ├── ToolExecutionError
    ├── ThreadError
    ├── CacheError
    └── ValidationError
"""

from typing import Any, Optional


class AuraError(Exception):
    """Base exception for all Aura CLI errors.

    All custom exceptions in Aura CLI should inherit from this class.
    This allows for consistent error handling and provides a common
    interface for error reporting.

    Attributes:
        message: Human-readable error message
        details: Optional additional details about the error
        context: Optional context information (file, line, etc.)
    """

    def __init__(
        self,
        message: str,
        details: Optional[str] = None,
        context: Optional[dict] = None,
    ):
        """Initialize Aura error.

        Args:
            message: Human-readable error message
            details: Optional additional details
            context: Optional context information
        """
        super().__init__(message)
        self.message = message
        self.details = details
        self.context = context or {}

    def __str__(self) -> str:
        """Return formatted error message."""
        if self.details:
            return f"{self.message}: {self.details}"
        return self.message

    def to_dict(self) -> dict:
        """Convert error to dictionary for serialization."""
        return {
            "error_type": self.__class__.__name__,
            "message": self.message,
            "details": self.details,
            "context": self.context,
        }


class ConfigurationError(AuraError):
    """Configuration-related errors.

    Raised when there are issues with configuration files,
    API keys, or other configuration settings.

    Examples:
        - Missing required configuration
        - Invalid configuration format
        - Configuration file not found
    """


class LLMError(AuraError):
    """Base exception for LLM-related errors.

    All LLM errors inherit from this class.
    """


class RateLimitError(LLMError):
    """Rate limit exceeded error.

    Raised when an LLM API rate limit is exceeded.

    Attributes:
        model: Model that hit the rate limit
        retry_after: Seconds to wait before retrying (if available)
    """

    def __init__(
        self,
        message: str = "Rate limit exceeded",
        model: Optional[str] = None,
        retry_after: Optional[int] = None,
        details: Optional[str] = None,
    ):
        """Initialize rate limit error.

        Args:
            message: Error message
            model: Model that hit the rate limit
            retry_after: Seconds to wait before retrying
            details: Additional details
        """
        super().__init__(message, details=details)
        self.model = model
        self.retry_after = retry_after


class APIKeyError(LLMError):
    """API key related errors.

    Raised when there are issues with API keys:
    - Missing API key
    - Invalid API key
    - API key leaked/revoked
    """

    def __init__(
        self,
        message: str,
        provider: Optional[str] = None,
        details: Optional[str] = None,
    ):
        """Initialize API key error.

        Args:
            message: Error message
            provider: LLM provider (google, openai, anthropic, etc.)
            details: Additional details
        """
        super().__init__(message, details=details)
        self.provider = provider


class ModelNotFoundError(LLMError):
    """Model not found error.

    Raised when a requested LLM model is not available or not found.
    """

    def __init__(
        self,
        message: str,
        model: Optional[str] = None,
        details: Optional[str] = None,
    ):
        """Initialize model not found error.

        Args:
            message: Error message
            model: Model name that was not found
            details: Additional details
        """
        super().__init__(message, details=details)
        self.model = model


class ToolExecutionError(AuraError):
    """Tool execution errors.

    Raised when a tool fails to execute or returns an error.

    Attributes:
        tool_name: Name of the tool that failed
        tool_params: Parameters passed to the tool
    """

    def __init__(
        self,
        message: str,
        tool_name: Optional[str] = None,
        tool_params: Optional[dict] = None,
        details: Optional[str] = None,
    ):
        """Initialize tool execution error.

        Args:
            message: Error message
            tool_name: Name of the tool that failed
            tool_params: Parameters passed to the tool
            details: Additional details
        """
        super().__init__(message, details=details)
        self.tool_name = tool_name
        self.tool_params = tool_params or {}


class ThreadError(AuraError):
    """Thread management errors.

    Raised when there are issues with thread creation, management, or shutdown.
    """

    def __init__(
        self,
        message: str,
        thread_name: Optional[str] = None,
        details: Optional[str] = None,
    ):
        """Initialize thread error.

        Args:
            message: Error message
            thread_name: Name of the thread (if applicable)
            details: Additional details
        """
        super().__init__(message, details=details)
        self.thread_name = thread_name


class CacheError(AuraError):
    """Cache-related errors.

    Raised when there are issues with cache operations.
    """


class ValidationError(AuraError):
    """Validation errors.

    Raised when input validation fails.
    """

    def __init__(
        self,
        message: str,
        field: Optional[str] = None,
        value: Optional[Any] = None,
        details: Optional[str] = None,
    ):
        """Initialize validation error.

        Args:
            message: Error message
            field: Field that failed validation (if applicable)
            value: Value that failed validation (if applicable)
            details: Additional details
        """
        super().__init__(message, details=details)
        self.field = field
        self.value = value


class OperationCancelled(Exception):
    """Exception raised when an operation is cancelled by the user (ESC)."""


class SecurityError(AuraError):
    """Security-related errors.

    Raised when security validation fails (e.g., unsafe commands).
    """

    def __init__(
        self,
        message: str = "Security error",
        command: Optional[str] = None,
        reason: Optional[str] = None,
        details: Optional[str] = None,
    ):
        """Initialize security error.

        Args:
            message: Error message
            command: Command that failed security check (if applicable)
            reason: Reason for security failure (if applicable)
            details: Additional details
        """
        if command and reason:
            message = f"Unsafe command blocked: {command} ({reason})"
        super().__init__(message, details=details)
        self.command = command
        self.reason = reason
