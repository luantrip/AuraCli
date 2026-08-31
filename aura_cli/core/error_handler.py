"""
Centralized Error Handler for Aura CLI.

Provides a unified interface for error handling throughout the application,
ensuring consistent error reporting, logging, and user notification.
"""

import logging
from typing import Any, Callable, Dict, Optional

from aura_cli.core.exceptions import AuraError
from aura_cli.core.logger import get_logger

logger = get_logger(__name__)


class ErrorHandler:
    """Centralized error handler for Aura CLI.

    Provides methods for handling errors consistently across the application,
    with appropriate logging, user notification, and error recovery strategies.
    """

    def __init__(self):
        """Initialize error handler."""
        self.logger = get_logger(__name__)

    def handle_error(
        self,
        error: Exception,
        context: str = "",
        log: bool = True,
        notify: bool = False,
        notify_callback: Optional[Callable[..., Any]] = None,
        reraise: bool = False,
    ) -> Optional[Dict[str, Any]]:
        """Handle error with appropriate logging and notification.

        Args:
            error: Exception to handle
            context: Context information (e.g., "command:process", "tool:read_file")
            log: Whether to log the error (default: True)
            notify: Whether to notify the user (default: False)
            notify_callback: Optional callback function for user notification
            reraise: Whether to re-raise the exception (default: False)

        Returns:
            Error information dictionary or None if reraise is True

        Raises:
            Exception: If reraise is True, re-raises the original exception
        """
        error_info = self._extract_error_info(error, context)

        if log:
            self._log_error(error, error_info, context)

        if notify and notify_callback:
            self._notify_user(error, error_info, notify_callback)

        if reraise:
            raise error

        return error_info

    def _extract_error_info(self, error: Exception, context: str) -> Dict[str, Any]:
        """Extract error information from exception.

        Args:
            error: Exception to extract info from
            context: Context information

        Returns:
            Dictionary with error information
        """
        error_info = {
            "error_type": type(error).__name__,
            "message": str(error),
            "context": context,
        }

        if isinstance(error, AuraError):
            error_info.update(
                {
                    "details": error.details,  # type: ignore[dict-item]
                    "context_data": error.context,  # type: ignore[dict-item]
                }
            )

            if hasattr(error, "provider"):
                error_info["provider"] = error.provider
            if hasattr(error, "model"):
                error_info["model"] = error.model
            if hasattr(error, "tool_name"):
                error_info["tool_name"] = error.tool_name
            if hasattr(error, "retry_after"):
                error_info["retry_after"] = error.retry_after

        return error_info

    def _log_error(
        self, error: Exception, error_info: Dict[str, Any], context: str
    ) -> None:
        """Log error with appropriate level.

        Args:
            error: Exception to log
            error_info: Error information dictionary
            context: Context information
        """
        log_level = logging.ERROR

        if isinstance(error, (KeyboardInterrupt, SystemExit)):
            log_level = logging.INFO
        elif isinstance(error, AuraError):
            log_level = logging.ERROR
        elif isinstance(error, (ValueError, TypeError, AttributeError)):
            log_level = logging.WARNING

        log_message = f"Erro em {context}: {error_info['message']}"
        if error_info.get("details"):
            log_message += f" ({error_info['details']})"

        self.logger.log(log_level, log_message, exc_info=True)

    def _notify_user(
        self,
        error: Exception,
        error_info: Dict[str, Any],
        notify_callback: Callable[..., Any],
    ) -> None:
        """Notify user about error.

        Args:
            error: Exception that occurred
            error_info: Error information dictionary
            notify_callback: Callback function for notification
        """
        if isinstance(error, AuraError):
            message = error.message
            if error.details:
                message += f": {error.details}"
        else:
            message = f"Erro: {error_info['message']}"

        try:
            notify_callback(message, severity="error")
        except Exception as e:
            self.logger.warning(f"Error notifying user: {e}")

    def handle_tool_error(
        self,
        tool_name: str,
        error: Exception,
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Handle tool execution error specifically.

        Args:
            tool_name: Name of the tool that failed
            error: Exception that occurred
            params: Parameters passed to the tool

        Returns:
            Error information dictionary
        """
        from aura_cli.core.exceptions import ToolExecutionError

        tool_error = ToolExecutionError(
            message=f"Ferramenta '{tool_name}' falhou",
            tool_name=tool_name,
            tool_params=params or {},
            details=str(error),
        )

        return self.handle_error(  # type: ignore[return-value]
            tool_error,
            context=f"tool:{tool_name}",
            log=True,
            notify=False,
        )

    def handle_llm_error(
        self,
        error: Exception,
        provider: Optional[str] = None,
        model: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Handle LLM-related error specifically.

        Args:
            error: Exception that occurred
            provider: LLM provider (if known)
            model: Model name (if known)

        Returns:
            Error information dictionary
        """
        from aura_cli.core.exceptions import APIKeyError, LLMError, RateLimitError

        error_str = str(error).lower()
        if "rate limit" in error_str or "429" in error_str:
            llm_error = RateLimitError(
                message="Limite de taxa excedido",
                model=model,
            )
        elif "api key" in error_str or "403" in error_str or "401" in error_str:
            llm_error = APIKeyError(  # type: ignore[assignment]
                message="Erro de chave de API",
                provider=provider or "unknown",
                details=str(error),
            )
        else:
            llm_error = LLMError(  # type: ignore[assignment]
                message=f"Erro LLM: {error!s}",
                details=f"Provedor: {provider or 'desconhecido'}, Modelo: {model}",
            )

        return self.handle_error(  # type: ignore[return-value]
            llm_error,
            context=f"llm:{provider}:{model}",
            log=True,
            notify=True,
        )


_error_handler: Optional[ErrorHandler] = None


def get_error_handler() -> ErrorHandler:
    """Get global error handler instance.

    Returns:
        ErrorHandler instance (singleton)
    """
    global _error_handler
    if _error_handler is None:
        _error_handler = ErrorHandler()
    return _error_handler
