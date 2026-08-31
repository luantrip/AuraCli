"""Centralized error handling patterns."""

from __future__ import annotations

import functools
import logging
from typing import Callable, Type, TypeVar

F = TypeVar("F", bound=Callable)

logger = logging.getLogger(__name__)


def handle_exceptions(
    *catch_types: Type[BaseException],
    log_level: int = logging.ERROR,
    default=None,
    reraise: bool = False,
):
    """Decorator for standardized exception handling.

    Args:
        *catch_types: Exception types to catch. Defaults to Exception.
        log_level: Logging level for caught exceptions.
        default: Value to return on failure (if not reraising).
        reraise: Whether to re-raise after logging.

    Example:
        @handle_exceptions(ValueError, TypeError, reraise=True)
        def validate(data):
            ...

        @handle_exceptions(IOError, default="")
        def read_optional_file(path):
            ...
    """
    if not catch_types:
        catch_types = (Exception,)

    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except catch_types as e:
                logger.log(log_level, "%s failed: %s", func.__qualname__, e)
                if reraise:
                    raise
                return default

        return wrapper  # type: ignore[return-value]

    return decorator


def async_handle_exceptions(
    *catch_types: Type[BaseException],
    log_level: int = logging.ERROR,
    default=None,
    reraise: bool = False,
):
    """Async version of handle_exceptions."""
    if not catch_types:
        catch_types = (Exception,)

    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except catch_types as e:
                logger.log(log_level, "%s failed: %s", func.__qualname__, e)
                if reraise:
                    raise
                return default

        return wrapper  # type: ignore[return-value]

    return decorator
