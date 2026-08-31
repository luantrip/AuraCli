"""Error handling helper functions for Paint tool."""

from typing import TYPE_CHECKING, Any, Optional

from aura_cli.application.paint.localization.i18n import get as _

if TYPE_CHECKING:
    from textual.geometry import Region


def _get_full_region(image_width: int, image_height: int) -> "Region":
    """Get full document region.

    Args:
        image_width: Width of the image
        image_height: Height of the image

    Returns:
        Region covering entire document
    """
    from textual.geometry import Region

    return Region(0, 0, image_width, image_height)


def _handle_file_error(
    message_box_func,
    file_path: str,
    operation: str,
    error: Exception,
) -> None:
    """Handle file operation errors.

    Args:
        message_box_func: Function to show message box
        file_path: Path to the file
        operation: Operation name (Open, Save, Paste, etc.)
        error: Exception that occurred
    """
    error_msg = str(error)
    if isinstance(error, PermissionError):
        message_box_func(operation, _("%1: Permission denied.", file_path), "ok")
    elif isinstance(error, FileNotFoundError):
        message_box_func(operation, _("%1: File not found.", file_path), "ok")
    else:
        message_box_func(operation, _("%1: %2", file_path, error_msg), "ok")


def _handle_operation_error(
    message_box_func,
    operation: str,
    error: Exception,
    context: Optional[str] = None,
) -> None:
    """Handle generic operation errors.

    Args:
        message_box_func: Function to show message box
        operation: Operation name
        error: Exception that occurred
        context: Additional context message (optional)
    """
    error_msg = str(error)
    error_type = type(error).__name__

    if isinstance(error, PermissionError):
        message = _("%1: Permission denied.", operation)
    elif isinstance(error, FileNotFoundError):
        message = _("%1: File not found.", operation)
    elif isinstance(error, ValueError):
        message = _("%1: Invalid value: %2", operation, error_msg)
    elif isinstance(error, TypeError):
        message = _("%1: Type error: %2", operation, error_msg)
    else:
        message = _("%1: %2 (%3)", operation, error_msg, error_type)

    if context:
        message = f"{context}\n{message}"

    message_box_func(operation, message, "ok")


def _handle_validation_error(
    message_box_func,
    field: str,
    value: Any,
    expected: str,
    operation: str = "Validation",
) -> None:
    """Handle validation errors.

    Args:
        message_box_func: Function to show message box
        field: Field name that failed validation
        value: Invalid value provided
        expected: Expected format/type/range
        operation: Operation name (default: "Validation")
    """
    message = _("Invalid %1: %2\nExpected: %3", field, str(value), expected)
    message_box_func(operation, message, "ok")
